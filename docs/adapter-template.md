# 项目 Harness 适配器 —— 模板

把本模板的内容拷进你的项目，填好尖括号部分。适配器承载所有**项目专属**的内容 —— 这些正是通用 `harness-skills` 刻意不包含的部分。

载体随你选（详见 README「配合项目适配器使用」）：

- **本地适配器 skill**：`.agents/skills/<project>-harness-adapter/SKILL.md`；如果只给 Claude Code 用，也可以放到 `.claude/skills/<project>-harness-adapter/SKILL.md`。作为 skill 使用时保留下方 frontmatter。
- **约定文件**：`AGENTS.md` / `CLAUDE.md` 里的一节，去掉 frontmatter、只留正文即可。

```markdown
---
name: <project>-harness-adapter
description: <project> 的项目专属 harness 规则。与通用 harness-review / harness-fix / harness-build 一同加载，为本项目提供真实路径、产物名、QC 脚本名、强制路径规则与项目 playbook。仅在本项目内触发。
---
（仅当载体是 skill 时需要上面的 frontmatter；写进 AGENTS.md / CLAUDE.md 时删掉它。）

# <project>-harness-adapter

通用方法论位于 `harness-skills` 插件中。本适配器提供**本项目的具体信息**。

## 路径与产物
- skills 目录：`<.agents/skills 或 .claude/skills>`
- 运行/输出布局：`<runs/{...}/{...}>`
- 关键 sidecar：`<列出>`
- QC 脚本：`<qc_1 ... qc_N>` 以及各自检查什么
- schema：`<schemas/...>`
- manifest/status 入口：`<run_manifest status>`

## 强制规则（仅本项目）
- 强制修复纪律 / 强制路径 / 跨产物协同约束 等

## 项目 playbook：失败逃逸与防线
本节只承载项目专属语境。优先把失败逃逸升级为可执行防线：契约、QC、注入测试、回归 fixture 或 trigger eval。只有暂时无法程序化的经验，才作为案例写在这里。

### 已程序化的防线

| 抽象类型（harness-fix taxonomy） | 本项目真实症状 | 已升级的防线 | regression hook |
|----------------------------------|----------------|--------------|-----------------|
| 字段名不一致 | <真实字段对> | <schema/QC/helper 修复> | <test/eval/fixture> |
| QC 覆盖盲区 | <真实症状> | <新增 QC + 注入坏样本> | <test/eval/fixture> |

### 暂未程序化的项目经验

| 抽象类型（harness-fix taxonomy） | 本项目经验 | 暂无法程序化原因 | 下次升级入口 |
|----------------------------------|------------|----------------|--------------|
| <类型> | <经验> | <原因> | <计划补的 QC/test/eval 或 N/A> |
```

让适配器（无论以何种载体存在）成为项目专属知识唯一的沉淀处，通用 skill 才能始终保持纯净。
