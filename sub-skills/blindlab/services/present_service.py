# -*- coding: utf-8 -*-
"""展示页服务：生成自包含 HTML 幻灯片（浏览器打开、方向键翻页、可投影）。

三类展示页：
- responses：盲评回应展示（情境黑字 + AI 回应红字）
- ranking：评分统计与排名可视化
- compare：任意两个盲码的左右分栏对比
"""
import html
from pathlib import Path

from config import settings

MAX_SCORE = float(settings.SCORE_MAX)


def _esc(text) -> str:
    return html.escape(str(text), quote=False)


def _paragraphs(text: str) -> str:
    parts = [p.strip() for p in text.split("\n\n") if p.strip()]
    return "".join(f"<p>{_esc(p).replace(chr(10), '<br>')}</p>" for p in parts)


def _scenario_html(scenario: dict, response: str | None) -> str:
    """情境正文：旁白黑字，AI 回应红字。无回应时占位符显示为下划线空位。"""
    out = []
    if scenario["before"]:
        out.append(_paragraphs(scenario["before"]))
    if response:
        out.append(f'<p class="response">{_esc(response).replace(chr(10), "<br>")}</p>')
    else:
        out.append('<p class="response blank">＿＿＿＿＿＿＿＿＿＿</p>')
    if scenario["after"]:
        out.append(_paragraphs(scenario["after"]))
    return "".join(out)


_BASE_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", sans-serif;
       background: #fafaf7; color: #1a1a1a; overflow: hidden; }
.slide { display: none; width: 100vw; height: 100vh; padding: 5vh 7vw 8vh;
         flex-direction: column; }
.slide.active { display: flex; }
.deck-header { font-size: 1.6vh; color: #777; letter-spacing: .1em;
               margin-bottom: 2vh; display: flex; justify-content: space-between; }
