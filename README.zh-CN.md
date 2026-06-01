# harness-skills

[English](README.md) · **简体中文**

[![Claude Code](https://img.shields.io/badge/Claude_Code-plugin-d97757)](https://github.com/qiyuey/harness-skills)
[![Codex](https://img.shields.io/badge/Codex-plugin-412991)](https://github.com/qiyuey/harness-skills)
[![evals](https://img.shields.io/badge/evals-L1_PASS_·_L2_6%2F6_·_L3_18%2F18-2ea44f)](evals/README.md)
[![license](https://img.shields.io/github/license/qiyuey/harness-skills)](LICENSE)

面向 AI agent（Claude Code / Codex）的通用 **LLM 工作流 harness 方法论**。

```bash
# Claude Code —— 以插件形式安装全部三个 skill
/plugin marketplace add qiyuey/harness-skills
/plugin install harness-skills@harness-skills
```

"Harness 工程" = 把一个不可靠的 LLM 包裹成一个**稳定、可恢复**的多步骤工作流。这些 skill 不评判领域质量（数字是否正确、文笔是否好），它们评判的是一个工作流能否**在中断、token 耗尽、局部失败以及事后复盘排查中存活下来**。

## 内容一览

| skill | 适用场景 |
|-------|---------|
| **harness-review** | 按 7 个 harness 维度审计一个多步骤工作流 skill（状态持久化、断点续跑、局部重做、程序化 QC、可观测性、失败契约、指令极性）。输出 PASS/FAIL + 修复建议。 |
| **harness-fix** | 已经定位到某个具体 bug/异常。跑 3 层闭环：根因分析 → 加 guard（QC）→ 源头修复，确保不再复发。 |
| **harness-build** | 新增一个契约字段 / sidecar / QC 规则 / 流水线步骤。跑 4 层闭环：设计 → 实现 → QC → 文档。 |

### 路由（刻意不设入口 skill）

按照 Anthropic 的 skills 指南，**是 `name` + `description` 这段 frontmatter 决定模型何时触发某个 skill** —— 路由信息应该写在那里，而不是单独搞一个分发器。这三个 `description` 本身已经编码了互斥的触发条件与彼此衔接关系，因此**没有 `using-harness` 路由 skill**。

> 注：Superpowers 的 `using-superpowers` 并*不是*路由器 —— 它是一个 SessionStart **引导（bootstrap）**，往上下文里注入"你拥有 skills，请使用 Skill 工具"，这是因为它有几十个 skill 才值得。本仓库只有三个自描述的 skill，这种引导在这里没有收益。如果本仓库增长到 ~6 个 skill 以上，再重新评估 —— 那时一个 `harness-skills-sync` skill（参考 baoyu/qiyuey 的 `hermes-skills-sync` 以及 Superpowers 的 `pulling-updates-from-skills-repository`）比一个入口路由器更有价值。

直接挑选：

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

本仓库本身就是它自己的插件市场（marketplace）。Skill 会从 `skills/` 自动发现。

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

每个 skill 仅靠纯文本方法论即可工作 —— 不需要运行时 Python，没有共享脚本包。

### 配合项目适配器（adapter）使用

本仓库保持**通用**。项目专属的规则（路径、产物名、QC 脚本名、真实失败案例）应放在消费方项目中的一个**本地适配器 skill** 里，例如：

```
<project>/.claude/skills/<project>-harness-adapter/SKILL.md
```

运行时，`harness-fix` / `harness-build` 会先读取适配器以获取项目路径和项目真实的失败案例库，然后再套用本仓库的通用方法论。起步模板见 `docs/adapter-template.md`。

## 非目标（Non-goals）

- 不是领域框架（不是股票研究，也不针对任何垂直行业）。
- **不**提供通用 QC 脚本 —— 具体的 QC 属于消费方项目或其适配器。
- **不**替代项目的本地适配器。

## 质量 / evals

这些 skill 自带一套 3 层 eval 套件，位于 `evals/`（详见 `evals/README.md`）。因为这些是**方法论** skill、没有运行时代码，所以测试金字塔做了调整：

| 层级 | 测试内容 | 用 LLM? | 运行 |
|-----|---------|--------|------|
| **L1 Lint** | SKILL.md 自合规：frontmatter 规则、零领域残留、交叉引用完整、**指令极性自审（吃自己的狗粮）** | 否 | `python3 evals/scripts/run_evals.py --layer l1` |
| **L2 Behavioral** | 把一份植入了缺陷的工作流 SKILL.md 喂给 `harness-review`，断言它能抓出来 | 是（`claude` CLI） | `--layer l2` |
| **L3 Trigger** | 三个 skill 的路由准确率 + 互斥性 | 是（`claude` CLI） | `--layer l3` |

最近一次运行：**L1 PASS · L2 6/6 · L3 18/18（100% 准确率，0 跨 skill 错误）。**

```bash
python3 evals/scripts/run_evals.py            # 跑全部三层
python3 evals/scripts/run_evals.py --layer l1 # 零 LLM，CI 默认（失败即阻断）
```

## 脚本 / 自动化策略

Skill 本身只附带 **`SKILL.md` + Markdown 引用** —— 没有运行时 `.py`、没有 npm workspace、没有共享脚本包。单个 skill 在安装后必须仅靠文本方法论就能工作。

`evals/` 目录**确实**是 Python，但它是**仓库维护工具，不是 skill 的运行时依赖** —— 安装任意单个 skill 都不会把 `evals/` 拉进来。这符合该策略对 `tools/`/`scripts/` 下维护工具的豁免。

## 上游同步（面向 fork / 消费方项目）

如果某个消费方项目在本地定制了某个 skill，应当把本仓库作为上游 base 进行跟踪，并记录同步日志，参照 `sync-upstream-skill` 模式：

| 日期 | 上游 commit（新 base） | 操作 | 备注 |
|------|----------------------|------|------|
| 2026-06-01 | （初始） | 建立 fork base | |
