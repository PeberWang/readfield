# blindlab — 心眼子活动课数据管道

「给 AI 安心眼子」盲评工作坊的现场设施，装置名 **blindlab**（盲评实验台）。一条命令完成一个环节，目标是在 1 小时的活动课现场零手工操作跑完：AI 回应生成 → 盲评展示 → 问卷收集 → 统计排名 → 对比讨论。

活动课的教学设计见 `设计.md`，装置使用入口见 `SKILL.md`。以下命令均在本目录（`sub-skills/blindlab`）下执行。

## 现场速查（跑会前只看这一段）

```bash
# 0. 会前：把共读人交来的成品放进 data/skills/（zip 直接 skill import），城堡场景放进 data/scenarios/text-based/
#    如果之前跑过示例/测试，先清场（--purge-feishu 会连旧评分表一起删）：
python blindlab.py reset --round day1 --purge-feishu
# 1. 生成全部 AI 回应（可断点续跑；工作流型 skill 会自动跳过）
python blindlab.py generate --round day1
# 1b. 若有工作流型 skill：生成子进程任务清单 → 小劳 spawn 子进程执行 → 回收产出
python blindlab.py delegate plan --round day1
#    （小劳按 data/results/agent_plan_day1.json 每个 skill 起一个子进程，跑完后：）
python blindlab.py delegate collect --round day1
# 2. 生成盲评展示页（投屏用，方向键翻页）
python blindlab.py present responses --round day1 --open
# 3. 一键建评分多维表格，拿到链接 → 网页打开 → 建「问卷」视图 → 出二维码
python blindlab.py ballot create --round day1
# 4. 评分结束后拉取统计
python blindlab.py tally --round day1
# 5. 排名可视化展示页
python blindlab.py present ranking --round day1 --open
# 6. 任意两份回应左右分栏对比（讨论用，可多次生成）
python blindlab.py present compare --round day1 --left 01 --right 03 --open
# 7. 讨论收尾时揭晓盲码与作者
python blindlab.py reveal --round day1
```

Day 2 把 `--round day1` 换成 `--round day2`（场景放 data/scenarios/real-based/，skill 沿用同一批，盲码不变——同一批 skill 走两轮，这是准实验对照的核心）。
两天都评分后，用 `present ranking --round all` 生成跨语境对照展示页。

## 命令一览

| 命令 | 作用 | 输出 |
|------|------|------|
| `scenarios --round R` | 列出场景 | 终端 |
| `skills` | 列出心法 | 终端 |
| `generate --round R [--model M] [--workers N]` | skill × 场景生成 AI 回应（仅简单心法） | `data/results/responses_R.json` |
| `delegate plan --round R` | 生成工作流型 skill 的子进程任务清单 | `data/results/agent_plan_R.json` |
| `delegate collect --round R` | 校验子进程产出的契约 JSON，并入回应数据 | `data/results/responses_R.json` + `agentic_R.json` |
| `skill import <file> [--key K] [--force]` | 导入成品：`zip`（AI 云电脑打包，首选）或含 `===FILE:===` 块的 `txt`（兜底），落成 `data/skills/K/`（zip 缺省取 zip 内文件夹名） | 终端 |
| `present responses --round R` | 盲评展示页（黑字旁白/红字回应） | `output/responses_R.html` |
| `ballot create --round R` | 建评分多维表格（幂等，可断点续建） | 打印链接 + `data/results/survey_R.json` |
| `tally --round R` | 拉取评分并统计三维度 | `data/results/scores_R.json` |
| `present ranking --round R\|all` | 排名可视化（all = 两天对照） | `output/ranking_R.html` |
| `present compare --round R --left X --right Y` | 两份回应分栏对比 | `output/compare_R_X_vs_Y.html` |
| `reveal --round R` | 揭晓盲码 → skill/作者 | 终端 |
| `reset --round R [--purge-feishu]` | 清场：删除本轮运行状态，可选删飞书表 | 终端 |
| `demo` | mock 数据产出全部展示页（离线验证） | `output/demo/` |

`--open`：生成后直接用默认浏览器打开。

## 数据格式

**场景**（`data/scenarios/<轮次目录>/*.md`）：front matter（id/title/summary）+ 正文，正文中恰好一个 `[[response]]` 占位符，AI 回应就填在这里。