.counter { position: fixed; right: 2vw; bottom: 2vh; font-size: 1.6vh; color: #999; }
h1.title { font-size: 5vh; margin-bottom: 1vh; }
.subtitle { font-size: 2.4vh; color: #777; margin-bottom: 3vh; }
h2 { font-size: 3.2vh; margin-bottom: 2.2vh; }
h2 .tag { color: #c0392b; }
.body { flex: 1; overflow-y: auto; font-size: 2.3vh; line-height: 1.9; }
.body p { margin-bottom: 1.2em; }
.body p.response { color: #b91c1c; font-weight: 600; }
.body p.response.blank { color: #bbb; font-weight: 400; }
.divider-slide { flex: 1; display: flex; flex-direction: column; justify-content: center; }
.big-code { font-size: 12vh; color: #c0392b; font-weight: 700; }
.bar-row { display: flex; align-items: center; margin-bottom: 1.6vh; gap: 1.5vw; }
.bar-label { width: 9vw; font-size: 2.4vh; text-align: right; flex-shrink: 0; }
.bar-track { flex: 1; background: #eceae4; border-radius: 4px; height: 3.4vh; position: relative; }
.bar-fill { height: 100%; border-radius: 4px; background: #3a3a38; }
.bar-fill.first { background: #c0392b; }
.bar-fill.b { background: #8e44ad; }
.bar-value { width: 7vw; font-size: 2.2vh; color: #555; flex-shrink: 0; }
table.score { border-collapse: collapse; font-size: 2.2vh; margin-top: 1vh; }
table.score th, table.score td { border: 1px solid #ddd; padding: .9vh 1.6vw; text-align: center; }
table.score th { background: #f0eee8; }
.two-col { display: flex; gap: 2.5vw; flex: 1; min-height: 0; align-items: stretch; }
.col { flex: 1; border: 1px solid #e2dfd6; border-radius: 8px; padding: 2.5vh 2vw;
       overflow-y: auto; background: #fff; }
.col-head { font-size: 2.6vh; font-weight: 700; margin-bottom: 1.5vh; }
.col-head .mean { color: #c0392b; font-weight: 600; font-size: 2vh; margin-left: 1em; }
.col .resp { font-size: 2.5vh; line-height: 1.85; color: #b91c1c; font-weight: 600; }
.col .resp p { margin-bottom: 1em; }
.scenario-brief { font-size: 2vh; color: #666; background: #f0eee8; border-radius: 6px;
                  padding: 1.2vh 1.5vw; margin-bottom: 2vh; line-height: 1.7; }
.comment { font-size: 2vh; color: #555; border-left: 3px solid #c0392b; padding-left: 1em;
           margin-bottom: 1em; line-height: 1.7; }
.legend { font-size: 1.8vh; color: #888; margin-top: 1vh; }
"""

_BASE_JS = """
let idx = 0;
const slides = document.querySelectorAll('.slide');
function fit(slide) {
  const body = slide.querySelector('.body');
  if (!body) return;
  let size = 2.3;
  body.style.fontSize = size + 'vh';
  while (size > 1.5 && body.scrollHeight > body.clientHeight) {
    size -= 0.1;
    body.style.fontSize = size + 'vh';
  }
}
function show(i) {
  idx = Math.max(0, Math.min(i, slides.length - 1));
  slides.forEach((s, k) => s.classList.toggle('active', k === idx));
  document.getElementById('counter').textContent = (idx + 1) + ' / ' + slides.length;
  fit(slides[idx]);
}
document.addEventListener('keydown', e => {
  if (['ArrowRight', 'PageDown', ' '].includes(e.key)) show(idx + 1);
  if (['ArrowLeft', 'PageUp'].includes(e.key)) show(idx - 1);
  if (e.key === 'Home') show(0);
  if (e.key === 'End') show(slides.length - 1);
});
document.addEventListener('click', e => {
  if (e.clientX > window.innerWidth * 0.82) show(idx + 1);
  else if (e.clientX < window.innerWidth * 0.18) show(idx - 1);
});
window.addEventListener('resize', () => fit(slides[idx]));
show(0);
"""


def render_deck(deck_title: str, slides_html: list[str], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(
        f'<section class="slide"><div class="deck-header"><span>{_esc(deck_title)}</span>'
        f'<span>心眼子 · 知合 NEXUS 2026</span></div>{s}</section>'
        for s in slides_html
    )
    doc = (f"<!DOCTYPE html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
           f"<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
           f"<title>{_esc(deck_title)}</title><style>{_BASE_CSS}</style></head><body>"
           f"{body}<div class=\"counter\" id=\"counter\"></div>"
           f"<script>{_BASE_JS}</script></body></html>")
    out_path.write_text(doc, encoding="utf-8")
    return out_path


def _bar(label: str, value: float | None, extra: str = "", klass: str = "") -> str:
    pct = 0 if value is None else max(0.0, min(1.0, value / MAX_SCORE)) * 100
    val = "—" if value is None else f"{value:.2f}"
    return (f'<div class="bar-row"><div class="bar-label">{_esc(label)}</div>'
            f'<div class="bar-track"><div class="bar-fill {klass}" style="width:{pct:.1f}%"></div></div>'
            f'<div class="bar-value">{val}{extra}</div></div>')


# ---------- responses deck ----------

def present_responses(round_label: str, scenarios: list[dict], responses: dict,
                      codes: list[str], out_path: Path) -> Path:
    n = len(codes)
    slides = [
        f'<div class="divider-slide"><h1 class="title">盲评回应展示</h1>'
        f'<div class="subtitle">{_esc(round_label)} · {n} 份回应 × {len(scenarios)} 个情境</div>'
        f'<div class="legend">黑字为情境旁白，<span style="color:#c0392b">红字为该回应的主人公反应</span>。'
        f'请记住每份回应的编号，打分环节只认编号。</div></div>'
    ]
    for code in codes:
        slides.append(
            f'<div class="divider-slide"><div class="big-code">回应 {code}</div>'
            f'<div class="subtitle">{len(scenarios)} 个情境，依次呈现</div></div>'
        )
        for sc in scenarios:
            resp = responses.get(sc["id"], {}).get(code, "")
            slides.append(
                f'<h2><span class="tag">回应 {code}</span> · 情境「{_esc(sc["title"])}」</h2>'
                f'<div class="body">{_scenario_html(sc, resp or None)}</div>'
            )
    return render_deck(f"盲评回应展示 · {round_label}", slides, out_path)


# ---------- ranking deck ----------

def present_ranking(scores_by_round: dict[str, dict], out_path: Path) -> Path:
    rounds = list(scores_by_round)
    first = scores_by_round[rounds[0]]
    cross = len(rounds) > 1
    title = "评分排名 · " + (" × ".join(scores_by_round[r]["label"] for r in rounds) if cross
                             else first["label"])

    slides = [
        f'<div class="divider-slide"><h1 class="title">盲评排名揭晓</h1>'
        f'<div class="subtitle">{_esc(title)} · {first["voters"]} 人参与评分</div>'
        f'<div class="legend">各维度 {settings.SCORE_MIN}–{int(MAX_SCORE)} 分：'
        f'{" / ".join(settings.DIMS)}；总分为各维度合并均分。</div></div>'
    ]

    # 总排名
    rows = []
    for i, code in enumerate(first["ranking"]):
        s = first["codes"][code]
        rows.append(_bar(f"#{i + 1} 回应 {code}", s["total_mean"],
                         extra=f"　n={s['n_scores']}", klass="first" if i == 0 else ""))
    slides.append(f"<h2>总排名（{_esc(first['label'])}）</h2><div>{''.join(rows)}</div>")

    # 分维度
    for dim in settings.DIMS:
        stats = [(c, first["codes"][c]["dims"][dim]["mean"]) for c in first["codes"]]
        stats = [x for x in stats if x[1] is not None]
        stats.sort(key=lambda x: x[1], reverse=True)
        rows = [_bar(f"回应 {c}", v, klass="first" if i == 0 else "")
                for i, (c, v) in enumerate(stats)]
        slides.append(f"<h2>维度 · {_esc(dim)}（{_esc(first['label'])}）</h2><div>{''.join(rows)}</div>")

    # 明细表
    head = "".join(f"<th>{_esc(d)}</th>" for d in settings.DIMS)
    lines = []
    for i, code in enumerate(first["ranking"]):
        s = first["codes"][code]
        tds = "".join(
            f"<td>{'—' if s['dims'][d]['mean'] is None else format(s['dims'][d]['mean'], '.2f')}</td>"
            for d in settings.DIMS)
        lines.append(f"<tr><td>#{i + 1} 回应 {code}</td>{tds}<td><b>{s['total_mean']:.2f}</b></td></tr>")
    slides.append(f"<h2>评分明细（{_esc(first['label'])}）</h2>"
                  f'<table class="score"><tr><th>回应</th>{head}<th>总均分</th></tr>{"".join(lines)}</table>')

    # 跨天对照
    if cross:
        second = scores_by_round[rounds[1]]
        rank1 = {c: i + 1 for i, c in enumerate(first["ranking"])}
        rank2 = {c: i + 1 for i, c in enumerate(second["ranking"])}
        union = [c for c in first["ranking"] if c in second["codes"]]
        for c in second["ranking"]:
            if c not in union:
                union.append(c)
        rows = []
        for code in union:
            v1 = first["codes"].get(code, {}).get("total_mean")
            v2 = second["codes"].get(code, {}).get("total_mean")
            r1, r2 = rank1.get(code, "—"), rank2.get(code, "—")
            delta = ""
            if isinstance(r1, int) and isinstance(r2, int):
                change = r1 - r2
                delta = f" ↑{change}" if change > 0 else (f" ↓{-change}" if change < 0 else " →")
            rows.append(
                f'<div class="bar-row"><div class="bar-label">回应 {code}</div>'
                f'<div class="bar-track" style="margin-bottom:4px"><div class="bar-fill first" '
                f'style="width:{(v1 or 0) / MAX_SCORE * 100:.1f}%"></div></div>'
                f'<div class="bar-track"><div class="bar-fill b" '
                f'style="width:{(v2 or 0) / MAX_SCORE * 100:.1f}%"></div></div>'
                f'<div class="bar-value">#{r1}→#{r2}{delta}</div></div>'
            )
        slides.append(
            f"<h2>语境迁移对照：{_esc(first['label'])}（红） × {_esc(second['label'])}（紫）</h2>"
            f"<div>{''.join(rows)}</div>"
            f'<div class="legend">同一份心法在两个语境中的排名变化。谁稳住了？谁掉队了？为什么？</div>'
        )

    # 评语摘录
    comment_blocks = []
    for code in first["ranking"]:
        comments = first["codes"][code].get("comments", [])[:3]
        if comments:
            items = "".join(f'<div class="comment">{_esc(c)}</div>' for c in comments)
            comment_blocks.append(f"<h2 style=\"font-size:2.4vh\">回应 {code}</h2>{items}")
    if comment_blocks:
        slides.append(f"<h2>评分人评语摘录（{_esc(first['label'])}）</h2>"
                      f'<div class="body">{"".join(comment_blocks)}</div>')

    return render_deck(title, slides, out_path)


# ---------- compare deck ----------

def present_compare(round_label: str, scenarios: list[dict], responses: dict,
                    scores: dict, left: str, right: str, out_path: Path) -> Path:
    stats = scores.get("codes", {}) if scores else {}

    def mean(code: str, dim: str):
        return stats.get(code, {}).get("dims", {}).get(dim, {}).get("mean")

    def total(code: str):
        return stats.get(code, {}).get("total_mean")

    slides = []
    face = []
    for dim in settings.DIMS:
        face.append(
            f'<div class="bar-row"><div class="bar-label">{_esc(dim)}</div>'
            f'<div class="bar-track"><div class="bar-fill first" '
            f'style="width:{(mean(left, dim) or 0) / MAX_SCORE * 100:.1f}%"></div></div>'
            f'<div class="bar-value">{left} {"—" if mean(left, dim) is None else format(mean(left, dim), ".2f")}</div>'
            f'<div class="bar-track"><div class="bar-fill b" '
            f'style="width:{(mean(right, dim) or 0) / MAX_SCORE * 100:.1f}%"></div></div>'
            f'<div class="bar-value">{right} {"—" if mean(right, dim) is None else format(mean(right, dim), ".2f")}</div>'
            f'</div>'
        )
    slides.append(
        f'<div class="divider-slide"><h1 class="title">回应 {left} × 回应 {right}</h1>'
        f'<div class="subtitle">{_esc(round_label)} · 总均分 '
        f'{"—" if total(left) is None else format(total(left), ".2f")} : '
        f'{"—" if total(right) is None else format(total(right), ".2f")}</div>'
        f'<div style="margin-top:3vh">{"".join(face)}</div>'
        f'<div class="legend">红条 = 回应 {left}，紫条 = 回应 {right}。为什么前者比后者好（或差）？差异从哪里来？</div></div>'
    )

    for sc in scenarios:
        l_resp = responses.get(sc["id"], {}).get(left, "（无回应）")
        r_resp = responses.get(sc["id"], {}).get(right, "（无回应）")
        brief = sc["summary"] or (sc["before"][:120] + "……")
        slides.append(
            f'<h2>情境「{_esc(sc["title"])}」</h2>'
            f'<div class="scenario-brief">{_esc(brief)}</div>'
            f'<div class="two-col">'
            f'<div class="col"><div class="col-head">回应 {left}'
            f'<span class="mean">总均分 {"—" if total(left) is None else format(total(left), ".2f") + " / 5"}</span></div>'
            f'<div class="resp">{_paragraphs(l_resp)}</div></div>'
            f'<div class="col"><div class="col-head">回应 {right}'
            f'<span class="mean">总均分 {"—" if total(right) is None else format(total(right), ".2f") + " / 5"}</span></div>'
            f'<div class="resp">{_paragraphs(r_resp)}</div></div>'
            f'</div>'
        )
    return render_deck(f"对比 · 回应 {left} × 回应 {right} · {round_label}", slides, out_path)
