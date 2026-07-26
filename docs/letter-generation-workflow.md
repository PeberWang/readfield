# 前哨信件生成工作流

> 本文档定义 readfield 框架中信件模块的生成流程，适用于所有课程实例。
> 与 course-format.md 互补：course-format 管整体课程形式，本文档管信件这个具体模块的操作规范。

---

## 输入

生成一封信需要以下输入，按优先级从低到高排列（后者的权重高于前者）：

### 1. 角色口吻文档（voice）
定义角色的说话风格和思维特征。通用文档，一次蒸馏后不变。
位置：`samples/{course}/voice-{character}.md`

### 2. 角色定义文档（role）
定义角色在课程中的身份、职责和行事方式。通用文档。
位置：`samples/{course}/role-{character}.md`

### 3. 信件引用素材（letter-sources）
角色在信中引用的外部材料——文献、报道、思潮、其他调查队的结论等。不是一手田野纪要，是角色用来支撑自己判断的外部参考。每次课可能不同。
位置：`samples/{course}/{day-or-trial}/letter-sources.md`

### 4. 当天的原著选段（excerpts）
作为一手田野纪要的原著文本选段，由用户选取。信件内容需要基于这些选段形成对当天材料的引入和概况。
位置：`samples/{course}/{day-or-trial}/excerpt-*.md`

### 5. 课程 README（session readme）
定义当次课程的主题、视角和流程安排。
位置：`samples/{course}/{day-or-trial}/README.md`

### 6. 用户 prompt（prompt）
用户对本次信件生成的具体指令和想法。可能很短，但权重最高——这些文字最能让生成的文本区别于其他文本，最应该被重视。
位置：`samples/{course}/{day-or-trial}/prompt.md`

---

## 输出

一封信的完整结构，按排列顺序：

### 1. 信件正文
角色写给队友的信，融合 voice 和 role，基于选段和引用素材，体现 README 中的主题视角。

### 2. 附件
信中引用的外部材料的原文摘录（来自 letter-sources），直接附在信后，作为角色的注释支撑。

### 3. 书记官按
几行小笔记，引导式的半提问，永远放在最后。不是独立板块，而是对信和附件的注解收束。

---

## 参与流程

1. 用户选取原著选段，填入 letter-sources，写好 prompt
2. AI 读取上述全部输入文件，生成信件正文 + 附件 + 书记官按
3. 用户编辑定稿
4. 排版输出

---

## 文件命名

- 信件成品：`scout-letter.md`
- 附件：嵌入在信件文件内，不单独拆分
- 原著选段：`excerpt-01.md`、`excerpt-02.md`...
- 引用素材：`letter-sources.md`
- 用户指令：`prompt.md`

---

*创建于：2026-07-02*
