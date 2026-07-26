# -*- coding: utf-8 -*-
"""委托执行服务：工作流型 skill 的任务清单（plan）与结果回收（collect）。

执行模型：每个工作流型 skill 由一个 OpenClaw 子进程执行。子进程读 skill
文件夹里的 SKILL.md，按其中定义的工作流逐步处理场景（场景判别、中间分析
文档、playbook 调取等），最终把契约 JSON 写到 AGENTIC_DIR。

管道本身不 spawn 子进程——编排由小劳（OpenClaw 主 session）完成：
    1. blindlab.py delegate plan --round R    生成任务清单 agent_plan_R.json
    2. 小劳按清单 spawn 子进程（每个 skill 一个，处理该 skill 全部待办场景）
    3. blindlab.py delegate collect --round R 校验契约 JSON，并入 responses_R.json

契约 JSON（子进程写到 AGENTIC_DIR/<round>/<scenario_id>/<code>.json）：
    {
      "response": "主人公在 [[response]] 处的回应（必填，唯一进入盲评的文本）",
      "analysis": "工作流判断过程简述（必填，揭晓环节教学素材）",
      "scene_type": "判别出的场景类型（可选）",
      "notes": "任意备注（可选）"
    }
中间文档由子进程写到 AGENTIC_WORK_DIR/<round>/<code>/<scenario_id>/，
collect 时会登记到 agentic_R.json 备查。
"""
import datetime
import json
from pathlib import Path

from config import settings
from libs import store
from services import generate_service, scenario_service, skill_service

# 契约必填字段
REQUIRED_FIELDS = ("response", "analysis")


def _plan_path(round_name: str) -> Path:
    return settings.RESULTS_DIR / f"agent_plan_{round_name}.json"


def _sidecar_path(round_name: str) -> Path:
    return settings.RESULTS_DIR / f"agentic_{round_name}.json"


def plan(round_name: str, skip_existing: bool = True) -> dict:
    """生成委托任务清单。已并入或输出 JSON 已存在的任务自动跳过。"""
    settings.ensure_dirs()
    scenarios = scenario_service.list_scenarios(round_name)
    all_skills = skill_service.list_skills()
    wf_skills = {s["key"]: s for s in all_skills if s.get("kind") == "workflow"}
    if not wf_skills:
        raise SystemExit("没有工作流型 skill（data/skills/ 下需要含 SKILL.md 的文件夹）")

    data = generate_service.load_responses(round_name)
    responses = data.get("responses", {})
    blind = skill_service.prune_blind_map(round_name, all_skills, responses)

    tasks = []
    for code, skill_key in sorted(blind.items()):
        skill = wf_skills.get(skill_key)
        if not skill:
            continue
        for sc in scenarios:
            if code in responses.get(sc["id"], {}):
                continue  # 已并入
            out = settings.AGENTIC_DIR / round_name / sc["id"] / f"{code}.json"
            if skip_existing and out.exists():
                continue  # 子进程已产出，等 collect（删文件可重新入单）
            tasks.append({
                "code": code,
                "skill_key": skill_key,
                "skill_name": skill["name"],
                "skill_dir": skill["dir"],
                "scenario_id": sc["id"],
                "scenario_title": sc["title"],
                "scenario_path": sc["path"],
                "work_dir": str(settings.AGENTIC_WORK_DIR / round_name / code / sc["id"]),
                "output": str(out),
            })

    plan = {
        "round": round_name,
        "label": settings.ROUNDS[round_name]["label"],
        "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "placeholder": settings.RESPONSE_PLACEHOLDER,
        "contract": {
            "required": list(REQUIRED_FIELDS),
            "schema": {"response": "str 主人公回应（必填）",
                       "analysis": "str 工作流判断简述（必填）",
                       "scene_type": "str 场景类型（可选）",
                       "notes": "str 备注（可选）"},
        },
        "tasks": tasks,
    }
    store.save_json(_plan_path(round_name), plan)
    return plan


def collect(round_name: str) -> dict:
    """校验 AGENTIC_DIR 下的契约 JSON，并入 responses_{round}.json。

    幂等：重复执行覆盖同一 code 的回应，不产生重复条目。
    返回 {ingested: [...], problems: [...]}。
    """
    base = settings.AGENTIC_DIR / round_name
    if not base.exists():
        return {"ingested": [], "problems": [f"目录不存在：{base}（子进程尚未产出）"]}

    scenarios = scenario_service.list_scenarios(round_name)
    all_skills = skill_service.list_skills()
    skill_by_key = {s["key"]: s for s in all_skills}
    data = generate_service.load_responses(round_name)
    responses = data.setdefault("responses", {})
    blind = skill_service.prune_blind_map(round_name, all_skills, responses)
    generate_service.ensure_meta(data, round_name, scenarios, blind,
                                 model="openclaw-subagent")

    sidecar = store.load_json(_sidecar_path(round_name),
                              default={"round": round_name, "items": {}})
    ingested, problems = [], []

    for sc_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        sc_id = sc_dir.name
        if sc_id not in {s["id"] for s in scenarios}:
            problems.append(f"{sc_id}: 不在本轮场景库中，已跳过")
            continue
        for f in sorted(sc_dir.glob("*.json")):
            code = f.stem
            tag = f"{sc_id}/{code}"
            if code not in blind:
                problems.append(f"{tag}: 盲码 {code} 不在映射中，已跳过")
                continue
            try:
                item = json.loads(f.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                problems.append(f"{tag}: JSON 解析失败（{e}）")
                continue
            missing = [k for k in REQUIRED_FIELDS
                       if not isinstance(item.get(k), str) or not item[k].strip()]
            if missing:
                problems.append(f"{tag}: 缺少必填字段 {missing}")
                continue
            responses.setdefault(sc_id, {})[code] = item["response"].strip()
            sidecar["items"][tag] = {
                "skill_key": blind[code],
                "skill_name": skill_by_key.get(blind[code], {}).get("name", blind[code]),
                "analysis": item["analysis"].strip(),
                "scene_type": item.get("scene_type", ""),
                "notes": item.get("notes", ""),
                "work_dir": str(settings.AGENTIC_WORK_DIR / round_name / code / sc_id),
                "ingested_at": datetime.datetime.now().isoformat(timespec="seconds"),
            }
            ingested.append(tag)

    if ingested:
        data["generated_at"] = datetime.datetime.now().isoformat(timespec="seconds")
        generate_service.save_responses(round_name, data)
        store.save_json(_sidecar_path(round_name), sidecar)
    return {"ingested": ingested, "problems": problems}