**心法**（`data/skills/*.md`）：front matter（name/author）+ 正文。正文就是发给 AI 的「人格与策略说明」。共读人提交什么格式都不重要，只要是一个 md 文件。

**工作流型 skill**（`data/skills/<名字>/` 文件夹，内含 `SKILL.md` + 任意配套资源）：给想认真做工程的同学。`SKILL.md` 定义多步工作流（场景判别、中间分析文档、playbook 调取等），可以带 templates/、playbooks/ 等资源文件。这类 skill 不走裸 API，由 OpenClaw 子进程作为执行体跑完整个工作流，最终产出契约 JSON。示例见 `examples/skills/example-04-案头老吏/`（同目录另有 01–03 三份简单心法示例）。

**共读人提交格式**：小组在 Kimi 等聊天工具里用启动包（`starter-pack/`，zip 分发）与 AI 协作设计 skill。成品交付双通道：首选 AI 云电脑打包的 zip（`skill import xxx.zip`），兜底 `===FILE: 相对路径===` 分块格式的单条消息（存为 txt 后 `skill import xxx.txt --key <文件夹名>`）。

**契约 JSON**（子进程写到 `data/results/agentic/<轮次>/<场景id>/<盲码>.json`）：`response`（必填，唯一进入盲评的文本）、`analysis`（必填，工作流判断简述，揭晓环节的教学素材）、`scene_type`、`notes`（可选）。中间文档写到 `data/results/agentic_work/<轮次>/<盲码>/<场景id>/`，collect 时登记备查。子进程编排由小劳完成：delegate plan 出清单 → 每个 skill spawn 一个子进程 → delegate collect 回收。删输出 JSON 后重跑 plan 可让任务重新入单。

**盲码**：每轮一次随机分配，存 `data/results/blind_R.json`。新增 skill 会分配到新尾号，不打乱既有编号。`reveal` 前不要打开这个文件。

**评分表结构**：每位评分人一行。`昵称` + `提交时间` + 每个盲码 ×（`01·自然` `01·技巧` `01·远见` …，单选，选项为「分数（方向）」如 `5（非常好）`，标签在 course.yaml 的 score.labels 配）。

## 架构（胶水编程，四层）

```
blindlab.py       CLI 入口（参数解析）
  └─ glue/        编排层：命令实现，串联 services，零业务逻辑
      └─ services/  业务层：scenario/skill/generate/delegate/ballot/tally/present 七个功能单元
          └─ libs/  适配层：feishu_bitable（飞书API）、llm（LLM调用）、store（本地JSON）
              └─ config/  配置层：路径、凭证、业务常量
```

依赖：`requests` + `pyyaml`。凭证在本目录的 `.env`（飞书应用 + LLM key），不入库；模板见 `.env.example`。

**开新课**：课程实例（轮次/评分维度/分值/提示词）都在 `course.yaml`，复用者改这个文件 + 换场景与心法即可，不动代码。文件删除则回退内置默认值（就是本课程）。

## 现场故障预案

- **飞书频率限制（99991400）**：管道内置退避重试，等几十秒会自动穿过。不要连续狂点重跑，越点越慢。token 已做磁盘缓存。
- **代理干扰**：管道对所有外部调用强制直连（trust_env=False），Clash 等系统代理不影响。
- **generate 中断**：直接重跑同一命令，已生成的回应自动跳过。
- **某条回应生成失败**：重跑 `generate`，只补失败的那几条。
- **子进程产出不合契约**：delegate collect 会逐条列出问题（缺字段/JSON 损坏/盲码不明），修正后重跑 collect 即可，不影响已并入的。
- **评分表字段被手动改过**：统计按「盲码+维度名」模糊匹配（`01·自然`/`01-自然`/`回应01·自然` 都认），但别把两个字段改成重名。

## 实验控制说明

两条执行路径共用一套盲码。简单心法走裸 API：同一轮内同一模型（默认 deepseek-v4-flash）、同一温度（0.7）、同一提示词模板，唯一变量是心法内容。工作流型 skill 走 OpenClaw 子进程：同样锁 deepseek-v4-flash，但过程是多步工作流，变量是整个 skill 设计——工程化的组织理解本身就是被比较的「心眼子」。换模型用 `--model`，但一轮之内别换。
