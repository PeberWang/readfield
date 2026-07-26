# -*- coding: utf-8 -*-
"""命令编排：每个函数对应一条 CLI 命令，只做串联与输出。"""
import datetime
import os
import random
import shutil
from pathlib import Path

from config import settings
from libs import store
from services import (ballot_service, delegate_service, generate_service,
                      present_service, scenario_service, skill_service,
                      tally_service)


def cmd_scenarios(round_name: str) -> None:
    for sc in scenario_service.list_scenarios(round_name):
        print(f"  {sc['id']}  {sc['title']}  （{sc['summary'] or '无梗概'}）")


def cmd_skills() -> None:
    for s in skill_service.list_skills():
        author = f"（{s['author']}）" if s["author"] else ""
        kind = "工作流" if s.get("kind") == "workflow" else "简单心法"
        if skill_service.is_baseline(s["key"]):
            kind += "·基线"
        print(f"  {s['key']}  {s['name']}{author}  [{kind}，{len(s['content'])} 字]")


def cmd_generate(round_name: str, model: str | None, workers: int) -> None:
    print(f"开始生成回应：轮次 {round_name}（{settings.ROUNDS[round_name]['label']}）")
    result = generate_service.generate_round(round_name, model=model, workers=workers)
    failed = result.get("failed", 0)
    tail = f"，失败 {failed}" if failed else ""
    print(f"完成：新增 {result['new']} 条，API 路径总计 {result['total']} 条{tail}。"
          f"结果在 data/results/responses_{round_name}.json")
    if result.get("workflow"):
        print(f"另有 {result['workflow']} 个工作流型 skill 不走 API："
              f"请执行 delegate plan --round {round_name} 生成清单，由子进程跑完后 delegate collect。")


def cmd_delegate_plan(round_name: str) -> None:
    plan = delegate_service.plan(round_name)
    print(f"委托任务清单已生成：data/results/agent_plan_{round_name}.json")
    if not plan["tasks"]:
        print("  没有待办任务（都已产出或已并入）。删除对应输出 JSON 可重新入单。")
        return
    by_skill: dict[str, list] = {}
    for t in plan["tasks"]:
        by_skill.setdefault(t["code"], []).append(t)
    print(f"  待办 {len(plan['tasks'])} 条（{len(by_skill)} 个 skill，每个 spawn 一个子进程）：")
    for code, ts in by_skill.items():
        scs = "、".join(t["scenario_id"] for t in ts)
        print(f"    回应 {code}（{ts[0]['skill_name']}）→ 场景：{scs}")


def cmd_delegate_collect(round_name: str) -> None:
    result = delegate_service.collect(round_name)
    for tag in result["ingested"]:
        print(f"  [OK] 已并入 {tag}")
    for p in result["problems"]:
        print(f"  !! {p}")
    if result["ingested"]:
        print(f"完成：{len(result['ingested'])} 条回应已并入 data/results/responses_{round_name}.json")
    elif not result["problems"]:
        print("没有新的产出可并入。")


def cmd_present_responses(round_name: str, open_after: bool) -> None:
    scenarios = scenario_service.list_scenarios(round_name)
    data = generate_service.load_responses(round_name)
    if not data.get("responses"):
        raise SystemExit(f"还没有回应数据，请先执行 generate --round {round_name}")
    codes = sorted(data["blind"])
    out = settings.OUTPUT_DIR / f"responses_{round_name}.html"
    present_service.present_responses(data["label"], scenarios, data["responses"], codes, out)
    print(f"回应展示页已生成：{out}")
    if open_after:
        os.startfile(out)  # type: ignore[attr-defined]


def cmd_ballot_create(round_name: str) -> None:
    data = ballot_service.create_ballot(round_name)
    if data.pop("reused", False):
        print(f"轮次 {round_name} 的评分表已存在，直接复用：")
    else:
        print("评分多维表格已创建：")
    print(f"  链接：{data['url']}")
    print(f"  字段：昵称 + {len(data['codes'])} 个盲码 × （{'/'.join(settings.DIMS)}，单选 1–5 带方向标注）")
    if data.get("granted"):
        print("  已把你加为协作者，链接可直接打开。")
    else:
        print("  !! 自动授权未成功（应用可能缺少 drive 权限）。若链接打不开，请告诉我。")
    print("  下一步：在网页打开链接 → 基于该表创建「问卷」视图 → 生成二维码发给大家。")


def cmd_tally(round_name: str) -> None:
    data = tally_service.tally(round_name)
    print(f"已拉取评分：{data['voters']} 人提交（data/results/scores_{round_name}.json）")
    if not data["ranking"]:
        print("  尚无有效评分数据。")
        return
    print("  当前排名（总均分）：")
    for i, code in enumerate(data["ranking"], start=1):
        s = data["codes"][code]
        print(f"    #{i} 回应 {code}  总分 {s['total_mean']:.2f}  "
              f"（{' / '.join(str(s['dims'][d]['mean']) for d in settings.DIMS)}）")


def cmd_present_ranking(round_name: str, open_after: bool) -> None:
    rounds = list(settings.ROUNDS) if round_name == "all" else [round_name]
    scores_by_round = {}
    for r in rounds:
        scores = tally_service.load_scores(r)
        if scores.get("ranking"):
            scores_by_round[r] = scores
    if not scores_by_round:
        raise SystemExit("还没有评分数据，请先执行 tally")
    suffix = "all" if round_name == "all" else round_name
    out = settings.OUTPUT_DIR / f"ranking_{suffix}.html"
    present_service.present_ranking(scores_by_round, out)
    print(f"排名展示页已生成：{out}")
    if open_after:
        os.startfile(out)  # type: ignore[attr-defined]


