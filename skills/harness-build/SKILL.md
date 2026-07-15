---
name: harness-build
description: 仅在用户显式调用 harness-build（Codex `$harness-build` 或 Claude Code `/harness-build`）时使用。为通过 Agent Skill 执行的长时、多步骤、可恢复 harness 工作流新增契约、sidecar、manifest、逐步 QC、可恢复 step，或创建和更新项目 harness adapter。普通产品功能、数据库或接口 schema、CI/CD pipeline step、一般代码生成、测试和文档变更不触发；已暴露的 harness 故障使用 harness-fix。
disable-model-invocation: true
metadata:
  category: workflow-harness
  role: build
---

# harness-build

将 harness 工作流能力落地为代码 + 契约 + QC 变更，并同步所有下游文档；也负责生成项目 harness adapter。

## 铁律（The Iron Law）

```
四层缺一即半成品：设计 → 实现 → QC → 文档，一个都不能少。
NO FEATURE IS DONE UNTIL ALL FOUR LAYERS LAND.
```

- 缺任何一层（无契约 / 无 QC 覆盖 / 无文档同步）都视为**未完成**，不得宣称落地。
- 一次只落地一个功能；多需求分多次调用，每次重新对齐范围。
- schema 是契约：实现不得超出 schema 定义的字段。

> **违背流程的字面，就是违背交付的精神。**

> **先验证再执行**：本 skill 是工作流参考，不是任何具体 repo 状态的真理来源。执行前必须用 `grep`/`find`/`sed` 验证实际脚本、Step 编号、产物路径和 QC 名称；若本文示例与 repo 不一致，以 repo 为准。

---

## 四层落地原则

每个新功能必须经过四层，缺任何一层都是半成品。这里的"契约"不一定是 JSON Schema；也可以是 SKILL.md、scripts/README.md、task reference 或现有 sidecar 结构说明：

```
层1 设计（Design）     ─── 字段/步骤定义、数据来源、向后兼容策略
        ↓
层2 实现（Implement）  ─── schema/契约变更 + 数据脚本 + 填充/消费逻辑
        ↓
层3 QC（Verify）       ─── 新字段/新步骤纳入现有 QC 或新增检查项
        ↓
层4 文档（Document）   ─── 对应 skill / README / 项目级说明文档同步
```

**中途回路**：任意步骤发现规格有误（数据源不支持、schema 冲突、Step 编号变了），立即回到 Step 0 重新对齐，不要强撑继续。

---

## 执行流程

### Step 0：确认输入规格

从对话上下文提取本次要落地的规格，尚未明确且无法从 repo 推断时才提问；在 Default mode 下优先做合理假设并继续，不要因为"最好确认"而暂停。

```
- 字段/步骤名称是什么？
- 数据从哪里获取（外部文件 / API / 浏览器抓取 / LLM 生成）？
- 写入哪个产物（现有 JSON/Markdown/表格/目录，或新 sidecar）？
- 是 optional 还是 required？现有历史产物是否需要回填？
- 由哪个 workflow step/task 负责填充？需要新建 step/task 吗？
- 影响的是哪个产物域（数据抽取、产物生成、复盘、QC、渲染），上下游消费者是谁？
```

若用户明确要求"直接做/继续"，不要等待确认；在最终回复中列出采用的规格假设。

---

### Adapter 模式

当用户显式调用 `harness-build --adapter <project>`，或明确要求生成/更新项目 harness adapter 时：

1. 定位项目中实际执行工作流的 `SKILL.md`，确认它确实是长时、多步骤、可恢复的单 agent 工作流。
2. 扫描现有 schema、sidecar、manifest/status、逐步 QC、运行目录和失败处理入口；只记录工具已经证实的路径与命令。
3. 默认以 `docs/adapter-template.md` 为结构，生成项目内的被动契约文件 `.harness/adapter.md`。被动文件不参与 skill 自动路由，由已显式激活的 harness skill 主动查找并读取。
4. 仅当用户明确要求 adapter 本身作为 skill 安装时，生成 `<project>-harness-adapter/SKILL.md`，并同时配置 Codex `policy.allow_implicit_invocation: false` 与 Claude Code `disable-model-invocation: true`。
5. 对无法从仓库证实的项目经验保留待填写标记；不得把推测写成强制规则。
6. 验证 adapter 至少包含真实的 workflow 路径、产物布局、QC、schema、manifest/status 和 regression hook；缺失项必须明确标为未发现或不适用。

adapter 是项目语境契约，不是第四个自动路由入口。普通 API/SDK、数据库或 UI adapter 不属于本模式。

---

