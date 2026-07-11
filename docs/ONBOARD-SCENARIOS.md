# Onboard scenarios + depth

Claude Lane Stack onboarding has **two axes**.

## Axis 1 — Scenario (`minimal` | `full`)

What files get **seeded**.

| Scenario | When | Seeds |
|----------|------|--------|
| **minimal** | score &lt; 5 | CLAUDE, AGENTS, ARCHITECTURE, memory, plans |
| **full** | score ≥ 5 or multi-package monorepo | + GOTCHAS, GLOSSARY, TESTING, deployment, nested CLAUDE, optional SECURITY |

Signals: workspace tools, multi-package, src size, **nested** deploy files (maxdepth 3), docs depth, domain keywords, tests, git history.

Override: `project-onboard . --minimal | --full` or `ONBOARD_SCENARIO=…`.

## Axis 2 — Depth (`fast` | `deep`)

How hard **Codex** must analyze before `STATUS: complete`.

| Depth | Default | Behavior |
|-------|---------|----------|
| **fast** | minimal scenario | Passport fill; shallow explore OK |
| **deep** | full scenario | Forensic: entrypoints, module walk, 3–7 flows, wiki↔code audit, run verify, ship/secrets surface |

Override: `project-onboard . --deep | --fast` or `ONBOARD_DEPTH=…` or `/project-onboard deep`.

Written to `.agents/onboard.scenario.yaml` as `depth:`.

## Auto evidence

`project-onboard` always writes:

`.agents/runs/_onboard/artifacts/001/deep-scan.md`

— top-level listing, git status/log, entrypoints, largest source files, docs index, deep checklist reminder.

Codex **must** read this when depth=deep.

## Who fills content

| Step | Who |
|------|-----|
| Detect + seed + deep-scan | `project-onboard` (bash) |
| Fill from evidence | Codex `codex-onboarder` (sol for deep, terra for fast) |
| Nightly honesty | `docs-maintain` (respects scenario; does not invent full-pack on minimal) |

## Models

| Depth | Model |
|-------|--------|
| fast | gpt-5.6-terra high |
| deep | gpt-5.6-sol high |

## Language

All durable docs: **English**. See [LANGUAGE.md](LANGUAGE.md).

## Slash

```
/project-onboard
/project-onboard deep
/project-onboard fast
/project-onboard /path/to/repo deep
```
