# 案例：重返城堡（2026 夏 · 知合 NEXUS 中山夏令营）

ReadField 框架的首次实战。7 天正课 + 2 天活动课，共读人以田野调查为认知工具阅读卡夫卡《城堡》：主人公 K 被重塑为田野调查队派出的前哨，共读人作为后方调查主力，阅读、研究和评议前哨回传的材料。

本目录是这门课从设计到交付的完整档案，与 `SKILL.md` 六步工作流对应：

| 工作流步骤 | 本案例中的对应物 |
|-----------|----------------|
| Step 1 课程骨架 | `syllabus.md`（原始课纲）、`课纲_重返城堡.tex/.pdf`（排版版） |
| Step 2 选定材料 | 各 day 目录的 `excerpt-XX.md`、`catalyst-XX.md` |
| Step 3 生成引导语与导引 | `voice-k.md` + `role-k.md`（前置文档）、各 day 的 `scout-letter.md`（K 的信）、`day-01/prompt.md`（第一封信的生成指令实例） |
| Step 4 定稿 | 各 day 的 README 与文本终稿 |
| Step 5 渲染教案 | 各 day 的 `_lesson.tex`（可用 xelatex 自行编译） |
| Step 6 全课程合版 | `merged/`（含《重返城堡》完整版教案.pdf 与合版 tex） |

## 目录地图

- `day-01/` … `day-07/`：每日教案。`README.md` 是当天设计（主题、材料链、节奏）；`scout-letter.md` 是导引（K 以前哨口吻写的信）；`excerpt-XX.md` 原文选段；`catalyst-XX.md` 对话触媒。day-05 另有 `素材_*.md` 三份街头官僚专题材料，day-01 另有 `PRACTICE-RUN.md` 预演方案。
- `merged/`：全课程合版。《重返城堡》完整版教案.pdf 是成品；`cover.tex`、`merged_lessons.tex` 可复现。
- `voice-k.md` / `role-k.md`：K 的口吻文档与角色文档（子 skill `sub-skills/voice-distillation/` 的实例）。
- `plot-structure.md`：《城堡》情节结构梳理，选材阶段的作业文档。
- `STYLE-GUIDE.md` / `排版注意事项.md`：排版规范的迭代记录。
- `daily-conclusion.txt`：每天课后发给共读人的总结信。
- `daily-share/`：课前预热分享卡片（Insight Card）三天实例，含 PNG 成品（子 skill `sub-skills/insight-card/` 的实例）。
- `starter-pack/`：活动课启动包的交付成品——`starter-pack.zip`（结构归档）与`心眼子启动包.txt`（单文件版，聊天上传用）。这是当时实际分发给共读人的形态；可编辑源文件维护在 `sub-skills/blindlab/starter-pack/`。
- `scenarios/`：活动课实考题目。`text-based/` 为城堡情境，`real-based/` 为现实情境。
- `skills/`：活动课共读人作品原件。各小组在营中用 AI 协作设计的 Skill（zip 为提交原格式），组名均为化名。

## 使用说明

- **渲染单课**：`python scripts/render_lesson.py samples/castle/day-01`（依赖 xelatex，中文需宋体/楷体字体）。
- **原文选段为教学合理引用**，均标注出处；作品全本不在本仓库内。
- 活动课的现场装置与教学设计见 `sub-skills/blindlab/`。
