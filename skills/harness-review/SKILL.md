---
name: harness-review
description: Audit any project-level multi-step workflow skill (any SKILL.md describing a Task/Step/phase pipeline) against seven harness-design dimensions — intermediate-state persistence, resume-after-interrupt, partial re-do, programmatic QC, observability/audit-trail, failure-handling contract, instruction polarity. Use when the user asks to audit/review/检查/优化 a workflow skill's harness design, or to score whether it survives long runs, partial failures, and post-mortem investigation. Output a report with PASS/FAIL per dimension and concrete fix suggestions. Skip for single-step snapshot skills and non-workflow files.
metadata:
  category: workflow-harness
  role: review
---

# harness-review

针对**多步骤 skill**（含 Task 1-N / Step 0-N / 阶段 1-N 等结构）的 **harness 设计审计**。

> **Harness 工程**：把不稳定的 LLM 包装成稳定可恢复的工作流。本 skill 不评估领域质量（数字对不对、文笔好不好），只评估 **当 LLM 中断、token 用尽、部分失败、产出有问题时，这个 skill 能不能恢复、定位、修复**。

## 适用性前置判断

调用前先判断目标 skill 是否值得审：

| 应当审 | 不必审 |
|--------|--------|
| 多步骤生成型：含 Task/Step/阶段，且每步有输入输出 | 单步快照型：一次抓取、一次输出、无断点续做需求 |
| 单次执行 token 预算紧张（>20K tokens 或 >5 个 LLM 轮次） | 工具脚手架：无业务流程、无多阶段产物 |
| 产出物多、跨任务依赖（上游 sidecar → 下游模型/报告/复盘） | 纯只读检查器：只审已有产物，不生成多阶段状态 |
| 数据来源昂贵或不稳定（API 限流、人工核对、长文抽取） | 纯函数式单一职责工具 |

如果用户传入的目标不属于左侧，先告知"此 skill 不适用 harness-review，原因：…"，然后停止。

---

## 七大 harness 维度（摘要）

每个维度对应一种典型 LLM 工作流失败模式。**评分细则、PASS/FAIL 标志、反例与检测命令见 `references/seven-dimensions.md`**——评分前必须 Read 该文件。

| 维度 | 解决的失败 | PASS 一句话标准 |
|------|----------|----------------|
| A 中间状态持久化 | 上下文丢失就要从头来 | 每个 Step 落一个结构化 sidecar |
| B 断点续做 | 重启后无法识别完成进度 | 有 manifest/status 脚本扫描产物推断进度 |
| C 部分重做 | 局部失败被迫整轮重跑 | SKILL.md 有"删哪些文件触发哪步重做"表 |
| D 程序化 QC（含依赖边界）| 错误产出未被验出，或 QC 在错误时机触发 | 关键 Step 有配套 QC 脚本，单 Step 输入边界，无"禁止在 X 时机运行"警告 |
| E 可观测性 / Audit Trail | 事后无法定位为何上次产出有问题 | 每个 sidecar 有时间戳 + 来源/溯源字段 |
| F 失败处理契约 | 错误时 LLM 即兴发挥，行为不可预测 | 关键失败点有"如果 X 则 Y"显式契约 + 退出码语义 |
| G 指令正向性 | 负向指令触发 LLM 反讽回弹，被禁行为反而出现 | 行为/风格约束正向化；内容边界负向约束有 QC 配套 |

**总评规则**：A-G 七维，任一 FAIL → 总评 FAIL；全部 PASS → 总评 PASS。

---

## 执行流程

### Step 0：模式判断

**`--diff-only` 模式**（轻量，用于 SKILL.md 修改后快速检查）：

触发条件：用户传入 `--diff-only`，或对话中提到"刚修改了 SKILL.md，检查一下有没有文档-实现脱节"。

执行步骤：
1. 运行 `git diff HEAD <skill-path>/SKILL.md`，提取被修改的 Step 编号
2. 对每个被修改的 Step，grep 对应 QC 脚本是否有同期变动：`git diff HEAD <scripts-dir>/`
3. 若 SKILL.md 某 Step 有新规则但 QC 脚本无对应变动 → 输出：`❌ 文档-实现脱节：{Step N} 描述了规则 X，但 QC 脚本无对应变动`
4. 无脱节则输出：`✅ diff-only PASS：修改的 {N} 个 Step 均有对应 QC 变动或无需脚本覆盖`

`--diff-only` 模式**不**做七维全量审计，只做 D 维度增量检查。

---

### Step 1：定位目标

接收用户传入的 skill 名或路径：

```
review skill <name>              # ~/.claude/skills/<name>/SKILL.md
review skill <repo-relative>     # <skills-dir>/<name>/SKILL.md
review <path>/SKILL.md           # 直接路径
review skill <workflow-name> --diff-only   # 只检查文档-实现脱节
```

