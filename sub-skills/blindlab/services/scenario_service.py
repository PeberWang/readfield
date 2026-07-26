# -*- coding: utf-8 -*-
"""场景服务：读取场景库中的情境文本。

场景文件格式（markdown，含可选 front matter）：

    ---
    id: castle-01
    title: 莫慕斯的审问
    summary: 一句话梗概（用于对比页）
    ---
    旁白文本……

    [[response]]

    后续文本……

[[response]] 是主人公回应的占位符，全文只允许出现一次。
"""
from pathlib import Path

from config import settings


class ScenarioError(Exception):
    pass


def _parse_front_matter(text: str) -> tuple[dict, str]:
    meta: dict = {}
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                body = "\n".join(lines[i + 1:]).strip()
                return meta, body
            if ":" in line:
                key, _, value = line.partition(":")
                meta[key.strip()] = value.strip()
        raise ScenarioError("front matter 未闭合（缺少第二个 ---）")
    return meta, text.strip()


def parse_scenario(path: Path) -> dict:
    meta, body = _parse_front_matter(path.read_text(encoding="utf-8"))
    placeholder = settings.RESPONSE_PLACEHOLDER
    count = body.count(placeholder)
    if count != 1:
        raise ScenarioError(f"{path.name}: 占位符 {placeholder} 应恰好出现一次，实际 {count} 次")
    before, after = body.split(placeholder)
    stem = path.stem
    return {
        "id": meta.get("id", stem),
        "title": meta.get("title", stem),
        "summary": meta.get("summary", ""),
        "before": before.strip(),
        "after": after.strip(),
        "path": str(path),
    }


def list_scenarios(round_name: str) -> list[dict]:
    """按轮次列出场景（文件名排序）。"""
    if round_name not in settings.ROUNDS:
        raise ScenarioError(f"未知轮次 {round_name}，可选：{list(settings.ROUNDS)}")
    folder = settings.SCENARIOS_DIR / settings.ROUNDS[round_name]["dir"]
    files = sorted(folder.glob("*.md"))
    if not files:
        raise ScenarioError(f"场景目录为空：{folder}")
    return [parse_scenario(p) for p in files]
