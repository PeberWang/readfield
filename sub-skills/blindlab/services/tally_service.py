# -*- coding: utf-8 -*-
"""计票服务：从评分后端拉取评分，计算各维度均分与排名。

字段名兼容：以「盲码·维度」为基准，同时容忍手动微调过的常见变体。

【后端缝】_fetch_records 是评分后端唯一进入点。后端契约：
返回 [{"fields": {字段名: 值}}, ...] 形状的记录列表（见 ballot_service 文档）。
聚合逻辑与后端无关，CSV 后端（备忘录 B-001）只需在 _fetch_records 处分流。
"""
import datetime
import re

from config import settings
from libs import store
from libs.feishu_bitable import BitableClient
from services import ballot_service

# 「01·自然」「01-技巧」「回应01·远见」等变体；维度名取自 course.yaml，不写死
_DIMS_PATTERN = "|".join(re.escape(d) for d in settings.DIMS)
_FIELD_RE = re.compile(rf"^(?:回应)?(\d{{1,2}})\s*[·\-—.:：]?\s*({_DIMS_PATTERN})$")


def _scores_path(round_name: str):
    return settings.RESULTS_DIR / f"scores_{round_name}.json"


def load_scores(round_name: str) -> dict:
    return store.load_json(_scores_path(round_name), default={})


def _to_float(value) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            m = re.match(r"^\s*(\d+(?:\.\d+)?)", value)  # 单选选项形如「5（非常好）」
            return float(m.group(1)) if m else None
    if isinstance(value, list) and value:  # 个别字段类型可能返回数组
        return _to_float(value[0])
    return None


def _fetch_records(survey: dict, client: BitableClient) -> list:
    """评分后端的唯一读取点。返回 [{"fields": {字段名: 值}}, ...]。

    未来接入 CSV 后端（B-001）时在此按 survey 登记信息分流，
    把 CSV 行适配成同一形状即可，下游聚合逻辑不变。
    """
    return client.list_records(survey["app_token"], survey["table_id"])


def tally(round_name: str, client: BitableClient | None = None) -> dict:
    settings.ensure_dirs()
    settings.require_feishu()

    survey = ballot_service.load_ballot(round_name)
    if not survey.get("app_token"):
        raise SystemExit(f"轮次 {round_name} 还没有评分表，请先执行 ballot create --round {round_name}")

    client = client or BitableClient()
    records = _fetch_records(survey, client)

    raw: dict[str, dict[str, list]] = {}
    voters = 0
    for rec in records:
        fields = rec.get("fields", {})
        voted = False
        for fname, value in fields.items():
            m = _FIELD_RE.match(str(fname))
            if m:
                code = m.group(1).zfill(2)
                dim = m.group(2)
                score = _to_float(value)
                if score is None:
                    continue
                raw.setdefault(code, {}).setdefault(dim, []).append(score)
                voted = True
        if voted:
            voters += 1

    codes_stats = {}
    for code, dims in raw.items():
        dim_stats = {}
        all_scores = []
        for dim in settings.DIMS:
            values = dims.get(dim, [])
            if values:
                dim_stats[dim] = {"mean": round(sum(values) / len(values), 2), "n": len(values)}
                all_scores.extend(values)
            else:
                dim_stats[dim] = {"mean": None, "n": 0}
        total = round(sum(all_scores) / len(all_scores), 2) if all_scores else None
        codes_stats[code] = {
            "dims": dim_stats,
            "total_mean": total,
            "n_scores": len(all_scores),
        }

    ranked = sorted(
        (c for c, s in codes_stats.items() if s["total_mean"] is not None),
        key=lambda c: codes_stats[c]["total_mean"], reverse=True,
    )

    data = {
        "round": round_name,
        "label": settings.ROUNDS[round_name]["label"],
        "pulled_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "voters": voters,
        "codes": codes_stats,
        "ranking": ranked,
    }
    store.save_json(_scores_path(round_name), data)
    return data
