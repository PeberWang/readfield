# -*- coding: utf-8 -*-
"""Skill 服务：读取共读人提交的「心法」，维护盲码映射。

Skill 文件格式（markdown，含可选 front matter）：

    ---
    name: 老K
    author: 某某
    ---
    心法正文（你是什么样的人，在城堡情境中怎么想、怎么说）……

盲码：每轮次一次性随机分配并持久化到 results/blind_{round}.json，
保证同一轮内回应展示、问卷字段、排名、对比使用同一套编号。
"""
import random
import re
import zipfile
from pathlib import Path, PurePosixPath

from config import settings
from libs import store


def _parse_skill(path: Path) -> dict:
    text = path.read_text(encoding="utf-8").strip()
    meta: dict = {}
    body = text
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                body = "\n".join(lines[i + 1:]).strip()
                break
            if ":" in line:
                key, _, value = line.partition(":")
                meta[key.strip()] = value.strip()
    return {
        "key": path.stem,
        "name": meta.get("name", path.stem),
        "author": meta.get("author", ""),
        "content": body,
        "path": str(path),
        "kind": "simple",
    }


def _parse_workflow_skill(folder: Path) -> dict:
    """工作流型 skill：一个文件夹，内含 SKILL.md（front matter + 工作流定义）与配套资源。

    这类 skill 不走裸 API，由 OpenClaw 子进程按 SKILL.md 定义的工作流执行，
    最终产出 JSON 契约文件，由 delegate collect 并入回应数据。
    """
    parsed = _parse_skill(folder / "SKILL.md")
    return {
        **parsed,
        "key": folder.name,
        "name": parsed["name"] if parsed["name"] != "SKILL" else folder.name,
        "kind": "workflow",
        "dir": str(folder),
    }


def is_baseline(key: str) -> bool:
    """该 key 是否为基线 skill（裸模型对照，见 course.yaml baseline 节）。"""
    return key == settings.BASELINE_KEY


def list_skills() -> list[dict]:
    skills = [_parse_skill(p) for p in sorted(settings.SKILLS_DIR.glob("*.md"))]
    for d in sorted(settings.SKILLS_DIR.iterdir()):
        if d.is_dir() and not d.name.startswith(".") and (d / "SKILL.md").exists():
            skills.append(_parse_workflow_skill(d))
    if not settings.BASELINE_ENABLED:
        skills = [s for s in skills if not is_baseline(s["key"])]
    if not skills:
        raise SystemExit(f"skill 目录为空：{settings.SKILLS_DIR}（请共读人先提交心法 md 文件或 skill 文件夹）")
    return skills


def _blind_path(round_name: str) -> Path:
    return settings.RESULTS_DIR / f"blind_{round_name}.json"


def get_blind_map(round_name: str, skills: list[dict] | None = None) -> dict:
    """返回 {code: skill_key}。已存在则复用；不存在则基于当前 skill 列表随机分配。

    规则：
    - 跨轮次一致：day2 继承 day1 的映射（准实验对照要求同一批 skill 同一批编号）
    - 盲码只增不改：新增 skill 分配新尾号，不打乱既有编号
    """
    existing = store.load_json(_blind_path(round_name), default={})
    if not existing and round_name != "day1":
        # 非首轮：继承 day1 的映射
        existing = dict(store.load_json(_blind_path("day1"), default={}))
        if existing:
            store.save_json(_blind_path(round_name), existing)
    if skills is None:
        if not existing:
            raise SystemExit(f"轮次 {round_name} 尚无盲码映射，请先执行 run 生成")
        return existing
    assigned = set(existing.values())
    todo = [s for s in skills if s["key"] not in assigned]
    if todo:
        used_codes = {int(c) for c in existing} if existing else set()
        next_code = max(used_codes) + 1 if used_codes else 1
        random.shuffle(todo)
        for s in todo:
            existing[f"{next_code:02d}"] = s["key"]
            next_code += 1
        store.save_json(_blind_path(round_name), existing)
    return existing


def prune_blind_map(round_name: str, skills: list[dict], responses: dict) -> dict:
    """清理已删除 skill 的盲码条目（该编号下尚未生成任何回应时才删）。"""
    blind = get_blind_map(round_name, skills)
    valid_keys = {s["key"] for s in skills}
    used_codes = set()
    for bucket in responses.values():
        used_codes.update(bucket.keys())
    pruned = {code: key for code, key in blind.items()
              if key in valid_keys or code in used_codes}
    if pruned != blind:
        store.save_json(_blind_path(round_name), pruned)
    return pruned


def reveal(round_name: str) -> dict:
    """返回 {code: {key, name, author}} 供揭晓环节使用。基线 skill 标注「基线」。"""
    blind = get_blind_map(round_name)
    skills = {s["key"]: s for s in list_skills()}
    out = {}
    for code, key in sorted(blind.items()):
        if is_baseline(key):
            s = skills.get(key, {"name": key, "author": ""})
            out[code] = {"key": key, "name": f"{s['name']}（基线·裸模型）",
                         "author": s["author"] or "主讲人"}
            continue
        s = skills.get(key, {"name": key, "author": "?"})
        out[code] = {"key": key, "name": s["name"], "author": s["author"]}
    return out


_IMPORT_HEADER = re.compile(r"^===FILE:\s*(?P<path>.+?)\s*===\s*$")


