# harness-skills

Generic **LLM workflow harness methodology** for AI agents (Claude Code / Codex).

"Harness engineering" = wrapping an unreliable LLM into a **stable, recoverable** multi-step workflow. These skills don't judge domain quality (是否数字对、文笔好). They judge whether a workflow **survives interruption, token exhaustion, partial failure, and post-mortem investigation**.

## What's inside

| skill | use when |
|-------|----------|
| **harness-review** | Audit a multi-step workflow skill against 7 harness dimensions (state persistence, resume, partial re-do, programmatic QC, observability, failure contract, instruction polarity). Output PASS/FAIL + fixes. |
| **harness-fix** | A specific bug/anomaly is already known. Run the 3-layer loop: root-cause → guard (QC) → source fix, so it can't recur. |
| **harness-build** | Add a new contract field / sidecar / QC rule / pipeline step. Run the 4-layer loop: design → implement → QC → docs. |

### Routing (no entry skill by design)

Per Anthropic's skills guidance, **the `name` + `description` frontmatter is what makes the model decide when to trigger a skill** — routing belongs there, not in a separate dispatcher. Each of the three `description`s already encodes mutually-exclusive triggers and handoffs, so there is **no `using-harness` router**.

> Note: Superpowers' `using-superpowers` is *not* a router — it's a SessionStart **bootstrap** that injects "you have skills, use the Skill tool" into context, justified by its dozens of skills. With three self-describing skills that bootstrap has no payoff here. If this repo grows past ~6 skills, revisit — a `harness-skills-sync` skill (cf. baoyu/qiyuey `hermes-skills-sync` and Superpowers `pulling-updates-from-skills-repository`) is a higher-value 4th skill than an entry router.

Pick directly:

```
审计一个多步骤 skill 的 harness 设计      → harness-review
修复一个已知的 workflow bug，且要防复现   → harness-fix
新增字段 / sidecar / QC 规则 / step       → harness-build
不确定是 fix 还是 build？
  • 症状是"已经坏了" → harness-fix
  • 需求是"还没有这个能力" → harness-build
```

## Install

### Full plugin (all three skills)

Add this repo as a plugin (Claude Code reads `.claude-plugin/plugin.json`; Codex reads `.codex-plugin/plugin.json`). Skills are auto-discovered from `skills/`.

### Single skill

Copy one skill folder into your project's `.claude/skills/`:

```bash
cp -r harness-skills/skills/harness-review /path/to/project/.claude/skills/
```

Each skill works on text methodology alone — no runtime Python, no shared script package.

### Using with a project adapter

This repo stays **generic**. Project-specific rules (paths, artifact names, QC script names, real failure cases) live in a **local adapter skill** in the consuming project, e.g.:

```
<project>/.claude/skills/<project>-harness-adapter/SKILL.md
```

At runtime, `harness-fix` / `harness-build` Read the adapter first to pick up project paths and the project's real failure-case library, then apply the generic methodology here. See `docs/adapter-template.md` for a starter.

## Non-goals

- Not a domain framework (not equity research, not any vertical).
- Provides **no** generic QC scripts — concrete QC belongs to the consuming project or its adapter.
- Does **not** replace a project's local adapter.

## Scripts / automation policy

v1 ships **only `SKILL.md` + Markdown references** — no runtime `.py`, no npm workspace, no shared script package. A single skill must work on text methodology after install.

If v2 needs automation, add a top-level `tools/` or `scripts/` used **only for repo maintenance**, never as a skill runtime dependency.

## Upstream sync (for forks / consuming projects)

A consuming project that locally customizes a skill should track this repo as the upstream base and record a sync log, mirroring the `sync-upstream-skill` pattern:

| date | upstream commit (new base) | action | notes |
|------|----------------------------|--------|-------|
| 2026-06-01 | (initial) | fork base established | |
