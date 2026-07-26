# -*- coding: utf-8 -*-
"""验证 skill import 的 zip 双通道（临时脚本，测完可删）。"""
import shutil
import sys
import zipfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

from config import settings
from services import skill_service

TMP = Path(__file__).resolve().parent / "tmp_zip_test"
shutil.rmtree(TMP, ignore_errors=True)
TMP.mkdir(parents=True)

GOOD = {
    "team-wolves/SKILL.md": "---\nname: 群狼\nauthor: 测试组\n---\n\n# 人设\n\n测试。\n",
    "team-wolves/playbooks/general.md": "# 兜底\n\n一、测试铁律。\n",
}
TXT = "===FILE: SKILL.md===\n---\nname: 文本通道\nauthor: 阿文\n---\n\n# 人设\n文本。\n===FILE: playbooks/general.md===\n# 兜底\n一、文本。\n"

def make_zip(path: Path, files: dict) -> None:
    with zipfile.ZipFile(path, "w") as z:
        for name, content in files.items():
            z.writestr(name, content)

results = []

# 1. 正常 zip（不带 --key，应取顶层文件夹名）
good = TMP / "good.zip"
make_zip(good, GOOD)
dest = settings.SKILLS_DIR / "team-wolves"
shutil.rmtree(dest, ignore_errors=True)
try:
    r = skill_service.import_skill_zip(good, None)
    ok = (dest / "SKILL.md").exists() and (dest / "playbooks" / "general.md").exists()
    lf = (dest / "SKILL.md").read_bytes()
    results.append(("正常zip导入", ok and r["key"] == "team-wolves" and b"\r\n" not in lf, r))
except Exception as e:
    results.append(("正常zip导入", False, str(e)))

# 2. 已存在不 force 应拒绝
try:
    skill_service.import_skill_zip(good, None)
    results.append(("重复导入拒绝", False, "未报错"))
except SystemExit as e:
    results.append(("重复导入拒绝", "已存在" in str(e), str(e)))

# 3. zip-slip 防护
evil = TMP / "evil.zip"
make_zip(evil, {"team-wolves/SKILL.md": GOOD["team-wolves/SKILL.md"],
                "../escape.txt": "x"})
try:
    skill_service.import_skill_zip(evil, None, force=True)
    results.append(("zip-slip拦截", False, "未拦截"))
except SystemExit as e:
    results.append(("zip-slip拦截", "非法路径" in str(e), str(e)))

# 4. 多顶层文件夹应拒绝
multi = TMP / "multi.zip"
make_zip(multi, {"a/SKILL.md": GOOD["team-wolves/SKILL.md"],
                 "b/SKILL.md": GOOD["team-wolves/SKILL.md"]})
try:
    skill_service.import_skill_zip(multi, None)
    results.append(("多顶层拒绝", False, "未拒绝"))
except SystemExit as e:
    results.append(("多顶层拒绝", "唯一" in str(e), str(e)))

# 5. 缺 SKILL.md 应拒绝
noskill = TMP / "noskill.zip"
make_zip(noskill, {"team-x/playbooks/g.md": "# x\n"})
try:
    skill_service.import_skill_zip(noskill, None)
    results.append(("缺SKILL.md拒绝", False, "未拒绝"))
except SystemExit as e:
    results.append(("缺SKILL.md拒绝", "SKILL.md" in str(e), str(e)))

# 6. 文本通道仍可用
txt_dest = settings.SKILLS_DIR / "team-txt"
shutil.rmtree(txt_dest, ignore_errors=True)
try:
    r = skill_service.import_skill(TXT, "team-txt")
    results.append(("文本通道", (txt_dest / "SKILL.md").exists() and r["name"] == "文本通道", r))
except Exception as e:
    results.append(("文本通道", False, str(e)))

# 7. skills 列表能识别新导入的两个
try:
    keys = {s["key"] for s in skill_service.list_skills()}
    results.append(("skills列表识别", {"team-wolves", "team-txt"} <= keys, sorted(keys)))
except Exception as e:
    results.append(("skills列表识别", False, str(e)))

print("\n===== 结果 =====")
failed = 0
for name, ok, detail in results:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if not ok:
        failed += 1
        print(f"        {detail}")

# 清理测试产物
for k in ("team-wolves", "team-txt"):
    shutil.rmtree(settings.SKILLS_DIR / k, ignore_errors=True)
shutil.rmtree(TMP, ignore_errors=True)
print(f"\n{'全部通过' if failed == 0 else f'{failed} 项失败'}（测试产物已清理）")
sys.exit(1 if failed else 0)
