# Onboard scenarios (minimal vs full)

Claude Lane Stack does **not** dump the same docs into every repo. `project-onboard` scores maturity and picks a path.

## Detection

Written to `.agents/onboard.scenario.yaml`.

| Signal | Points (approx) |
|--------|-----------------|
| Workspace tool (pnpm/turbo/nx/lerna) | +3 |
| ≥2 packages under apps/packages/services | +3 |
| Source files ≥40 / ≥120 / ≥400 | +1 / +2 / +3 |
| Deploy signals (Docker, PM2, k8s, CI, …) | +1–2 |
| Existing docs depth | +1–2 |
| Domain (auth, payments, queues, workers) | +2 |
| Solid test layout | +1 |
| Git commits ≥50 / ≥200 | +1 / +2 |

**full** if `score ≥ 5` or multi-package monorepo. Else **minimal**.

Override: `project-onboard . --minimal | --full` or `ONBOARD_SCENARIO=…`.

## What gets seeded

### Minimal (greenfield / small)

- `CLAUDE.md`, `AGENTS.md`
- `docs/ARCHITECTURE.md`
- `PROGRESS.md`, `LESSONS.md`
- `docs/plans/README.md`
- `.agents/` memory + routing + BOARD
- README anamnesis if missing

### Full (mature)

Everything above, plus stubs for:

- `docs/GOTCHAS.md`
- `docs/GLOSSARY.md`
- `docs/TESTING.md`
- `docs/deployment.md`
- `docs/decisions.md` (if missing)
- nested `apps/*/CLAUDE.md`, `packages/*/CLAUDE.md`
- `docs/SECURITY.md` when domain complexity detected

**Skip seed** if a case-insensitive sibling already exists (`gotchas.md` vs `GOTCHAS.md`).

## Who fills content

| Step | Who |
|------|-----|
| Detect + seed empty templates | `project-onboard` (bash) |
| Fill from **repo evidence** | Codex `codex-onboarder` (`gpt-5.6-terra` high) |
| Nightly honesty | `docs-maintain` (respects scenario; no full-pack on minimal) |

## Language

All durable docs: **English**. See [LANGUAGE.md](LANGUAGE.md).
