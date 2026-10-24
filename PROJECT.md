---
title: Claude Lane Stack agent reference
updated: 2026-10-24
sources:
  - bin/run-controller
  - bin/run-init
  - bin/run-validate
  - bin/pipeline_stages.py
  - plugins/lane-stack/.claude-plugin/plugin.json
  - hooks/guard_code_quality.py
  - hooks/lane_statusline_session.py
  - plugins/lane-stack/hooks/jev-router.ts
  - board/server/server.mjs
  - bin/lane_memory.py
  - docs/architecture.md
  - docs/data-model.md
  - docs/gotchas.md
---
# Claude Lane Stack agent reference

## Identity

- CLI orchestration for coding agents; plugin metadata: `plugins/lane-stack/.claude-plugin/plugin.json:1-19`.
- Read [overview](docs/overview.md) and [architecture](docs/architecture.md).

## Entry points

- User-facing PM: `lane-pm` (`bin/lane-pm:1-45`).
- Install host tools: `./install.sh` (`install.sh:1-30`).
- Run lifecycle: `run-init`, `run-validate`, `run-controller` (`bin/run-init:185-270`, `bin/run-validate:410-450`, `bin/run-controller:117-159`).
- Stage map and defaults: `bin/pipeline_stages.py:193-300`; see [ROUTING.md](docs/ROUTING.md).
- Hook reference: [HOOKS.md](docs/HOOKS.md).

## Critical invariants

- Task scope is expressed through `owns_paths` and `never_touch` (`schemas/task-v2.schema.json:90-145`).
- Acceptance validation binds receipts to task identity and verifies evidence (`bin/run-validate:348-421`). See [data model](docs/data-model.md).
- Provider execution outcome is recorded separately from the task contract (`schemas/outcome-v1.schema.json:1-140`).
- Lane Board endpoints are reads; unsupported API writes return 404 or 405 (`board/server/server.mjs:216-227`).

## Conventions

- Keep run/task contracts and receipts in project `.agents/runs/<slug>/` (`bin/run-init:185-270`).
- Provider-specific behavior belongs in stage configuration and adapter hooks; see [routing](docs/ROUTING.md) and [hooks](docs/HOOKS.md).
- Keep provider and routing behavior in the stage defaults and adapters (`bin/pipeline_stages.py:205-300`, `plugins/lane-stack/hooks/jev-router.ts:105-129`).

## Common gotchas

- A report is not acceptance evidence; validate task receipts (`bin/run-validate:348-421`).
- The memory SQLite index is derived from Markdown source records (`bin/lane_memory.py:468-510`).
- Read [gotchas](docs/gotchas.md) before changing lifecycle or hook behavior.

## Useful commands

- `./install.sh` — install host tools (`install.sh:1-30`).
- `project-onboard .` — create the project passport (`bin/project-onboard:40-55`).
- `lane-pm` — start the PM (`bin/lane-pm:1-45`).
- `run-validate --run-dir PATH --phase PHASE` — validate a run phase (`bin/run-validate:1-35`).
