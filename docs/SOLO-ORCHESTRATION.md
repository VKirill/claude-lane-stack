# Solo orchestration (one human + one PM)

You work **alone** through **dev-orchestrator**. No multi-developer merge dance.

**Related:** [LANE-EXEC.md](LANE-EXEC.md) · [ONBOARD-SCENARIOS.md](ONBOARD-SCENARIOS.md) · [LANGUAGE.md](LANGUAGE.md) · [ROUTING.md](ROUTING.md)

## Non-negotiables

1. **Orchestrator owns `main`.** Workers never push/merge to main. PM merges when the run is green. If the repo has a remote (origin), PM pushes main immediately after merge/commit — merge without push is an unfinished ship. No remote -> local main is the end state.
2. **You never merge.** If PM asks you to merge, PM is wrong — fix the skill.
3. **Parallel only with ownership.** Disjoint `owns_paths` or serial.
4. **Worktree for parallel / score≥4.** Isolated branch → PM merges to main → deletes worktree.
5. **One visible supervisor per run.** `run-supervisor` watches one durable
   deterministic controller; Grok resumes only the writer session pool owned by
   that run and rotates after seven successful tasks.
6. **Receipts are truth.** Task YAML is immutable; `state.json` drives live
   STATUS/BOARD and only `acceptance.json` means done.
7. **Stall is recoverable.** No heartbeat → stalled → re-dispatch or other lane.
8. **Durable progressive accept.** `run-controller` dispatches detached Grok
   processes, reacts to receipts, and accepts each ready task without waiting
   for the slowest concurrent lane. The controller survives Claude restarts.
9. **Bounded pools.** Provider default 5/max 10; verification default 2/max 10.
10. **Fail-closed ship.** Commit, validation, finalize, then push; branch and
    worktree stay recoverable on any failure.
11. **Typed provider recovery.** Retry exact Grok once after a persisted
    deadline; only a second classified availability failure may use one
    ephemeral Codex Sol high writer attempt through the same receipts.

Daytime: micro/medium ship fast with exact checks and **no daytime LLM review**.
Night: `night-shift` performs typed Codex Sol
xhigh review and prepares verified Grok-primary fixes in an isolated worktree.
The same typed one-shot Sol high recovery is available after two classified
Grok availability failures; the independent xhigh re-review remains mandatory.
Morning: `resume-project` surfaces canonical findings and any repair run still
awaiting human or merge policy action.

Automatic nightly merge/push is disabled by default. A repository must opt in
through `.agents/night-shift.yaml`; high/critical fixes still require the
configured pre-merge gate. The runner is resumable, retries Grok once, and
allows at most one typed recovery attempt.

## Micro path

Applies when score 0–2, risk low, ≤2 files, and no `high_risk_paths`. PM
keeps the generated v2 files concise and ships in minutes.

- Skips: worktree, heartbeat ceremony, reviewer.
- Keeps: strict generated task, validation, `run-controller`, ownership/verification/
  acceptance receipts, PM commit to main.
- Commit: `<type>(<area>): <title> [micro:<slug>]`.

## Review tiers

| Tier    | Trigger                            | Review |
|---------|-------------------------------------|--------|
| none    | micro path / risk low               | verify field + check-owns-paths only |
| nightly | everything else (medium/high/ship)  | typed Sol xhigh findings; bounded Grok repair; fresh re-review |

Normal daytime runs never invoke an LLM reviewer. Historical or explicitly
configured `gate: pre-merge` runs stop for an operator decision instead of
silently starting a reviewer. The standard review/fix loop is nightly.

## End-state of every run

```
main ← contains the feature (merged by PM)
origin/main <- in sync (pushed by PM when remote exists)
.worktrees/<slug> ← gone
.agents/runs/<slug>/merge.json ← machine merge/push/install receipt
.agents/runs/<slug>/MERGE.md ← how/when merged
.agents/runs/<slug>/finalize.json ← applied PROGRESS/BOARD/OPEN actions
PROGRESS.md ← Now/Next updated
```

## Commands PM uses

| Command | When |
|---------|------|
| `project-memory-init` | new repo once |
| `resume-project` | cold start / new session |
| `run-init <repo> <slug>` | create a strict schema-v2 run |
| `run-validate --phase pre-dispatch\|pre-merge` | validate schema, DAG, scopes, and receipts |
| `wt-create <repo> <slug>` | start isolated run |
| `run-controller start/watch/status` | durable DAG dispatch, progressive acceptance, and live run status |
| `lane-heartbeat …` | worker or supervisor pulse |
| `lane-ctl start/status/events/tail` | low-level typed lifecycle control and diagnostics |
| `lane-ctl retry/cancel` | bounded recovery from recorded control state |
| `lane-ctl verify` | exact task checks under the separate verification semaphore |
| `lane-ctl accept` | write the sole technical done receipt |
| `lane-session status --run-dir …` | inspect run-owned Grok session IDs and rotations |
| `run-board <repo>` | refresh BOARD.md |
| `lane-stall-check <repo>` | find zombies |
| `check-owns-paths <task.yaml>` | after write lane |
| `wt-merge-main <repo> <slug>` | ship to main (PM only) |
| `run-finalize --run-dir …` | deterministic PROGRESS/BOARD/OPEN refresh |
| `night-audit <repo>` | overnight audit file |
| `night-review <repo>` | typed read-only review + canonical findings |
| `night-shift <repo>` | review + isolated bounded Grok repair loop |
| `night-shift-all` | discover configured projects and run the night shift |

## Human UX

- Talk only to **dev-orchestrator**.
- Say what you want; do not manage branches.
- Cold start: `/resume-project` or «продолжи» → PM reads BOARD + PROGRESS.
- During a run, the single `run-supervisor` remains visible until accepted or
  blocked; Lane Board reads `controller.json` and exact task runtime stages.
- If something stuck >5 min: «проверь stall» → PM runs stall-check + re-dispatch.

## Language

All agent-written files **English**. Chat with human **Russian**. See [LANGUAGE.md](LANGUAGE.md).
