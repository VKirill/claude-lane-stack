# ADR: Foreign dirt and owns-check

## Status
Accepted (2026-07-30)

## Context
Shared dirty mains and parallel sessions caused owns-check to block healthy
tasks on files they never touched.

## Decision
- `check-owns-paths` classifies uncommitted paths outside `owns_paths` as
  **foreign ignored** when no dirt baseline exists, or when the path was present
  in `dirt-baseline.json` at lane start.
- `lane-ctl start` writes `artifacts/<task_id>/dirt-baseline.json`.
- New paths outside owns (not in baseline) remain **violations** (writer leak).
- `never_touch` hard-fails for newly introduced hits (not pre-baseline foreign).
- Prefer worktrees for score≥4 / multi-write runs to reduce shared-main dirt.

## Consequences
False owns freezes from parallel sessions stop. Writer leaks are still caught
when baselines are written at start.
