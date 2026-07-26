# -*- coding: utf-8 -*-
"""评分票服务：在飞书多维表格一键建好评分数据结构。

结构：每位评分人一行记录。
  昵称（文本） + 提交时间（自动） + 每个盲码 × 各维度单选（1–5 分，选项带方向标注，如 5（非常好））

建好后把链接交给领读人，在网页端基于该表创建「问卷视图」生成二维码即可。

【后端缝】评分收集后端是可替换的。一个后端要实现两件事：
1. 建表（本文件的 create_ballot），并把登记信息落盘到 survey_{round}.json
2. 供 tally_service 读取评分记录，记录形状统一为 {"fields": {字段名: 值}}
飞书后端 = BitableClient（注入点：create_ballot/tally 的 client 参数）。
CSV 后端（备忘录 B-001）按同一契约另写模块即可，本服务无需改动。
"""
import datetime
import time

from config import settings
from libs import store
from libs.feishu_bitable import BitableClient
from services import skill_service

TEXT, SINGLE_SELECT, CREATED_TIME = 1, 3, 1001


def _survey_path(round_name: str):
    return settings.RESULTS_DIR / f"survey_{round_name}.json"


def load_ballot(round_name: str) -> dict:
    return store.load_json(_survey_path(round_name), default={})


def score_field(code: str, dim: str) -> str:
    return f"{code}·{dim}"


def _score_options() -> list[dict]:
    """五分量表单选选项：分数（方向），如 5（非常好）。标签可在 course.yaml score.labels 配。"""
    return [{"name": f"{i}（{settings.SCORE_LABELS.get(i, '')}）"}
            for i in range(settings.SCORE_MIN, settings.SCORE_MAX + 1)]


def create_ballot(round_name: str, client: BitableClient | None = None) -> dict:
    settings.ensure_dirs()
    settings.require_feishu()

    existing = load_ballot(round_name)
    if existing.get("app_token") and existing.get("fields_ready"):
        return {**existing, "reused": True}

    blind = skill_service.get_blind_map(round_name)
    codes = sorted(blind)
    label = settings.ROUNDS[round_name]["label"]
    today = datetime.date.today().isoformat()

    client = client or BitableClient()
    if existing.get("app_token"):
        # 断点续建：复用已创建的库，只补后续步骤
        app_token = existing["app_token"]
        table_id = existing["table_id"]
        url = existing["url"]
    else:
        app = client.create_app(f"心眼子评分-{round_name}（{label}）-{today}")
        app_token = app["app_token"]
        table_id = app.get("default_table_id")
        url = app.get("url") or f"https://feishu.cn/base/{app_token}"

    # 建库成功立即落盘，后续步骤失败可断点重试
    data = {
        "round": round_name,
        "app_token": app_token,
        "table_id": table_id,
        "url": url,
        "codes": codes,
        "granted": False,
        "fields_ready": False,
        "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    store.save_json(_survey_path(round_name), data)

    # 默认表清理：主字段「文本」改名为「昵称」，删掼默认的「单选/日期/附件」
    print("  配置表结构…", flush=True)
    existing_names = set()
    for f in client.list_fields(app_token, table_id):
        fname, fid = f.get("field_name"), f["field_id"]
        if f.get("is_primary") or fname == "文本":
            if fname != "昵称":
                client.rename_field(app_token, table_id, fid, "昵称", f.get("type", TEXT))
                fname = "昵称"
        elif fname in ("单选", "日期", "附件"):
            client.delete_field(app_token, table_id, fid)
            continue
        existing_names.add(fname)

    wanted = ["提交时间"]
    for code in codes:
        for dim in settings.DIMS:
            wanted.append(score_field(code, dim))

    for name in wanted:
        if name in existing_names:
            continue
        print(f"  建字段 {name}", flush=True)
        time.sleep(0.4)  # 控制调用频率，避开飞书频率限制
        if name == "提交时间":
            client.create_field(app_token, table_id, name, CREATED_TIME)
        else:
            client.create_field(app_token, table_id, name, SINGLE_SELECT,
                                {"options": _score_options()})

    data["fields_ready"] = True
    data["granted"] = client.grant_full_access(app_token, settings.OWNER_OPEN_ID)
    store.save_json(_survey_path(round_name), data)
    return data
