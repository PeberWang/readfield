# -*- coding: utf-8 -*-
"""把 starter-pack/ 打成两个分发产物（每次改完启动包都要重跑）：

1. starter-pack.zip        结构归档（人类查看、备份用；Kimi 聊天上传不收 zip）
2. 心眼子启动包.txt         单文件版（上传 Kimi 用）：以 ===PACK-FILE: 相对路径===
                           分块包含全部文件。外层容器格式故意与包内教的
                           ===FILE:=== 输出契约区分开，避免与文档示例撞车。

用法（在 blindlab 目录）：
    python tools/pack_starter.py
"""
import sys
import zipfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "starter-pack"
ZIP_DST = ROOT / "starter-pack.zip"
TXT_DST = ROOT / "心眼子启动包.txt"


def main() -> None:
    if not SRC.is_dir():
        raise SystemExit(f"找不到 {SRC}")
    files = sorted(p for p in SRC.rglob("*") if p.is_file())
    if not files:
        raise SystemExit("starter-pack/ 是空的")

    with zipfile.ZipFile(ZIP_DST, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, arcname=str(p.relative_to(ROOT)).replace("\\", "/"))

    blocks = []
    for p in files:
        rel = str(p.relative_to(SRC)).replace("\\", "/")
        content = p.read_text(encoding="utf-8").strip("\n")
        blocks.append(f"===PACK-FILE: {rel}===\n{content}")
    txt = "\n\n".join(blocks) + "\n"
    with open(TXT_DST, "w", encoding="utf-8", newline="\n") as f:
        f.write(txt)

    print(f"已打包 {len(files)} 个文件：")
    print(f"  {ZIP_DST}（结构归档）")
    print(f"  {TXT_DST}（单文件版，上传 Kimi 用这个，{len(txt)} 字符）")


if __name__ == "__main__":
    main()
