# harness-skills Evals

评估体系与 skills 同仓（闭环原则）：skill 改动时 evals 随之更新。

**核心差异**：harness-skills 是**纯方法论 skill**（无 runtime Python），所以三层金字塔的含义与脚本型 skill 不同——L1 不测"脚本输出数字"，而测"SKILL.md 本身是否自洽合规"。

## 三层评估金字塔

| 层 | 测什么 | 速度 | 依赖 | 何时跑 |
|----|--------|------|------|--------|
| **L1 Lint** | SKILL.md 自身合规：frontmatter 规范、零领域残留、内部交叉引用完整、**skills 是否遵守自己的指令正向性规则** | <2s | Python 标准库 | 每次改 SKILL.md 后必跑（CI 阻塞） |
| **L2 Behavioral** | 把"植入已知缺陷的 workflow SKILL.md"喂给 harness-review，断言它能检出这些缺陷 | ~2min | claude CLI | review 逻辑或审计维度细则改动后 |
| **L3 Trigger** | 显式调用路由 + 普通开发近邻误触发；每条默认独立运行 3 次 | ~3-5min | claude CLI | 改 description、调用策略或 adapter 入口后 |

## 快速上手

```bash
# L1（最常用，零 LLM，CI 默认）
python3 evals/scripts/run_evals.py --layer l1

# 全部三层
python3 evals/scripts/run_evals.py

# 单层
python3 evals/scripts/run_evals.py --layer l3
```

退出码：L1 失败返回 1（CI 阻塞）；L2/L3 失败打印 warning（除非 `--strict`）。

## L1 Lint — SKILL.md 自洽合规（零 LLM）

为什么 L1 对方法论 skill 最关键：这套 skill 的全部价值在于 SKILL.md 文本质量本身，没有脚本可回归。L1 把"skill 应有的品质"机械化：

| 检查 | 规则 | 来源 |
|------|------|------|
| **frontmatter 合规** | name kebab-case ≤64；description ≤1024 且无尖括号；允许通用字段及 Claude Code 官方 `disable-model-invocation` 扩展 | Agent Skills spec + Claude Code skills |
| **显式调用策略** | 三个 skill 均要求 Claude `disable-model-invocation: true`，且 Codex `agents/openai.yaml` 设置 `allow_implicit_invocation: false` | 防止普通开发误触发 harness workflow |
| **零领域残留** | skills/ 下不得出现金融词（ebitda/financial_snapshot/AKShare/IRR/rs_competition…）或绝对用户路径 | 通用库纯粹性约束 |
| **交叉引用完整** | SKILL.md 中引用的 `references/*.md` 文件必须存在 | 防文档悬空引用 |
| **语言中立** | skill 本体不得耦合具体编程语言（python3/.py/argparse/import 等）；方法论必须语言无关 | 通用库纯粹性约束 |
| **指令正向性自审** | harness-review 自己定义了"禁止行为/风格类负向指令"——三个 skill 自身的行为/风格类负向指令应当受控（吃自己的狗粮） | harness-review 维度 D3（指令极性）|
| **渐进披露** | SKILL.md body 行数告警阈值（建议 <500）；>300 行的 reference 应有目录 | anthropics 渐进披露 |

## L2 Behavioral — review 能否检出植入缺陷

`fixtures/` 下放**人工构造的有缺陷 workflow SKILL.md**，每个缺陷对应九条审计维度中的一项。把它喂给 harness-review，断言报告点名了该缺陷。

| fixture | 植入缺陷 | 期望 review 检出 |
|---------|---------|-----------------|
| `broken_workflow_skill.md` | 无 sidecar 持久化（A）、无 manifest（B）、联合 QC + 时机警告语（D）、语言禁令（G） | A/B/D/G 至少各 1 项 FAIL，且点名联合 QC 与负向指令 |

## L3 Trigger — 路由准确率 + 互斥性

测三件事：
1. **显式召回**：只有显式点名 `$harness-*`、`/harness-*` 或“运行 harness-*”的 query 才路由到对应 skill。
2. **互斥**：review / fix / build 的显式样本不串触发。
3. **近邻误触发**：普通应用 bug、schema、CI pipeline、GitHub Actions、API adapter 等共享关键词的开发任务必须返回 `none`；未显式调用的 harness 请求也必须返回 `none`。

`fixtures/trigger-evals.json` 每条标注 `expected_skill`（review/fix/build/none）。默认每条独立运行 3 次，任一次误触发都会计入失败；严格通过要求误触发、漏触发、串触发均为 0，attempt accuracy ≥95%。Codex/Claude 的平台调用策略由 L1 静态检查阻塞。

## 加新用例

- **L1**：在 `run_l1_lint.py` 加检查函数，或扩 `FORBIDDEN_TERMS`。
- **L2**：在 `fixtures/` 加一个植入新缺陷的 SKILL.md，在 `evals.json` 的 `l2_behavioral` 追加断言。
- **L3**：在 `fixtures/trigger-evals.json` 追加 `{"query":"...","expected_skill":"review|fix|build|none"}`。