### Step 1：设计（Design）

Read 相关契约文件确认当前定义，再设计新字段/新步骤：

```bash
# 先定位目标 workflow 的契约文件，不要假设固定路径
find <skills-dir> -maxdepth 2 -name SKILL.md
find <schemas-dir> <scripts-dir> -maxdepth 4 -type f | grep -E "(schema|README|qc_|manifest|postmortem|assemble|generate)"
# 再读取与本次改动直接相关的 SKILL.md / schema / README / helper / QC
```

输出设计稿：契约片段 + 字段/步骤说明 + 向后兼容策略（新 optional 字段不破坏历史产物 QC）。

---

### Step 2：实现（Implement）

**2a. 更新契约文件** — Edit 对应 schema / SKILL.md / scripts README / task reference。

**2b. 确认填充时机与方式** — 先 Read 当前目标 workflow 的 SKILL.md 确认步骤分配，不依赖本文件的任何步骤号记录。

| 写入场景 | 填充方式 |
|---------|---------|
| 现有 JSON sidecar | 在产生该 sidecar 的 step 一并写入，保持字段命名与契约一致 |
| 现有 Markdown/报告产物 | 在生成该章节/段落的 step 消费新约束，并在结构化快照中留痕 |
| 新 sidecar 文件 | 新建或扩展 step，并补充 manifest / QC / README 契约 |
| 跨 step 消费规则 | 增加 helper 读取入口，在上游快照写入"已消费"标记，下游 QC 验证 |
| QC 规则 | 找到最早能拦截问题的 step，优先加入该 step 的 QC |

新建 sidecar 时额外检查：
- schema/契约文件命名与现有项目约定一致
- QC 归入对应 step 的现有 QC；体量大时新建独立脚本，并在 manifest/README 中登记
- 若影响全项目目录结构或强制消费规则，同步项目级说明文档

**2c. 向后兼容** — 新字段默认 optional；但若能自动检测到历史产物存在且必须消费，QC 可对"未消费"FAIL。

---

### Step 3：更新 QC（Verify）

| 被检对象 | QC 选择原则 |
|---------|-------------|
| 单 step sidecar | 该 step 的 QC 脚本，或新增同粒度 QC |
| 跨 step 消费 | 最早消费点的 QC 检查"已消费/已留痕" |
| 终态报告/渲染产物 | 终态 validator + 必要的章节/图表专项 QC |
| 复盘/回填产物 | 回填产物 QC 检查状态变化、幂等性、下一轮可消费字段 |

新增检查项规范：字段存在时验证格式/约束；字段缺失时仅 WARNING（optional 字段）。

验证必须真跑，读取完整输出和 exit code，再声明结果：

```bash
# 用现有真实或最小样例确认仍 PASS（读 exit code）
<run-qc-command> <valid-fixture-or-artifact>
# 注入非法值确认能检出 WARNING/FAIL（真跑，不得跳过）
<run-qc-command> <bad-fixture-or-temp-artifact>
```

---

### Step 4：文档同步（Document）

| 文档 | 更新内容 |
|------|---------|
| 目标 workflow 的 `SKILL.md` | step/task 顺序、输入输出、失败契约、消费规则 |
| 目标 workflow 的 scripts README / task reference | sidecar / snapshot / helper 接口契约 |
| 项目级说明文档 | 只有当目录结构、强制消费规则或跨 workflow 约定变化时同步 |

---

### Step 5：端到端验证

文档同步后，优先做可重复、低成本的 smoke test；只有用户明确要求或风险很高时，才重跑完整昂贵 workflow。

轻量 smoke（推荐，按目标语言落地）：
- 对改动的源文件做**语法/编译检查**（编译型语言编译、解释型语言做 parse/lint）
- **加载新 helper + 构造最小样例**，确认能产出预期结构
- 对该最小样例**跑相关 QC**，确认 PASS

---

## 注意事项

- **不要在 SKILL.md 里存储待办清单** — 具体要加什么字段来自对话对齐，不属于 skill 定义
- **一次只落地一个功能** — 多个需求分多次调用，每次 Step 0 确认当次范围
- **schema 变更是契约** — 改完 schema 后所有实现必须向它看齐，不允许实现超出 schema 定义的字段

---

## 与其他 skill 的关系

| skill | 关系 |
|-------|------|
| `harness-fix` | 互斥：fix 修已知 bug，build 落地新功能 |
| `harness-review` | build 完成后可用 review 审计新增 step/字段是否满足各审计维度 |
| 项目 harness adapter | 提供该项目的路径/产物/命名约定；build 时先 Read adapter 对齐项目规则 |