def cmd_present_compare(round_name: str, left: str, right: str, open_after: bool) -> None:
    left, right = left.zfill(2), right.zfill(2)
    scenarios = scenario_service.list_scenarios(round_name)
    data = generate_service.load_responses(round_name)
    if not data.get("responses"):
        raise SystemExit(f"还没有回应数据，请先执行 generate --round {round_name}")
    scores = tally_service.load_scores(round_name)
    out = settings.OUTPUT_DIR / f"compare_{round_name}_{left}_vs_{right}.html"
    present_service.present_compare(data["label"], scenarios, data["responses"],
                                    scores, left, right, out)
    print(f"对比展示页已生成：{out}（回应 {left} × 回应 {right}）")
    if open_after:
        os.startfile(out)  # type: ignore[attr-defined]


def cmd_skill_import(file_path: str, key: str | None, force: bool) -> None:
    path = Path(file_path)
    if not path.exists():
        raise SystemExit(f"文件不存在：{path}")
    if path.suffix.lower() == ".zip":
        result = skill_service.import_skill_zip(path, key, force=force)
    else:
        if not key:
            raise SystemExit("文本通道必须指定 --key（zip 通道可省略，默认取 zip 内文件夹名）")
        result = skill_service.import_skill(path.read_text(encoding="utf-8"),
                                            key, force=force)
    print(f"skill 已落地：data/skills/{result['key']}/（{result['name']}，作者：{result['author'] or '未填'}）")
    for rel in result["files"]:
        print(f"  {rel}")
    if not result["author"]:
        print("  !! SKILL.md 的 author 为空，揭晓环节将无法署名，请提醒小组补上。")
    print("用 skills 命令可确认它已被管道识别。")


def cmd_reveal(round_name: str) -> None:
    mapping = skill_service.reveal(round_name)
    print(f"轮次 {round_name} 盲码揭晓：")
    for code, info in mapping.items():
        author = f"（作者：{info['author']}）" if info["author"] else ""
        print(f"  回应 {code} = {info['name']}{author}")


def cmd_reset(round_name: str, purge_feishu: bool) -> None:
    """清场：删除本轮全部运行状态（盲码/回应/评分表登记/评分），可选同时删飞书表。"""
    survey = ballot_service.load_ballot(round_name)
    if purge_feishu and survey.get("app_token"):
        from libs.feishu_bitable import BitableClient
        ok = BitableClient().delete_app(survey["app_token"])
        print(f"  飞书表 {'已删除' if ok else '删除失败（可手动删）'}: {survey['url']}")
    removed = []
    for name in ("blind", "responses", "survey", "scores", "agent_plan", "agentic"):
        path = settings.RESULTS_DIR / f"{name}_{round_name}.json"
        if path.exists():
            path.unlink()
            removed.append(path.name)
    # 子进程产出与中间文档也要清，否则旧契约 JSON 可能被 collect 误并进新一轮
    for d in (settings.AGENTIC_DIR / round_name, settings.AGENTIC_WORK_DIR / round_name):
        if d.exists():
            shutil.rmtree(d)
            removed.append(d.name + "/")
    print(f"轮次 {round_name} 已清场：{', '.join(removed) if removed else '（本来就没有状态文件）'}")


def cmd_demo() -> None:
    """用内置 mock 数据走通全部展示页，不调用任何外部 API。"""
    settings.ensure_dirs()
    print("demo：生成 mock 回应与评分，产出三种展示页到 output/demo/")

    scenarios = scenario_service.list_scenarios("day1")
    codes = ["01", "02", "03"]
    canned = {
        "01": "我抬起头，看着莫慕斯：「我可以回答你的问题。但我想先知道，这次审问记录会送到谁的手里，我有没有权利知道它的用途？」",
        "02": "我笑了笑，给莫慕斯让了个座：「先生远道而来辛苦了。审问当然配合，不过我们乡下人不懂规矩，您多担待，咱们慢慢聊。」",
        "03": "我沉默了一会儿，说：「在我弄明白自己为什么被传唤之前，我恐怕没什么好说的。」",
    }
    responses = {sc["id"]: dict(canned) for sc in scenarios}
    out1 = settings.OUTPUT_DIR / "demo" / "responses_demo.html"
    present_service.present_responses("城堡情境（demo）", scenarios, responses, codes, out1)

    random.seed(42)
    scores = {"round": "demo", "label": "城堡情境（demo）", "voters": 12,
              "codes": {}, "ranking": []}
    base = {"01": 4.3, "02": 3.6, "03": 2.8}
    for code in codes:
        dims = {}
        for dim in settings.DIMS:
            dims[dim] = {"mean": round(base[code] + random.uniform(-0.3, 0.3), 2), "n": 12}
        total = round(sum(d["mean"] for d in dims.values()) / len(dims), 2)
        scores["codes"][code] = {"dims": dims, "total_mean": total, "n_scores": 36,
                                 "comments": ["这个回应明显读懂了权力关系。", "措辞有点像真人。"]}
    scores["ranking"] = sorted(codes, key=lambda c: scores["codes"][c]["total_mean"],
                               reverse=True)
    out2 = settings.OUTPUT_DIR / "demo" / "ranking_demo.html"
    present_service.present_ranking({"demo": scores}, out2)

    out3 = settings.OUTPUT_DIR / "demo" / "compare_demo.html"
    present_service.present_compare("城堡情境（demo）", scenarios, responses,
                                    scores, "01", "03", out3)
    for p in (out1, out2, out3):
        print(f"  {p}")
