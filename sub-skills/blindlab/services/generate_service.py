# -*- coding: utf-8 -*-
"""回应生成服务：skill × scenario → AI 回应。

实验控制：同一轮内所有 skill 使用同一模型、同一温度、同一提示词模板，
唯一变量是共读人写的「心法」内容。
结果增量落盘，中断后可断点续跑。
"""
import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import settings
from libs import store
from libs.llm import LLMClient
from services import scenario_service, skill_service


def _responses_path(round_name: str):
    return settings.RESULTS_DIR / f"responses_{round_name}.json"


def load_responses(round_name: str) -> dict:
    return store.load_json(_responses_path(round_name), default={})


def save_responses(round_name: str, data: dict) -> None:
    store.save_json(_responses_path(round_name), data)


def ensure_meta(data: dict, round_name: str, scenarios: list, blind: dict,
                model: str) -> dict:
    """补齐 responses 文件的元信息（deck/ingest 等下游都依赖这些字段）。"""
    data.setdefault("round", round_name)
    data["model"] = model
    data["label"] = settings.ROUNDS[round_name]["label"]
    data["blind"] = blind
    data["scenarios"] = [{"id": s["id"], "title": s["title"], "summary": s["summary"]}
                         for s in scenarios]
    return data


def generate_round(round_name: str, model: str | None = None, workers: int = 4) -> dict:
    settings.ensure_dirs()
    settings.require_llm()

    scenarios = scenario_service.list_scenarios(round_name)
    all_skills = skill_service.list_skills()
    # 裸 API 只跑简单心法；工作流型 skill 由 delegate plan/collect（OpenClaw 子进程）处理
    skills = [s for s in all_skills if s.get("kind") == "simple"]
    workflow_keys = {s["key"] for s in all_skills if s.get("kind") == "workflow"}
    data = load_responses(round_name)
    responses = data.setdefault("responses", {})
    # 盲码覆盖全部 skill（含工作流型），保证两条执行路径共用一套编号
    blind = skill_service.prune_blind_map(round_name, all_skills, responses)
    skill_by_key = {s["key"]: s for s in skills}

    ensure_meta(data, round_name, scenarios, blind, model or settings.LLM_MODEL)

    tasks = []
    for sc in scenarios:
        bucket = responses.setdefault(sc["id"], {})
        for code, skill_key in blind.items():
            if skill_key in workflow_keys:
                continue  # 工作流型不走 API
            if code not in bucket:
                tasks.append((sc, code, skill_key))

    api_total = len(scenarios) * (len(blind) - len(workflow_keys))
    if not tasks:
        data["generated_at"] = datetime.datetime.now().isoformat(timespec="seconds")
        store.save_json(_responses_path(round_name), data)
        return {"round": round_name, "new": 0, "total": api_total,
                "workflow": len(workflow_keys)}

    client = LLMClient(model=model) if model else LLMClient()
    lock = threading.Lock()
    errors = []

    def work(sc, code, skill_key):
        skill = skill_by_key[skill_key]
        scenario_text = (sc["before"] + "\n\n" + settings.RESPONSE_PLACEHOLDER
                         + "\n\n" + sc["after"]).strip()
        answer = client.chat(
            settings.SYSTEM_PROMPT,
            settings.USER_TEMPLATE.format(skill=skill["content"], scenario=scenario_text,
                                          placeholder=settings.RESPONSE_PLACEHOLDER),
        )
        with lock:
            responses[sc["id"]][code] = answer
            data["generated_at"] = datetime.datetime.now().isoformat(timespec="seconds")
            store.save_json(_responses_path(round_name), data)  # 增量落盘

    done = 0
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(work, sc, code, key): (sc["id"], code)
                   for sc, code, key in tasks}
        for fut in as_completed(futures):
            sc_id, code = futures[fut]
            try:
                fut.result()
                done += 1
                print(f"  [{done}/{len(tasks)}] 场景 {sc_id} · 回应 {code} 完成")
            except Exception as e:  # 单点失败不拖垮整轮
                errors.append({"scenario": sc_id, "code": code, "error": str(e)})
                print(f"  !! 场景 {sc_id} · 回应 {code} 失败: {e}")

    if errors:
        data["errors"] = errors
        store.save_json(_responses_path(round_name), data)
    return {"round": round_name, "new": done, "failed": len(errors),
            "total": api_total, "workflow": len(workflow_keys)}
