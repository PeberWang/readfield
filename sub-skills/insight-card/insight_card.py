"""
Insight Card — ReadField 社群轻量分享图生成器

生成社群中非课程主线的、话题驱动的轻量分享卡。
输出单张 PNG（2x 高清），适合直接发微信社群。

依赖：pip install playwright && playwright install chromium
"""

import sys
from pathlib import Path


def render_insight_card(
    title,        # str  话题标题
    why,          # str  为什么分享（1-2句）
    questions,    # list 思考题，1-2个
    reference,    # dict {'title': str, 'desc': str, 'cite': str}
    source,       # str  来源
    tag,          # str  顶部标签
    output_path,  # str  输出文件路径，不含扩展名
):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Error: playwright not installed.")
        print("  pip install playwright && playwright install chromium")
        sys.exit(1)

    qs_html = "\n".join(
        f'<div class="qi">'
        f'<span class="q-dot"></span>'
        f'<span class="qt">{q}</span>'
        f'</div>'
        for q in questions
    )

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  background: #f0f0f0;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  padding: 24px;
  font-family: 'Noto Serif CJK SC', 'SimSun', serif;
}}
.wrap {{
  width: 480px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 32px rgba(0,0,0,0.10);
  overflow: hidden;
}}
/* 顶栏 */
.top-band {{
  background: #1a1a2e;
  padding: 14px 18px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}}
.tag {{
  font-family: Arial, sans-serif;
  font-size: 12px;
  font-weight: bold;
  color: #e8a020;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}}
.insight-tag {{
  font-family: Arial, sans-serif;
  font-size: 10px;
  color: #666;
}}
/* 标题区 */
.head {{
  padding: 22px 18px 18px;
  border-bottom: 1px solid #f0f0f0;
}}
.main-title {{
  font-size: 24px;
  font-weight: bold;
  color: #1a1a2e;
  line-height: 1.3;
}}
/* 为什么分享 */
.why {{
  padding: 16px 18px;
  border-bottom: 1px solid #f0f0f0;
}}
.sec-label {{
  font-family: Arial, sans-serif;
  font-size: 11px;
  font-weight: bold;
  color: #e8a020;
  letter-spacing: 0.08em;
  margin-bottom: 6px;
}}
.why-text {{
  font-size: 15px;
  color: #333;
  line-height: 1.75;
}}
/* 思考 */
.questions {{
  padding: 16px 18px;
  border-bottom: 1px solid #f0f0f0;
}}
.qi {{
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
  align-items: flex-start;
}}
.qi:last-child {{ margin-bottom: 0; }}
.q-dot {{
  width: 5px;
  height: 5px;
  background: #1a1a2e;
  border-radius: 50%;
  flex-shrink: 0;
  margin-top: 8px;
}}
.qt {{
  font-size: 14.5px;
  color: #333;
  line-height: 1.7;
  flex: 1;
}}
/* 延伸阅读 */
.ref {{
  padding: 16px 18px;
  border-bottom: 1px solid #f0f0f0;
  background: #fafaf8;
}}
.ref-title {{
  font-size: 14px;
  font-weight: bold;
  color: #1a1a2e;
  margin-bottom: 3px;
}}
.ref-desc {{
  font-size: 13px;
  color: #555;
  line-height: 1.65;
  margin-bottom: 3px;
}}
.ref-cite {{
  font-size: 10px;
  color: #999;
}}
/* 底部 */
.foot {{
  padding: 12px 18px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f7f7f7;
}}
.src {{
  font-size: 11px;
  font-weight: 600;
  color: #333;
}}
.brand {{
  font-family: Arial, sans-serif;
  font-size: 10px;
  color: #aaa;
  letter-spacing: 0.05em;
  text-align: right;
}}
</style>
</head><body>
<div class="wrap">
  <div class="top-band">
    <div class="tag">{tag}</div>
    <div class="insight-tag">INSIGHT</div>
  </div>
  <div class="head">
    <div class="main-title">{title}</div>
  </div>
  <div class="why">
    <div class="sec-label">为什么分享</div>
    <div class="why-text">{why}</div>
  </div>
  <div class="questions">
    <div class="sec-label">思考</div>
    {qs_html}
  </div>
{"  <div class=\"ref\">\n    <div class=\"sec-label\">延伸阅读</div>\n    <div class=\"ref-title\">" + reference['title'] + "</div>\n    <div class=\"ref-desc\">" + reference['desc'] + "</div>\n    <div class=\"ref-cite\">" + reference['cite'] + "</div>\n  </div>" if reference.get('title', '无') != '无' else ""}
  <div class="foot">
    <div class="src">来源 {source}</div>
    <div class="brand">ReadField</div>
  </div>
</div>
</body></html>"""

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        # 2x 分辨率保证清晰
        page = browser.new_page(
            viewport={"width": 480, "height": 820},
            device_scale_factor=2
        )
        page.set_content(html, wait_until="networkidle")
        out = output_path + ".png"
        page.screenshot(path=out, full_page=False)
        browser.close()

    print(f"Done: {out}")
    return out
