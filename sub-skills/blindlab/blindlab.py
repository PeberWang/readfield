# -*- coding: utf-8 -*-
"""心眼子活动课管道 · blindlab（盲评实验台）CLI 入口。

用法（在 readfield 根目录或 pipeline 目录下均可）：
    python pipeline/blindlab.py <命令> [参数]

命令一览：
    scenarios --round day1          列出场景
    skills                          列出已提交的心法
    generate --round day1           生成全部盲评回应（断点续跑；工作流型 skill 自动跳过）
    delegate plan --round day1      生成工作流型 skill 的子进程任务清单
    delegate collect --round day1   校验子进程产出的契约 JSON 并并入回应数据
    skill import <file> --key K     导入成品（zip 或 ===FILE:=== 文本）为 data/skills/K/
    present responses --round day1  生成「盲评回应展示」HTML
    ballot create --round day1      一键建评分多维表格，输出链接
    tally --round day1              拉取评分并统计
    present ranking --round day1|all
                                    生成「排名可视化」HTML（all = 跨天对照）
    present compare --round day1 --left 01 --right 03
                                    生成「左右分栏对比」HTML
    reveal --round day1             揭晓盲码与作者映射
    demo                            mock 数据一键产出三种展示页（不联网）
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # 保证包内 import 可用

from config import settings  # noqa: E402
from glue import commands  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(prog="blindlab", description="心眼子活动课数据管道（盲评实验台）")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("scenarios")
    p.add_argument("--round", default="day1", choices=list(settings.ROUNDS))

    sub.add_parser("skills")

    p = sub.add_parser("generate", help="skill × 场景生成盲评回应")
    p.add_argument("--round", required=True, choices=list(settings.ROUNDS))
    p.add_argument("--model", default=None, help="覆盖 .env 中的 LLM_MODEL")
    p.add_argument("--workers", type=int, default=4)

    p = sub.add_parser("delegate", help="工作流型 skill 的委托执行（plan/collect）")
    p.add_argument("action", choices=["plan", "collect"])
    p.add_argument("--round", required=True, choices=list(settings.ROUNDS))

    p = sub.add_parser("skill", help="skill 管理（import = 导入成品，zip 或 ===FILE:=== 文本）")
    p.add_argument("action", choices=["import"])
    p.add_argument("file", help="成品文件：AI 云电脑打包的 zip，或含 ===FILE:=== 块的 txt")
    p.add_argument("--key", default=None, help="落地的文件夹名（zip 通道缺省取 zip 内文件夹名；文本通道必填）")
    p.add_argument("--force", action="store_true", help="覆盖同名文件夹")

    p = sub.add_parser("present", help="生成投屏展示页（responses/ranking/compare）")
    p.add_argument("kind", choices=["responses", "ranking", "compare"])
    p.add_argument("--round", default="day1")
    p.add_argument("--left", default=None)
    p.add_argument("--right", default=None)
    p.add_argument("--open", action="store_true", help="生成后用默认浏览器打开")

    p = sub.add_parser("ballot", help="评分票（create = 一键建评分多维表格）")
    p.add_argument("action", choices=["create"])
    p.add_argument("--round", required=True, choices=list(settings.ROUNDS))

    p = sub.add_parser("tally", help="计票：拉取评分并统计")
    p.add_argument("--round", required=True, choices=list(settings.ROUNDS))

    p = sub.add_parser("reveal")
    p.add_argument("--round", required=True, choices=list(settings.ROUNDS))

    p = sub.add_parser("reset")
    p.add_argument("--round", required=True, choices=list(settings.ROUNDS))
    p.add_argument("--purge-feishu", action="store_true", help="同时删除飞书多维表格")

    sub.add_parser("demo")

    args = parser.parse_args()

    if args.cmd == "scenarios":
        commands.cmd_scenarios(args.round)
    elif args.cmd == "skills":
        commands.cmd_skills()
    elif args.cmd == "generate":
        commands.cmd_generate(args.round, args.model, args.workers)
    elif args.cmd == "delegate":
        if args.action == "plan":
            commands.cmd_delegate_plan(args.round)
        else:
            commands.cmd_delegate_collect(args.round)
    elif args.cmd == "skill":
        commands.cmd_skill_import(args.file, args.key, args.force)
    elif args.cmd == "present":
        if args.kind == "responses":
            commands.cmd_present_responses(args.round, args.open)
        elif args.kind == "ranking":
            commands.cmd_present_ranking(args.round, args.open)
        elif args.kind == "compare":
            if not args.left or not args.right:
                parser.error("present compare 需要 --left 与 --right（盲码，如 01 03）")
            commands.cmd_present_compare(args.round, args.left, args.right, args.open)
    elif args.cmd == "ballot":
        commands.cmd_ballot_create(args.round)
    elif args.cmd == "tally":
        commands.cmd_tally(args.round)
    elif args.cmd == "reveal":
        commands.cmd_reveal(args.round)
    elif args.cmd == "reset":
        commands.cmd_reset(args.round, args.purge_feishu)
    elif args.cmd == "demo":
        commands.cmd_demo()


if __name__ == "__main__":
    main()
