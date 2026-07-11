---
name: project-onboard
description: Primary project onboarding for Claude Lane Stack. Creates lean CLAUDE.md + pointer AGENTS.md, PROGRESS/LESSONS, .agents layout, agents-doctor profile. Use when: /project-onboard, онбординг, init project, bootstrap CLAUDE.md, новый репозиторий под оркестратор, «подготовь проект».
---

# Project onboard (Claude Lane Stack)

## Goal

One lean always-on context file + execution home under `.agents/` + memory pack. **No** duplicate instruction walls in AGENTS.md.

## MUST

1. Run from **repo root** (git top-level preferred).

```bash
export PATH="$HOME/.agents/bin:$PATH"
project-onboard .
# or: project-onboard . --force   # overwrite CLAUDE.md sections carefully
```

2. If script unavailable, create files per **templates** below (same layout).

3. After onboard, reply in Russian:
   - what was created
   - profile from `agents-doctor`
   - next: `claude --agent dev-orchestrator` or continue current PM

4. **Never** invent long architecture essays into CLAUDE.md — only non-obvious facts + pointers to `docs/`.

## Where things go (important)

| Kind | Path | Examples |
|------|------|----------|
| **Execution** (runs, tasks, reports, merge) | `.agents/runs/<slug>/` | PLAN.md, tasks/*.yaml, report.md |
| **Ideas** | `.agents/todos/` | backlog |
| **Session / debt** | `.agents/session-log/`, `agent-notes/` | auto ledger |
| **Living state** | `PROGRESS.md`, `LESSONS.md` | now/next, do/don't |
| **Durable product docs** | `docs/` | architecture, decisions, SEO strategy, **COCOON** |
| **Active product plans** (human-facing strategy) | `docs/plans/<topic>/` | long SEO/product specs |

**COCOON.md / strategy decks belong in `docs/plans/…`.**  
**Implementable coding work** for the orchestrator belongs in **`.agents/runs/`** with task YAML.

If user says «делай / реализуй» after a docs plan → **promote**: create `.agents/runs/<slug>/` from that plan (do not re-plan only in docs/).

## CLAUDE.md tone (community 2026)

- **≤ ~150–200 lines** always-on context (shorter better).  
- **EN** for rules (models follow better); RU ok for human-facing notes outside.  
- Critical first: Never/Always, verify commands, gotchas.  
- **Pointers** to docs, not full wiki dump.  
- No stack 101 the model already knows.  
- Section **Lane Stack** if this project uses orchestrator.  
- Section **Karpathy** pointer (skill `karpathy-guidelines`).  
- Compounding: after repeated mistakes → add one line to LESSONS or CLAUDE Never.

## AGENTS.md

```markdown
# Agents

Read **[CLAUDE.md](./CLAUDE.md)** — single source of project instructions for all coding agents (Claude, Codex, AGY, Grok).

Do not duplicate rules here.
```

Optional symlink: `ln -sfn CLAUDE.md AGENTS.md` (some tools prefer real file).

## Karpathy

Ensure skill exists globally (`~/.agents/skills/karpathy-guidelines` or Claude skills).  
CLAUDE.md must say: *Follow karpathy-guidelines on any non-trivial code change.*

## After onboard checklist

- [ ] `CLAUDE.md` + `AGENTS.md`
- [ ] `PROGRESS.md` / `LESSONS.md`
- [ ] `.agents/runs/BOARD.md` (via run-board)
- [ ] `.agents/routing.profile.yaml` (agents-doctor --apply)
- [ ] Karpathy skill linked
