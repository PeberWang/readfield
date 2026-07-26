"""
心眼子活动海报 — ReadField 视觉语言（与 Insight Card 同族）

输出单张 PNG（2x 高清），适合直接发微信社群。
用法：python xny_poster.py <输出路径，不含扩展名>
"""

import sys

from playwright.sync_api import sync_playwright

HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body {
  background: #e9e9ec;
  display: flex; justify-content: center; align-items: flex-start;
  min-height: 100vh; padding: 24px;
  font-family: 'Noto Serif CJK SC', 'SimSun', serif;
}
.wrap {
  width: 480px; background: #fff; border-radius: 8px;
  box-shadow: 0 4px 32px rgba(0,0,0,0.12); overflow: hidden;
}
/* 顶栏 */
.top-band {
  background: #1a1a2e; padding: 13px 20px;
  display: flex; justify-content: space-between; align-items: center;
}
.tag {
  font-family: Arial, sans-serif; font-size: 11px; font-weight: bold;
  color: #e8a020; letter-spacing: 0.12em;
}
.top-right { font-family: Arial, sans-serif; font-size: 10px; color: #667; letter-spacing: 0.08em; }
/* 主视觉 */
.hero {
  background: #1a1a2e; padding: 30px 24px 28px; color: #fff;
}
.hero-kicker {
  font-size: 13px; color: #e8a020; letter-spacing: 0.2em;
  margin-bottom: 12px; font-weight: bold;
}
.hero-title {
  font-size: 40px; font-weight: 900; line-height: 1.15; letter-spacing: 0.02em;
}
.hero-sub {
  margin-top: 12px; font-size: 15px; color: #c8c8d4; letter-spacing: 0.1em;
}
.hero-hook {
  margin-top: 18px; padding-top: 16px; border-top: 1px solid rgba(255,255,255,0.16);
  font-size: 14.5px; color: #e8a020; line-height: 1.7;
}
/* 区块 */
.sec { padding: 18px 24px; border-bottom: 1px solid #f0f0f0; }
.sec-label {
  font-family: Arial, sans-serif; font-size: 11px; font-weight: bold;
  color: #e8a020; letter-spacing: 0.1em; margin-bottom: 9px;
}
.sec-text { font-size: 14px; color: #333; line-height: 1.8; }
.sec-text b { color: #1a1a2e; }
/* 两轮 */
.rounds { display: flex; gap: 12px; }
.round {
  flex: 1; background: #f7f7f5; border-radius: 6px; padding: 12px 14px;
}
.round-day {
  font-family: Arial, sans-serif; font-size: 10px; font-weight: bold;
  color: #e8a020; letter-spacing: 0.1em; margin-bottom: 4px;
}
.round-name { font-size: 15px; font-weight: bold; color: #1a1a2e; margin-bottom: 5px; }
.round-desc { font-size: 12px; color: #555; line-height: 1.65; }
.rounds-note { margin-top: 10px; font-size: 12.5px; color: #777; line-height: 1.6; }
/* 行动 */
.steps { display: flex; flex-direction: column; gap: 8px; }
.step { display: flex; gap: 10px; align-items: flex-start; }
.step-n {
  flex-shrink: 0; width: 20px; height: 20px; border-radius: 50%;
  background: #1a1a2e; color: #e8a020;
  font-family: Arial, sans-serif; font-size: 11px; font-weight: bold;
  display: flex; justify-content: center; align-items: center; margin-top: 2px;
}
.step-t { font-size: 14px; color: #333; line-height: 1.6; flex: 1; }
/* 时间条 */
.time-band { background: #1a1a2e; padding: 16px 24px; }
.time-row {
  display: flex; justify-content: space-between; align-items: baseline;
  padding: 5px 0;
}
.time-label { font-size: 13px; color: #c8c8d4; }
.time-value { font-size: 15px; font-weight: bold; color: #fff; }
.time-value.deadline { color: #e8a020; }
/* 底部 */
.foot {
  padding: 11px 24px; display: flex; justify-content: space-between; align-items: center;
  background: #f7f7f7;
}
.foot-l { font-size: 11px; font-weight: 600; color: #333; }
.foot-r { font-family: Arial, sans-serif; font-size: 10px; color: #aaa; letter-spacing: 0.05em; }
</style></head><body>
<div class="wrap">
  <div class="top-band">
    <div class="tag">知合 NEXUS 2026</div>
    <div class="top-right">活动预告</div>
  </div>
  <div class="hero">
    <div class="hero-title">给 AI<br>安心眼子</div>
    <div class="hero-sub">组织理解力，可以被设计出来吗？</div>
    <div class="hero-hook">你不为难 AI，你武装 AI。<br>上场的不是你，是你的 skill。</div>
  </div>
  <div class="sec">
    <div class="sec-label">玩法</div>
    <div class="sec-text">小组设计一个 <b>skill</b>，指导 AI 替我们在各种组织场景中做判断。AI 有自己的智能，会泛化、会发挥，<b>关键在于你给它什么样的引导。</b></div>
  </div>
  <div class="sec">
    <div class="sec-label">情境题库</div>
    <div class="rounds">
      <div class="round">
        <div class="round-day">小说</div>
        <div class="round-name">城堡深处</div>
      </div>
      <div class="round">
        <div class="round-day">现实</div>
        <div class="round-name">治理现场</div>
      </div>
    </div>
    <div class="rounds-note">现场从题库抽三道，小说与现实同台。你的 skill 要通吃所有抽到的题。</div>
  </div>
  <div class="sec">
    <div class="sec-label">盲评定胜负</div>
    <div class="sec-text">全班打分，没人知道哪个回应是哪个小组的。<br><b>自然度 · 策略性 · 场景契合度</b>，各 1 到 5 分。</div>
  </div>
  <div class="sec">
    <div class="sec-label">现场一小时</div>
    <div class="steps">
      <div class="step"><div class="step-n">1</div><div class="step-t">现场分组，领取「心眼子启动包」</div></div>
      <div class="step"><div class="step-n">2</div><div class="step-t">与 Kimi 协作，把小组的组织理解造成 skill</div></div>
      <div class="step"><div class="step-n">3</div><div class="step-t">AI 替你们上场，逐个情境做出反应，给出行为</div></div>
      <div class="step"><div class="step-n">4</div><div class="step-t">全班盲评打分，排名揭晓，对照讨论</div></div>
    </div>
    <div class="rounds-note">无需任何准备，人到就行。</div>
  </div>
  <div class="time-band">
    <div class="time-row">
      <div class="time-label">时间</div>
      <div class="time-value deadline">7月19日（周日）16:00 – 17:00</div>
    </div>
    <div class="time-row">
      <div class="time-label">地点</div>
      <div class="time-value">铁城共创社</div>
    </div>
  </div>
</div>
</body></html>"""


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "xny_poster"
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 530, "height": 900},
                                device_scale_factor=2)
        page.set_content(HTML, wait_until="networkidle")
        page.screenshot(path=out + ".png", full_page=True)
        browser.close()
    print(f"Done: {out}.png")


if __name__ == "__main__":
    main()
