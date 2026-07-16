# Solo orchestration (one human + one PM)

You work **alone** through **dev-orchestrator**. No multi-developer merge dance.

**Related:** [LANE-EXEC.md](LANE-EXEC.md) · [ONBOARD-SCENARIOS.md](ONBOARD-SCENARIOS.md) · [LANGUAGE.md](LANGUAGE.md) · [ROUTING.md](ROUTING.md)

## Non-negotiables

1. **Orchestrator owns `main`.** Workers never push/merge to main. PM merges when the run is green. If the repo has a remote (origin), PM pushes main immediately after merge/commit — merge without push is an unfinished ship. No remote -> local main is the end state. 
2. **You never merge.** If PM asks you to merge, PM is wrong — fix the skill. 
3. **Parallel only with ownership.** Disjoint `owns_paths` or serial. 
4. **Worktree for parallel / score≥4.** Isolated branch → PM merges to main → deletes worktree. 
5. **Bounded warm writer context.** Each task gets a fresh Claude supervisor spawn, while Grok resume only the session pool owned by that exact run. Rotate after seven successful tasks; review stays fresh.
6. **Board is truth.** `.agents/runs/BOARD.md` + run `STATUS.md`. 
7. **Stall is recoverable.** No heartbeat → stalled → re-dispatch or other lane. 
8. **Progressive accept.** Multi-task runs accept each task when *it* finishes
   (`lane-poll` + `MODE=finish`) — never join-wait the slowest concurrent lane.

Daytime: micro/medium ship fast. Night: `night-review` batch. Morning: fix tasks from `REVIEW-<date>.md`.
Automation: night-review runs from cron (03:00) per repo; morning `resume-project` surfaces REVIEW-<date>.md with the fix plan.

## Micro path

Applies when score 0–2, risk low, ≤2 files, and no `high_risk_paths`. PM
skips the full run ceremony and ships in minutes.

- Skips: PLAN.md, worktree, `run-board`, `STATUS.md`, `lane-heartbeat`, reviewer.
- Keeps: minimal task YAML, `lane-bg` for the CLI call, `check-owns-paths`, PM commit to main.
- Commit: `<type>(<area>): <title> [micro:<slug>]`.

## Review tiers

| Tier    | Trigger                            | Review |
|---------|-------------------------------------|--------|
| none    | micro path / risk low               | verify field + check-owns-paths only |
| nightly | everything else (medium/high/ship)  | night-review batch (sol): verdicts + Morning fix plan; FAIL -> morning fix task, never ignored |

Pre-merge gate is OFF by default (solo, no-user products). When a project
serves real users or money, re-enable per project: add `gate: pre-merge` to
PROGRESS.md Pointers (or set `gate: pre-merge` in a task YAML) — then
codex-reviewer (sol high; xhigh for auth/pay/schema/migrations/security)
must pass BEFORE merge for high-risk work in that project.

## End-state of every run

```
main ← contains the feature (merged by PM)
origin/main <- in sync (pushed by PM when remote exists)
.worktrees/<slug> ← gone
.agents/runs/<slug>/MERGE.md ← how/when merged
PROGRESS.md ← Now/Next updated
```

## Commands PM uses

| Command | When |
|---------|------|
| `project-memory-init` | new repo once |
| `resume-project` | cold start / new session |
| `wt-create <repo> <slug>` | start isolated run |
| `lane-heartbeat …` | worker or supervisor pulse |
| `lane-session status --run-dir …` | inspect run-owned Grok session IDs and rotations |
| `run-board <repo>` | refresh BOARD.md |
| `lane-stall-check <repo>` | find zombies |
| `lane-poll --run-dir <run>` | multi-task progressive: which lanes are finish_ready |
| `lane-mode-check --run-dir <run> --mode …` | refuse MODE=full on multi-task (anti join-wait) |
| `check-owns-paths <task.yaml>` | after write lane |
| `wt-merge-main <repo> <slug>` | ship to main (PM only) |
| `night-audit <repo>` | overnight audit file |

## Human UX

- Talk only to **dev-orchestrator**. 
- Say what you want; do not manage branches. 
- Cold start: `/resume-project` or «продолжи» → PM reads BOARD + PROGRESS. 
- If something stuck >5 min: «проверь stall» → PM runs stall-check + re-dispatch.

## Language

All agent-written files **English**. Chat with human **Russian**. See [LANGUAGE.md](LANGUAGE.md).
