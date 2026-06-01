# harness-skills

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

**harness（线束/支架）** 指包在 LLM 外面、负责承接状态与编排执行的那层工程脚手架。LLM 本身是非确定的、上下文易失的；harness 工程就是把它包裹成一个**状态可持久化、流程可恢复**的多步骤工作流。

这些 skill 不评判领域质量（数字是否正确、文笔是否好），只评判工作流的**工程稳定性**：它能否在中断后从已落盘的产物继续、能否只重跑出错的那一步、能否在事后被追溯排查。换句话说，它们守护的是「流程能不能活下来」，而不是「内容写得好不好」。

## 三个 skill

| skill | 适用场景 |
|-------|---------|
| **harness-review** | 按 7 个 harness 维度审计一个多步骤工作流 skill（状态持久化、断点续跑、局部重做、程序化 QC、可观测性、失败契约、指令极性）。输出 PASS/FAIL + 修复建议。 |
| **harness-fix** | 已经定位到某个具体 bug/异常。跑 3 层闭环：根因分析 → 加 guard（QC）→ 源头修复，确保不再复发。 |
| **harness-build** | 新增一个契约字段 / sidecar / QC 规则 / 流水线步骤。跑 4 层闭环：设计 → 实现 → QC → 文档。 |

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

[MIT](LICENSE)
