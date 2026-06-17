# 项目 Harness 适配器 —— 模板

把本模板的内容拷进你的项目，填好尖括号部分。适配器承载所有**项目专属**的内容 —— 这些正是通用 `harness-skills` 刻意不包含的部分。

载体随你选（详见 README「配合项目适配器使用」）：

- **本地适配器 skill**：`.agents/skills/<project>-harness-adapter/SKILL.md`；如果只给 Claude Code 用，也可以放到 `.claude/skills/<project>-harness-adapter/SKILL.md`。作为 skill 使用时保留下方 frontmatter。
- **约定文件**：`AGENTS.md` / `CLAUDE.md` 里的一节，去掉 frontmatter、只留正文即可。

```markdown
---
name: <project>-harness-adapter
description: <project> 的项目专属 harness 规则。与通用 harness-review / harness-fix / harness-build 一同加载，为本项目提供真实路径、产物名、QC 脚本名、强制路径规则与具体失败案例库。仅在本项目内触发。
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

## 失败案例库（具体）
本项目观察到的真实案例，映射到 `harness-fix` 中的通用 taxonomy：

| 抽象类型（harness-fix taxonomy） | 本项目真实案例 | 根因文件:行 | 修复 |
|----------------------------------|----------------|-------------|------|
| 字段名不一致 | <真实字段对> | <file:line> | <fix> |
| QC 覆盖盲区 | <真实症状> | <qc file> | <fix> |
```

让适配器（无论以何种载体存在）成为项目专属知识唯一的沉淀处，通用 skill 才能始终保持纯净。
