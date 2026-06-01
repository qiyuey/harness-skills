# Project Harness Adapter — Template

Copy this into your project as `.claude/skills/<project>-harness-adapter/SKILL.md` and fill the brackets. The adapter holds everything **specific** to your project that the generic `harness-skills` deliberately leaves out.

```markdown
---
name: <project>-harness-adapter
description: Project-specific harness rules for <project>. Loaded alongside generic harness-review / harness-fix / harness-build to supply this project's real paths, artifact names, QC script names, mandatory-path rules, and concrete failure-case library. Triggers only inside this project.
---

# <project>-harness-adapter

Generic methodology lives in the `harness-skills` plugin. This adapter supplies **this project's specifics**.

## Paths & artifacts
- skills dir: `<.claude/skills>`
- run/output layout: `<runs/{...}/{...}>`
- key sidecars: `<list>`
- QC scripts: `<qc_1.py ... qc_N.py>` and what each checks
- schema(s): `<schemas/...>`
- manifest/status entry: `<run_manifest.py status>`

## Mandatory rules (this project only)
- 禁止补丁式修法 / 强制路径 / 跨产物协同约束 等

## Failure-case library (concrete)
Real cases observed in this project, mapped to the generic taxonomy in `harness-fix`:

| 抽象类型（harness-fix taxonomy） | 本项目真实案例 | 根因文件:行 | 修复 |
|----------------------------------|----------------|-------------|------|
| 字段名不一致 | <真实字段对> | <file:line> | <fix> |
| QC 覆盖盲区 | <真实症状> | <qc file> | <fix> |
```

Keep this adapter the single place where project-specific knowledge accrues, so the generic skills never get polluted.
