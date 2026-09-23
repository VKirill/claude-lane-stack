# ADR: Verification tiers L0 / L1 / L2

## Status
Amended (2026-09-24); accepted 2026-07-30

## Context
Running full package suites inside every writer and again in the controller
wastes tokens/CPU on multi-task runs and amplifies false reds from foreign dirt.

## Decision
| Tier | Owner | Scope | When |
|------|-------|-------|------|
| L0 | Writer | Implement only; do not execute test/typecheck runners | During implement |
| L1 | Controller `lane-ctl verify` | Task YAML `verification[]` only | After report → accept |
| L2 | PM pre-merge / CI | One full or affected suite | After all accepted |

Writer contracts forbid executing tests, typecheck, and `verification[]`.
`run-validate` warns on heavy per-task verification in multi-task pre-dispatch.

## Consequences
Acceptance criteria describe behavior; "all packages green" is an L2 concern.
