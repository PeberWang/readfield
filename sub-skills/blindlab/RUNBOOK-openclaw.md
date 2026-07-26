# 小劳执行规程 · blindlab 子进程编排

管道本身不 spawn 子进程。小劳（OpenClaw 主 session）按本规程编排。

## 流程（本课只设单轮 day1；多轮课程把 R 换成 day2 等再跑一遍）

```bash
cd sub-skills/blindlab
python blindlab.py generate --round R        # 建盲码+元信息；简单心法走 API，工作流型自动跳过
python blindlab.py delegate plan --round R   # 产出 data/results/agent_plan_R.json
```

1. 读 `data/results/agent_plan_R.json`，把 `tasks` 按 `code` 分组，**每个 skill 一个子进程**（同 skill 的多个场景顺序处理）。
2. 给每个子进程的简报（逐字段取自 task，不要改写路径）：

   > 你在执行一个工作流型 skill。先读 `{skill_dir}\SKILL.md`，严格按其中定义的工作流执行。
   > 对任务清单中的每个场景：读 `{scenario_path}`，完整走一遍工作流；
   > 中间文档写到 `{work_dir}\`（先建目录）；
   > 最终把契约 JSON 写到 `{output}`，UTF-8 编码，字段：`response`（必填，主人公回应）、
   > `analysis`（必填，200 字内判断过程）、`scene_type`、`notes`（可选）。
   > **JSON 纪律**：字符串值内部不要出现英文双引号——说话引语一律用中文引号「」，写完自己 json.loads 校验一遍再交。
   > 约束：无网络、无外部工具；每个场景独立，不带跨场景记忆；模型锁 deepseek-v4-flash，不要换。

3. 全部子进程完成后回收：

```bash
python blindlab.py delegate collect --round R
```

   `[OK]` = 已并入；`!!` = 逐条问题（JSON 损坏/缺字段/盲码不明），修好对应文件后**重跑 collect 即可**，已并入的不受影响。
   某个子进程要重跑：删它的输出 JSON，重跑 `delegate plan` 会重新入单。

4. 投屏：`python blindlab.py present responses --round R --open`

## 现场禁忌

- 一轮之内不换模型；不改 plan JSON 里的任何路径。
- 子进程只读自己 skill 文件夹内的资源，看不到其他组。
- reveal 之前不要打开 `data/results/blind_R.json`。