若用户**给的是一个具体 bug 或症状**（如"加粗没渲染"、"某字段为 null"、"某 QC 漏检"）而非 skill 名称，先执行**症状溯源**再进入审计：
1. 定位出问题的产物文件（JSON/Markdown/表格/图表等）
2. grep 生成该产物的脚本与 QC 脚本
3. 确定哪个 workflow skill 生成或消费了该产物
4. 以该 workflow skill 为审计目标，继续 Step 2

若用户**未指定目标**，执行 `find <skills-dir> -name SKILL.md` 列出全部候选，从中选取行数最多（最复杂）的多步骤 skill，并告知用户选择理由；如有多个旗鼓相当的候选，用 AskUserQuestion 询问。

Read 该 SKILL.md 完整内容。如果是 symlink，沿链接读到真实文件。

### Step 2：适用性判断

按"适用性前置判断"决定是否继续。不适用就直接返回原因，不写报告。

### Step 3：浏览结构

整体浏览 SKILL.md，记录：Step/Task 总数、各步产物名、引用的脚本名。这是七维评分的素材，无需机械 grep，直接读文件即可。

### Step 4：七维评分

**先 Read `references/seven-dimensions.md`**，逐个维度给 ✅ PASS / ❌ FAIL，每项写：
- **现状**（在 SKILL.md 哪里看到的，引用原文 1-2 行）
- **缺口**（与 PASS 等级差什么）
- **改进建议**（具体到要新增什么文件/小节，不写空话）

### Step 5：实测验证（仅当 skill 在本仓库且有配套脚本时）

找一个目标 workflow 已运行的真实目录，按以下顺序执行：

1. **跑 manifest/status**：若存在 manifest/status 脚本则执行，查看每步完成情况与文档描述是否一致
2. **对已有产物全量跑 QC**：找最近一个完整 run，对其主要产物（如 `report.json` / 各 sidecar）逐一执行对应 QC 脚本；若 QC 通过但已知有 bug，则说明该 QC 存在**文档-实现脱节**
3. **读 QC 脚本源码对照 SKILL.md 描述**：对于每个 SKILL.md 中承诺要检查的规则，在脚本里找对应实现；找不到 → 标注"D 维度文档-实现脱节：文档承诺 X，脚本无覆盖"
4. 不一致 → 在报告中具体标注脱节位置（SKILL.md 第 N 行描述了规则，但 QC 脚本第 M 行的实现不覆盖该场景）

### Step 6：输出结果

**单个 skill 审计（默认）**：直接在对话中输出完整报告，不写文件。

**同时审计多个 skill**：将每份报告写入 `tmp/harness-review/{skill_name}.md`，同时在对话中输出各 skill 的一行摘要对比表（skill名 | 总评 | 各维度评级 | 最高优先修复项）。
- 每次写入直接覆盖同名文件，不带时间戳
- 用户清理：`rm -rf tmp/harness-review/` 即可

### Handoff 到 harness-fix

报告输出完成后，如果存在 P0 或 P1 修复项，主动询问用户：

> "发现 {N} 项 P0/P1 修复项，是否立即执行 harness-fix？"

若用户确认，将本报告的「建议修复优先级」表直接作为 harness-fix 的输入症状列表，无需用户重新描述。

---

## 报告格式

完整模板见 `references/seven-dimensions.md` 末尾。核心骨架：

```markdown
# harness-review：{skill_name}

**审计时间**：{ISO timestamp}
**目标 SKILL.md**：{absolute_path}
**总 Step/Task 数**：{N}
**总评**：✅ PASS / ❌ FAIL（任一维度 FAIL → 总评 FAIL）

## 维度 A-G（逐个：结论 / 现状 / 缺口 / 改进建议）

## 建议修复优先级
| P | 改进项 | 预期工作量 | 价值 |

## 文档与实现一致性
{Step 5 实测发现；否则"未实测"}
```

---

## 写作纪律

- 评估范围限于 harness 工程质量（A-G 七维）；域质量问题转交该项目对应的 domain review skill 或人工判断
- 审计报告直接输出到对话；仅当用户明确说「按建议修复」时才修改 skill 文件
- 每个 finding 都引用 SKILL.md 具体行号或原文摘录
- 改进建议写到文件级：如「新增 qc_xxx.py 校验 Y 字段」

---

## 与其他 skill 的关系

| skill | 关系 |
|-------|------|
| `harness-fix` | 输出端：本 skill 发现的 P0/P1 修复项可直接作为 `harness-fix` 的输入；两者组成"发现→修复"闭环 |
| 通用 skill review | 审 SKILL.md 写作质量（描述、触发词、结构）；本 skill 专注 harness 设计 |
| domain review skill | 审领域内容质量；本 skill 只审工程稳定性和可恢复性 |
| 项目本地 adapter | 提供该项目的具体路径/产物/QC 规则与历史失败案例；本通用 skill 提供方法论框架 |
