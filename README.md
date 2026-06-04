# harness-skills

[![Claude Code](https://img.shields.io/badge/Claude_Code-plugin-d97757)](https://github.com/qiyuey/harness-skills)
[![Codex](https://img.shields.io/badge/Codex-plugin-412991)](https://github.com/qiyuey/harness-skills)
[![evals](https://img.shields.io/badge/evals-L1_PASS_·_L2_6%2F6_·_L3_18%2F18-2ea44f)](evals/README.md)
[![License](https://img.shields.io/badge/license-Anti--996-blue)](https://github.com/996icu/996.ICU)

面向 AI agent（Claude Code / Codex）的通用 **LLM 工作流 harness 方法论**。

```bash
# Claude Code —— 以插件形式安装全部三个 skill
/plugin marketplace add qiyuey/harness-skills
/plugin install harness-skills@harness-skills
```

**harness** 指包在 LLM 外面、负责承接状态与编排执行的那层工程脚手架。LLM 本身是非确定的、上下文易失的；harness 工程就是把它包裹成一个**状态可持久化、流程可恢复**的多步骤工作流。

这其实就是业界讲的 **durable execution（持久化 / 抗崩溃执行）**——「把失败变得无关紧要：进程崩了能从上次完成的步骤接着跑，而不是从头重来」。对 LLM 流水线，这一点尤其值钱：从头重来意味着**已经花掉的 token 和时间全部白费**，重跑一遍。2025 年这套模型随着 AI agent 基础设施的需求走向主流，Temporal、LangGraph、Azure Durable Task、Inngest 等都在用**框架与运行时**提供它。

本仓库的差异在于：它把同一套原则压缩成**纯文本方法论**，落在单个 skill 的 `SKILL.md` 里——不引入运行时、不绑定框架，靠把「状态落盘 / 断点续做 / 局部重跑 / 可审计」写进流程指令本身来达成。当你的工作流就是一个 Claude Code / Codex skill、不想（也不该）为它架一套执行引擎时，这是最轻的那一层。

这些 skill 不评判领域质量（数字是否正确、文笔是否好），只评判工作流的**工程稳定性**：它能否在中断后从已落盘的产物继续、能否只重跑出错的那一步、能否在事后被追溯排查。换句话说，它们守护的是「流程能不能活下来」，而不是「内容写得好不好」。

## 适用场景

这套方法论针对的是**单个 skill 或 cron 任务内部的长时间、多步骤执行**——一条由单个 agent 顺序跑完的流水线。它的脆弱点在于**时间跨度**与**步骤数量**：步骤越多、跑得越久，中途被打断、某一步出错、上下文丢失（context loss）、错误沿链路累积（compounding errors）的概率就越高。harness 工程就是把这条流水线包成「断了能续、错了能局部重跑、事后能追溯」的形态。

典型适用：

- **多步骤 skill**：一个 skill 内部分成多个 Task/Step 顺序执行（如「研究 → 抽取 → 验证 → 综合」），任意一步失败不应推倒重来。
- **cron / 定时任务**：周期性、无人值守地长时间运行，必须能从上次落盘的状态恢复，并在事后留下可审计的轨迹。
- **任何长链路单 agent 流水线**：步骤多、耗时长、依赖中间产物落盘的顺序执行流程。

**不适用**（不在本方法论范围内）：

- **多 Agent 编排（multi-agent orchestration）**：多个 agent 并行 / 协作 / 投票的场景（fan-out、pipeline、judge panel 等）。业界普遍把「单 agent 循环」（single-agent loop）和「多 agent 流水线」（multi-agent pipeline）当作生命周期上两个不同层面：后者管「agent 之间怎么协作通信」，由 Workflow 一类的编排工具解决，本仓库不涉及。本方法论只关注前者：**单个 agent 把一条长流水线稳定跑完**。

> 一句话：横向并行多个 agent 不是这里的目标；纵向把一条长流水线跑稳才是。

## 三个 skill

| skill | 适用场景 |
|-------|---------|
| **harness-review** | 按 harness 维度审计一个多步骤工作流 skill —— 六个方法论基本面（契约、状态落盘、程序化质检、局部恢复、可审计、可回归）分解为九条可独立打分的审计维度（状态持久化、断点续做、部分重做、QC 存在性、QC 依赖边界、指令极性、可观测性、失败契约、可回归评测）。输出 PASS/FAIL + 修复建议。 |
| **harness-fix** | 已经定位到某个具体 bug/异常。跑 3 层闭环：根因分析 → 加 guard（QC）→ 源头修复，确保不再复发。 |
| **harness-build** | 新增一个契约字段 / sidecar / QC 规则 / 流水线步骤。跑 4 层闭环：设计 → 实现 → QC → 文档。 |

## 闭环自进化

三个 skill 不是孤立工具，而是一个**越用越稳的飞轮**：审计发现缺口 → 修复并把经验沉淀成 QC/案例 → 扩展新能力 → 再审计。每转一圈，工作流多一层防护，同类问题下次被自动拦截，而不是反复踩坑。

```
            ┌─────────────────────────────────────────┐
            │                                         ▼
   ┌──────────────┐   P0/P1 修复项    ┌──────────────┐
   │ harness-review │ ───────────────▶ │  harness-fix  │
   │   发现缺口     │                   │  根因 → 修复   │
   └──────────────┘                   └──────────────┘
            ▲                                 │
            │ 新增 step/字段满足审计维度?       │ 沉淀复用（Step 4）
            │                                 ▼
   ┌──────────────┐                  ┌──────────────────────┐
   │ harness-build │ ◀──── 新需求 ──── │ QC 规则 / 回归测试 /    │
   │  设计 → 落地   │                  │ adapter 失败案例库      │
   └──────────────┘                  └──────────────────────┘
       └──────────────── 沉淀回流 ────────────────┘
```

两条让飞轮自进化的回流：

- **发现 → 修复**：`harness-review` 输出的 P0/P1 修复项可直接作为 `harness-fix` 的输入症状列表，无需重新描述。
- **修复 → 沉淀**：`harness-fix` 的最后一步把每次修复回流成**新的 QC 检查项、回归 fixture、或项目 adapter 的失败案例**——下次同类缺陷在产物到达用户前就被脚本拦下。`harness-build` 新增能力后再交给 `harness-review` 复检，闭合循环。

> 沉淀的落点（QC 脚本、回归测试、adapter 案例库）属于**消费方项目或其适配器**；本仓库只提供这套方法论与回流机制本身。

### 怎么挑

三个 skill 各自的 `description` 已编码互斥的触发条件，模型会自动路由；本仓库刻意不设单独的入口/分发 skill。如需手动选择：

```
审计一个多步骤 skill 的 harness 设计      → harness-review
修复一个已知的 workflow bug，且要防复现   → harness-fix
新增字段 / sidecar / QC 规则 / step       → harness-build

不确定是 fix 还是 build？
  • 症状是"已经坏了"     → harness-fix
  • 需求是"还没有这个能力" → harness-build
```

## 安装

### 完整插件（全部三个 skill）

本仓库本身就是它自己的插件市场（marketplace），skill 从 `skills/` 自动发现。

**Claude Code**（读取 `.claude-plugin/plugin.json`）：

```bash
/plugin marketplace add qiyuey/harness-skills
/plugin install harness-skills@harness-skills
```

**Codex CLI**（读取 `.codex-plugin/plugin.json`）：

```bash
codex plugin marketplace add https://github.com/qiyuey/harness-skills
codex plugin install harness-skills
```

### 单个 skill

把某个 skill 目录拷进你项目的 `.claude/skills/`：

```bash
cp -r harness-skills/skills/harness-review /path/to/project/.claude/skills/
```

每个 skill 仅靠纯文本方法论即可工作 —— 不需要运行时脚本，没有共享脚本包。

### 配合项目适配器（adapter）使用

本仓库保持**通用**。项目专属的规则（路径、产物名、QC 脚本名、真实失败案例）应放在消费方项目中的一个**本地适配器 skill** 里，例如：

```
<project>/.claude/skills/<project>-harness-adapter/SKILL.md
```

运行时，`harness-fix` / `harness-build` 会先读取适配器以获取项目路径和项目真实的失败案例库，然后再套用本仓库的通用方法论。起步模板见 [`docs/adapter-template.md`](docs/adapter-template.md)。

## 非目标（Non-goals）

- 不是领域框架（不针对任何垂直行业）。
- **不**针对多 Agent 编排 —— 只管单个 agent 把一条长流水线稳定跑完，agent 间的并行 / 协作 / 通信交给编排层（见[适用场景](#适用场景)）。
- **不**提供运行时或框架 —— 是纯文本方法论，不引入依赖、不绑定 Temporal / LangGraph 一类的执行引擎。
- **不**提供通用 QC 脚本 —— 具体的 QC 属于消费方项目或其适配器。
- **不**替代项目的本地适配器。

## 质量 / evals

skill 自带一套 3 层 eval 套件，位于 `evals/`（详见 [`evals/README.md`](evals/README.md)）。因为这些是**方法论** skill、没有运行时代码，测试金字塔做了相应调整：

| 层级 | 测什么 | 用 LLM? | 运行 |
|-----|---------|--------|------|
| **L1 Lint** | SKILL.md 自合规：frontmatter 规则、零领域残留、交叉引用完整、**指令极性自审（吃自己的狗粮）** | 否 | `python3 evals/scripts/run_evals.py --layer l1` |
| **L2 Behavioral** | 把一份植入了缺陷的工作流 SKILL.md 喂给 `harness-review`，断言它能抓出来 | 是（`claude` CLI） | `--layer l2` |
| **L3 Trigger** | 三个 skill 的路由准确率 + 互斥性 | 是（`claude` CLI） | `--layer l3` |

最近一次运行：**L1 PASS · L2 6/6 · L3 18/18（100% 准确率，0 跨 skill 错误）。**

```bash
python3 evals/scripts/run_evals.py            # 跑全部三层
python3 evals/scripts/run_evals.py --layer l1 # 零 LLM，CI 默认（失败即阻断）
```

## 脚本策略

skill 本身只附带 **`SKILL.md` + Markdown 引用**，没有运行时脚本、没有共享脚本包 —— 单个 skill 安装后必须仅靠文本方法论就能工作。

`evals/` 目录是仓库维护工具，**不是 skill 的运行时依赖**：安装任意单个 skill 都不会把 `evals/` 拉进来。

## License

[Anti 996 License v1.0](LICENSE)（基于 [996.ICU](https://github.com/996icu/996.ICU)）—— 使用本项目即承诺遵守所在司法辖区的劳动法,不得违反 996 工作制。