def _parse_file_blocks(text: str) -> dict:
    """解析聊天 AI 吐出的成品消息（===FILE: 相对路径=== 分块格式）。"""
    files: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []

    def flush():
        if current is None:
            return
        content = "\n".join(buf).strip("\n")
        # 容忍 AI 给内容套了 markdown 代码围栏
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else ""
        if content.rstrip().endswith("```"):
            content = content.rstrip()[:-3]
        files[current] = content.strip("\n") + "\n"

    for line in text.splitlines():
        m = _IMPORT_HEADER.match(line)
        if m:
            flush()
            current = m.group("path").strip().lstrip("./").replace("\\", "/")
            buf = []
        elif current is not None:
            buf.append(line)
    flush()
    return files


def _validate_key(key: str) -> None:
    if not key or key.startswith(".") or "/" in key or "\\" in key:
        raise SystemExit(f"非法的 skill key：{key!r}（用简洁的文件夹名，不含斜杠）")


def _materialize(files: dict, key: str, force: bool) -> dict:
    """把 {相对路径: 内容} 落成 data/skills/<key>/ 文件夹（工作流型 skill）。"""
    _validate_key(key)
    if "SKILL.md" not in files:
        raise SystemExit("成品里找不到 SKILL.md，请对照《02-输出契约》检查成品结构")
    for rel in files:
        p = Path(rel)
        if p.is_absolute() or ".." in p.parts:
            raise SystemExit(f"非法文件路径：{rel}")
    dest = settings.SKILLS_DIR / key
    if dest.exists() and not force:
        raise SystemExit(f"{dest} 已存在。确认要覆盖请加 --force")
    for rel, content in files.items():
        p = dest / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
    skill = _parse_workflow_skill(dest)
    return {"key": key, "name": skill["name"], "author": skill["author"],
            "files": sorted(files)}


def import_skill(text: str, key: str, force: bool = False) -> dict:
    """文本通道（兜底）：把聊天 AI 吐出的 ===FILE:=== 成品消息落成 skill 文件夹。"""
    _validate_key(key)
    files = _parse_file_blocks(text)
    if "SKILL.md" not in files:
        raise SystemExit("成品消息里找不到 ===FILE: SKILL.md=== 块，请检查聊天 AI 的输出格式")
    return _materialize(files, key, force)


def _fix_zip_name(info: zipfile.ZipInfo) -> str:
    """zip 成员名解码修正。未带 UTF-8 标记的成员被 zipfile 按 cp437 误解码
    （Kimi 云电脑打的中文名 zip 常见此问题），重编码后按 UTF-8、GBK 依次还原。"""
    name = info.filename
    if info.flag_bits & 0x800:
        return name
    try:
        raw = name.encode("cp437")
    except UnicodeEncodeError:
        return name
    for enc in ("utf-8", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return name


def import_skill_zip(zip_path: Path, key: str | None = None,
                     force: bool = False) -> dict:
    """zip 通道（首选）：把 AI 云电脑打包的 skill zip 落成 skill 文件夹。

    契约：zip 内唯一顶层文件夹即 skill 文件夹，SKILL.md 在其根部。
    容错：SKILL.md 直接在 zip 顶层（未套文件夹）时，以 zip 文件名作为 skill key。
    key 缺省时取顶层文件夹名（散包模式取 zip 文件名）。防 zip-slip：拒绝绝对路径与 .. 成员；
    自动跳过 __MACOSX 与 .DS_Store。
    """
    with zipfile.ZipFile(zip_path) as zf:
        members: list[tuple[zipfile.ZipInfo, tuple]] = []
        for info in zf.infolist():
            name = _fix_zip_name(info).replace("\\", "/")
            if name.endswith("/"):
                continue
            parts = PurePosixPath(name).parts
            if name.startswith("/") or ".." in parts:
                raise SystemExit(f"zip 内含非法路径：{info.filename}")
            if parts[0] == "__MACOSX" or parts[-1] == ".DS_Store":
                continue
            members.append((info, parts))
        if not members:
            raise SystemExit(f"{zip_path.name} 里没有可用文件")
        tops = {parts[0] for _, parts in members}
        root_mode = any(parts == ("SKILL.md",) for _, parts in members)  # SKILL.md 散在顶层：zip 根即 skill 文件夹
        if root_mode:
            if any(len(parts) > 1 and parts[-1] == "SKILL.md" for _, parts in members):
                raise SystemExit(f"zip 顶层与子文件夹里都有 SKILL.md，结构不明：{sorted(tops)}")
        elif len(tops) != 1:
            raise SystemExit(f"zip 顶层应有唯一 skill 文件夹，实际发现 {sorted(tops)}")
        top = "" if root_mode else tops.pop()
        files: dict[str, str] = {}
        for info, parts in members:
            rel = "/".join(parts) if root_mode else "/".join(parts[1:])
            if not rel:
                raise SystemExit(f"zip 顶层散落文件：{info.filename}（全部文件应在 {top}/ 内）")
            try:
                files[rel] = zf.read(info).decode("utf-8")
            except UnicodeDecodeError:
                raise SystemExit(f"zip 内文件不是 UTF-8 文本：{info.filename}")
    if "SKILL.md" not in files:
        raise SystemExit(f"zip 里的 {top or zip_path.stem}/ 下找不到 SKILL.md")
    return _materialize(files, key or top or zip_path.stem, force)
