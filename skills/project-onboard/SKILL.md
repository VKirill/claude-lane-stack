---
name: project-onboard
description: Primary project onboarding for Claude Lane Stack. Dual scenario (minimal vs full mature docs). Creates lean CLAUDE.md + pointer AGENTS.md, PROGRESS/LESSONS, .agents layout, agents-doctor profile. Use when: /project-onboard, онбординг, init project, bootstrap CLAUDE.md, новый репозиторий под оркестратор, «подготовь проект».
---

# Project onboard (Claude Lane Stack)

## Who runs it

| Role | Agent |
|------|--------|
| **Default writer** | **Codex** `gpt-5.6-terra` + **high** via `codex-onboarder` (sol if huge monorepo / full on large trees) |
| PM / slash | Claude dispatches `codex-onboarder` (`/project-onboard`) |
| Fallback only | shell `project-onboard` if `codex` CLI missing |

Also seeds: `docs/ARCHITECTURE.md` template, README anamnesis if missing. Full fill = Codex.

Do **not** use AGY or Grok for onboard. Do **not** have Fable write CLAUDE.md content by hand — dispatch Codex.

## Dual scenario (minimal vs full)

`project-onboard` **auto-detects** maturity and writes `.agents/onboard.scenario.yaml`.

| | **minimal** | **full** (mature) |
|--|-------------|-------------------|
| **Signals** | small src tree, few commits, no monorepo, no deploy stack | score ≥ 5: size, monorepo, deploy, docs depth, domain (auth/pay/jobs), tests, history |
| **Seeds** | CLAUDE · AGENTS · ARCHITECTURE · PROGRESS · LESSONS · plans · memory · routing | + GOTCHAS · GLOSSARY · TESTING · deployment · decisions · nested `apps/*/CLAUDE.md` · optional SECURITY |
| **Codex job** | Fill spine from evidence only | Fill **all** seeded stubs from evidence; respect existing lowercase wiki names |

**Override:**

```bash
project-onboard . --minimal
project-onboard . --full
ONBOARD_SCENARIO=full project-onboard .
```

Do **not** seed full pack on every greenfield — community rule: *earn every line*.

## Goal

Lean always-on `CLAUDE.md` + pointer `AGENTS.md` + `.agents/` + memory + **scenario-sized** docs from repo evidence. No duplicate rules in AGENTS.md.

## MUST

1. Prefer:

```text
Agent → codex-onboarder
PROJECT_CWD: /abs/repo
ARTIFACT_DIR: /abs/repo/.agents/runs/_onboard/artifacts/001
```

2. Fallback shell (no codex):

```bash
export PATH="$HOME/.agents/bin:$PATH"
project-onboard .
# or: project-onboard . --full
```

3. After onboard, reply in Russian: **scenario**, files created, doctor profile, gaps, next step PM.

4. **Never** invent architecture without evidence; mark hypotheses.

## Where things go (important)

| Kind | Path | Examples |
|------|------|----------|
| **Execution** (runs, tasks, reports, merge) | `.agents/runs/<slug>/` | PLAN.md, tasks/*.yaml, report.md |
| **Ideas** | `.agents/todos/` | backlog |
| **Session / debt** | `.agents/session-log/`, `agent-notes/` | auto ledger |
| **Living state** | `PROGRESS.md`, `LESSONS.md` | now/next, do/don't |
| **Durable product docs** | `docs/` | architecture, decisions, gotchas, SEO strategy, **COCOON** |
| **Active product plans** (human-facing strategy) | `docs/plans/<topic>/` | long SEO/product specs |
| **Onboard scenario** | `.agents/onboard.scenario.yaml` | minimal \| full + score |

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

### Always (minimal + full)

- [ ] `CLAUDE.md` + `AGENTS.md`
- [ ] `PROGRESS.md` / `LESSONS.md`
- [ ] `.agents/runs/BOARD.md` (via run-board)
- [ ] `.agents/routing.profile.yaml` (agents-doctor --apply)
- [ ] `.agents/onboard.scenario.yaml`
- [ ] `docs/ARCHITECTURE.md` (or existing architecture wiki)
- [ ] Karpathy skill linked

### Full only

- [ ] `docs/GOTCHAS.md` or existing gotchas filled
- [ ] `docs/GLOSSARY.md` if domain terms exist
- [ ] `docs/TESTING.md` with real commands
- [ ] `docs/deployment.md` from deploy evidence
- [ ] Nested `apps/*/CLAUDE.md` / `packages/*/CLAUDE.md` if monorepo
