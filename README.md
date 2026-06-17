# harness-skills

[![Claude Code](https://img.shields.io/badge/Claude_Code-plugin-d97757)](https://github.com/qiyuey/harness-skills)
[![Codex](https://img.shields.io/badge/Codex-plugin-412991)](https://github.com/qiyuey/harness-skills)
[![evals](https://img.shields.io/badge/evals-L1_PASS_·_L2_6%2F6_·_L3_18%2F18-2ea44f)](evals/README.md)
[![License](https://img.shields.io/badge/license-Anti--996-blue)](https://github.com/996icu/996.ICU)

面向 AI agent 的通用 **LLM 工作流 harness 方法论**：审计、修复并扩展长时间、多步骤的 agent 工作流，让流程能断点续跑、局部重做、程序化质检、事后追溯。

## 快速开始

新用户优先安装完整插件。插件会一次性提供三个 skill：`harness-review`、`harness-fix`、`harness-build`。如果你的工具不支持插件，也可以用通用目录安装。

### Codex CLI

插件安装：

```bash
codex plugin marketplace add https://github.com/qiyuey/harness-skills
codex plugin install harness-skills
```

通用安装方式，在本仓库根目录运行：

```bash
mkdir -p ~/.agents/skills
cp -R skills/* ~/.agents/skills/
```

`~/.agents/skills` 也适用于 Gemini CLI、OpenCode、VS Code Copilot 等支持 Agent Skills 通用目录的工具。

### Claude Code

插件安装：

```bash
/plugin marketplace add qiyuey/harness-skills
/plugin install harness-skills@harness-skills
```

通用安装方式，在本仓库根目录运行：

```bash
mkdir -p ~/.claude/skills
cp -R skills/* ~/.claude/skills/
```

安装后直接描述你的目标即可，agent 会根据 skill 的 `description` 自动选择。需要手动点名时，用下面的路由规则。

| 你要做什么 | 使用 |
|------------|------|
| 审计一个多步骤 workflow skill 的 harness 设计 | `harness-review` |
| 修复一个已经暴露的 workflow bug，并防止复发 | `harness-fix` |
| 新增契约字段、sidecar、QC 规则或 pipeline step | `harness-build` |

## Agent 读取要点

当本 README 被 agent 作为项目上下文读取时，按以下规则使用：

- 只有任务涉及长时间、多步骤、可恢复的单 agent 工作流时，才使用本仓库的 skill。
- 需要审计 workflow 设计时用 `harness-review`。
- 已知 bug / 异常 / 失败症状需要系统修复时用 `harness-fix`。
- 新增字段、sidecar、QC 规则或 pipeline step 时用 `harness-build`。
- 项目专属路径、产物名、QC 脚本和失败案例不要写进通用 skill；放进消费方项目的 adapter、`AGENTS.md` 或 `CLAUDE.md`。
- 不要把 `evals/` 当作 skill 运行时依赖。

## 这个仓库解决什么

LLM 长链路工作流常见的问题不是“模型不会写”，而是流程不够抗失败：跑到一半中断、上下文丢失、某一步出错后只能从头再来、产物没有状态记录、失败无法复盘。

**harness** 指包在 LLM 外面、负责承接状态与编排执行的工程脚手架。它对应业界常说的 durable execution：把一条长流程做成可以恢复、可以局部重跑、可以审计的形态。

本仓库把这套工程原则压缩成纯文本 skill：

- 不引入运行时框架。
- 不绑定 Temporal、LangGraph、Inngest 等系统。
- 不提供领域业务规则。
- 只把“状态落盘 / 断点续做 / 局部重跑 / 程序化 QC / 可审计 / 可回归”写进 agent 可执行的工作流指令。

这些 skill 评判的是**流程能不能活下来**，不是内容写得好不好、业务指标对不对。

## 适用范围

适用：

- **多步骤 skill**：研究、抽取、验证、综合等阶段顺序执行，任意一步失败不应推倒重来。
- **cron / 定时任务**：周期性、无人值守运行，需要从上次落盘状态恢复。
- **长链路单 agent 流水线**：步骤多、耗时长、依赖中间产物落盘。

不适用：

- **多 agent 编排**：fan-out、投票、judge panel、agent 间通信等问题应交给编排层处理。
- **领域框架**：本仓库不内置金融、法务、数据分析等垂直行业规则。
- **运行时系统**：这里没有 Python SDK、队列、数据库、状态机服务。

一句话：本仓库只管**单个 agent 把一条长流水线跑稳**。

## 三个 skill

| skill | 触发场景 | 输出 |
|-------|----------|------|
| `harness-review` | 审计一个多步骤 workflow skill 的 harness 设计 | 九个维度的 PASS / FAIL 报告和修复建议 |
| `harness-fix` | 已经有具体 bug、异常或失败症状 | 根因分析、前置 guard、源头修复、防复发沉淀 |
| `harness-build` | 新增契约字段、sidecar、QC 规则或 pipeline step | 设计、实现、QC 更新、文档同步 |

选择规则：

```text
只是想检查稳不稳                 -> harness-review
已经坏了，要修并避免复发           -> harness-fix
还没有这个能力，要新增             -> harness-build
```

三个 skill 故意互斥，不再额外提供入口/分发 skill。这样 agent 只需要根据任务类型路由，不需要先加载一个总控说明。

## 项目适配器

本仓库保持通用，不包含任何消费方项目的路径、产物命名、QC 脚本名或真实失败案例。项目专属信息建议沉淀到一个 adapter，让 `harness-fix` / `harness-build` 先读到本项目语境，再套用通用方法论。

adapter 可以放在三种地方：

- **约定文件**：写进项目根的 `AGENTS.md` 或 `CLAUDE.md`。最轻量，适合规则少的项目。
- **本地 adapter skill**：放到 `<project>/.agents/skills/<project>-harness-adapter/SKILL.md`；只给 Claude Code 用时可放到 `<project>/.claude/skills/<project>-harness-adapter/SKILL.md`。
- **对话内联**：项目很小时，直接在运行 skill 时把路径、产物名、失败案例告诉 agent。

模板见 [docs/adapter-template.md](docs/adapter-template.md)。

## 工作流闭环

三个 skill 可以组成一个自进化闭环：

```text
harness-review 发现缺口
        |
        v
harness-fix 修复已知问题，并沉淀 guard / 回归案例
        |
        v
harness-build 扩展新契约、新 QC 或新步骤
        |
        v
harness-review 复检
```

沉淀的落点属于消费方项目或 adapter：QC 脚本、回归 fixture、失败案例库、项目规则文档。本仓库只提供通用方法论，不接管你的项目实现。

## 质量与验证

eval 套件位于 [evals/](evals/README.md)。因为这些是纯文本方法论 skill，不含运行时代码，测试重点是结构合规、行为覆盖和路由准确性。

| 层级 | 测什么 | 用 LLM? | 运行 |
|------|--------|---------|------|
| L1 Lint | `SKILL.md` frontmatter、交叉引用、零领域残留、指令极性 | 否 | `python3 evals/scripts/run_evals.py --layer l1` |
| L2 Behavioral | `harness-review` 能否识别植入缺陷的 workflow skill | 是，使用 `claude` CLI | `python3 evals/scripts/run_evals.py --layer l2` |
| L3 Trigger | 三个 skill 的路由准确率和互斥性 | 是，使用 `claude` CLI | `python3 evals/scripts/run_evals.py --layer l3` |

最近一次结果：**L1 PASS · L2 6/6 · L3 18/18**。

```bash
python3 evals/scripts/run_evals.py
python3 evals/scripts/run_evals.py --layer l1
```

## 仓库约束

- skill 本体只包含 `SKILL.md` 和 Markdown 引用文件。
- 不在 skill 内放共享运行时脚本。
- 不把 `evals/` 作为 skill 手动安装的依赖。
- 不把项目专属规则写进通用 skill；这些内容应进入消费方项目或 adapter。

## License

[Anti 996 License v1.0](LICENSE)（基于 [996.ICU](https://github.com/996icu/996.ICU)）—— 使用本项目即承诺遵守所在司法辖区的劳动法，不得违反 996 工作制。
