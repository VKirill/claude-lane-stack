---
name: orchestrator-lanes
description: Solo file-based multi-lane orchestration. Durable switchable AGY/Grok controller, no daytime LLM review, nightly Codex review/fix, PM auto-merges to main.
---

# Orchestrator lanes — solo operator

Load: **karpathy-guidelines**, **lane-contract**, **project-memory**, **resume-project**.

Docs: `FILE-CONTRACT.md`, `ROUTING.md`, `SOLO-ORCHESTRATION.md` under `/home/ubuntu/.agents/docs/`.

You are the **only** person who merges to `main`. Human never merges.

## Phase 0 — Score (announce once)

+2 multi-problem · +2 UI/state/auth/pay · +2 backend/API · +2 multi-surface · +2 needs verify · +3 prod/billing/security

| Score | Path |
|------:|------|
| 0–2 | Micro: 1 short generated contract, no heartbeat/reviewer, **commit main** |
| 3–6 | Express: 1 task, dispatch, verify, **commit/merge main** |
| 7–8 | Brief: 2–4 tasks, PLAN.md, worktree if ≥2 writes |
| 9–10 | Full: SPEC + DAG + worktree |
| 11+ | Split feature; ask user |

### Micro path (score 0–2)

Trigger: score 0–2 **and** risk low **and** ≤2 files **and** no
`high_risk_paths` (auth/pay/schema/migrations/security).

Keeps generated schema-v2 PLAN/SPEC/STATUS files short; skips worktree,
heartbeat ceremony, and reviewer.

Keeps: strict task YAML from `run-init`, pre-dispatch validation, `lane-bg` for
the CLI call, `check-owns-paths`, independent verify, `lane-ctl accept`, and PM
commit to main.

Micro commit format: `<type>(<area>): <title> [micro:<slug>]`.

Default writer is AGY `gemini-3.6-flash-high`; Grok 4.5 remains selectable with
`--provider grok`. The controller retries the selected provider once after a persisted
backoff; a second classified model/catalog/quota/auth/transport failure uses one
integrated `gpt-5.6-sol` + `high` Codex attempt through the same receipt chain.

Target latency: < 3 minutes word-to-commit.

## Phase 1 — Files

**Not** `docs/plans/` for coding execution.
`docs/plans/` = strategy (COCOON, product). Promote strategy → run when implementing.

```bash
run-init "$(pwd)" <slug> --score <score>
# Replace every REPLACE_ME in tasks/001.yaml; split into numbered tasks as needed.
run-validate --run-dir "$(pwd)/.agents/runs/<slug>" --phase pre-dispatch
run-board "$(pwd)"
```

`run-controller` repeats this validation at startup and before every new DAG
dispatch wave; a changed contract never rides on an earlier successful check.

Every new task is schema v2 and immutable after first start. It must declare
`read_first`, `interfaces`, `invariants`, `out_of_scope`, `expected_outputs`,
`owns_paths`, `never_touch`, `depends_on`, behavioral `acceptance`, and
structured verification commands. Parallel tasks: **disjoint** owns_paths.

## Phase 2 — Isolation

| Condition | Action |
|-----------|--------|
| score ≥ 4 **or** ≥2 write tasks | `wt-create "$(pwd)" <slug>` → set all `project_cwd` to worktree path |
| 1 low-risk task | may use main checkout; still only PM commits |
| high-risk write | worktree + **no** parallel writers |

```bash
wt-create /abs/repo <slug>
# → prints WORKTREE_PATH=... BRANCH=agent/<slug>
```

## Phase 3 — Dispatch (durable, bounded)

Provider concurrency defaults to **5** and is configurable from **1–10**.
Verification has a separate pool, default **2**, also bounded at **10**. High
risk work remains solo. Parallel writers require **disjoint owns_paths**.

One source-read-only `run-supervisor` stays visible for the whole run. It starts
the durable `run-controller`, performs bounded `watch` calls, and returns only
when the run is accepted or blocked. The controller, not the model, owns the
DAG and progressive acceptance. `lane-bg`, `lane-exec`, and `lane-session` own
the detached controller/provider process lifetimes.
Automated Grok writer processes disable imported Claude lifecycle hooks and
set the lane automation marker consumed by the native session-ledger hook.
Neither source can mutate the task worktree; Claude-compatible skills, rules,
and non-ledger safety hooks remain available.

```text
1) `run-controller start` validates/resumes one durable worker for the run.
2) Agent run-supervisor watches bounded state changes until terminal.
3) Controller fills provider slots with ready DAG tasks.
4) Complete provider report → owns check → verify → accept immediately.
5) Incomplete/failed/stalled provider or failed verification retries once.
6) A second fallback-eligible Grok availability failure starts one typed Codex
   Sol high attempt; every other second failure becomes blocked.
```

Required run dispatch fields are `RUN_DIR` and `PROJECT_CWD`. `lane-ctl start`
builds each writer prompt from the shared `agents/grok/writer.md` contract plus the raw task YAML,
registers immutable argv in
`attempts/<nn>/control.json`, and appends lifecycle records to run-level
`events.jsonl`.

```text
You are run-supervisor.
RUN_DIR: /absolute/repo/.agents/runs/<slug>
PROJECT_CWD: /absolute/worktree
Run `run-controller start --provider agy|grok`, then bounded `watch` calls until accepted/blocked.
Never edit source and never return while the controller is still running.
```

| `lane` | Agent |
|--------|--------|
| agy / grok | one run-supervisor (read-only watch); selected provider processes are writers |
| codex fallback | automatic Sol high write only after two eligible Grok failures |
| codex-implementer | manual emergency recovery after the typed controller blocks |
| codex-review-medium | codex-reviewer (sol xhigh) |
| codex-review | codex-reviewer |

### Control-plane commands

```bash
run-controller start --run-dir "$RUN_DIR" --project-cwd "$PROJECT_CWD" --provider agy
run-controller watch --run-dir "$RUN_DIR" --timeout 240
run-controller status --run-dir "$RUN_DIR" --json
lane-ctl start --run-dir "$RUN_DIR" --task-file "$TASK_FILE" --project-cwd "$PROJECT_CWD"
lane-ctl status --run-dir "$RUN_DIR" --task-id "$TASK_ID" --json
lane-ctl events --run-dir "$RUN_DIR" --task-id "$TASK_ID" --json
lane-ctl fallback --run-dir "$RUN_DIR" --task-id "$TASK_ID" # controller/recovery only
lane-ctl verify --run-dir "$RUN_DIR" --task-file "$TASK_FILE" --project-cwd "$PROJECT_CWD"
check-owns-paths "$TASK_FILE" --run-scope
lane-ctl accept --run-dir "$RUN_DIR" --task-file "$TASK_FILE" --project-cwd "$PROJECT_CWD"
```

Docs: `~/.agents/docs/LANE-EXEC.md`. Primary run bin: `run-controller`; `lane-ctl`
is the typed task control layer. Low-level
compatibility bins remain `lane-bg`, `lane-wait`, `lane-poll`, `lane-mode-check`,
`lane-exec`, and `lane-session`.

After controller start, `controller.json` exposes the exact run stage, counts,
last event, and next action. Each task `state.json` exposes its exact stage.
Never edit task YAML after dispatch.
After each accept: `acceptance.json` becomes the sole done receipt, freeing the
slot and unlocking `depends_on` dependents.

**Detached heartbeat:** `lane-exec --heartbeat ARTIFACT/heartbeat.json` writes
only on real activity (stdout/CPU). Run-level events distinguish registered live
work from old task YAML and completed historical runs.

## Phase 4 — Accept (per-task, as soon as ready)

**Progressive accept is mandatory for multi-task runs.** When task A verifies
while B and C still run: accept A **now**, write its done receipt, free its slot, start the
next ready task if any. **Never** defer accept until the last concurrent task
completes.

1. Canonical `report.md` with `STATUS: complete` + provider evidence,
   materialized by `lane-session` from the single task/prompt-bound final
   envelope; the Grok process never writes `.agents` directly. Trust only a
   report whose digest matches the current attempt's `runtime.json`; `lane-ctl`
   enforces this for status, verify, and accept.
2. Controller `check-owns-paths "$TASK_FILE" --run-scope` exit 0 +
   `owns-check.json`. The run-scoped union is required for a shared worktree;
   direct/night single-task calls stay per-task.
3. `lane-ctl verify` exit 0 + attempt-scoped `verification.json`.
4. No full-diff re-read on happy path.
5. Weak/empty/partial → one retry or recovery lane.
6. No daytime LLM review; the nightly loop reviews accepted and shipped work.
7. `lane-ctl accept` writes `acceptance.json`; without a receipt matching the
   immutable task hash and current attempt, the task is not done.

Acceptance for **all** tiers is report + the appropriate `check-owns-paths`
scope + verify + machine
`acceptance.json`.
Merge to main only when **all** tasks in the run are `done` (Phase 6) — but
individual tasks become `done` as they finish, not as a batch.

| Tier    | Trigger                            | Review |
|---------|-------------------------------------|--------|
| none    | micro path / risk low               | verify field + check-owns-paths only |
| nightly | everything else (medium/high/ship)  | typed Sol xhigh findings; bounded Grok repair; fresh re-review |

Normal daytime runs never invoke a reviewer. Historical or explicitly
configured `gate: pre-merge` runs stop for an operator decision rather than
silently spending a review call. The standard independent review/fix loop is
nightly.

Nightly/batch **reviews** may still group finished work later. That is not
join-wait on write accept — write accept stays per-task progressive.

Micro path still uses the durable controller around one detached Grok task.
Acceptance is the same machine receipt; no daytime reviewer.

Never mark task YAML done. A task is done only when `acceptance.json.accepted`
is true.

## Phase 5 — Stall recovery

```bash
lane-stall-check "$(pwd)" --minutes 5
```

The controller marks stalled from exact runtime evidence, retries the same lane
once, then records blocked with the evidence and next action.

## Phase 6 — Ship to main (PM only — always)

When **all** tasks in the run are accepted:

```bash
run-validate --run-dir "$(pwd)/.agents/runs/<slug>" --phase pre-merge
```

### Worktree path

```bash
# optional final suite in worktree
wt-merge-main "$(pwd)" <slug>
# freezes agent/<slug>, validates receipts, merges locally, runs finalize,
# pushes only after finalize succeeds, then removes the clean worktree
```

If the worktree auto-commit, finalize, or push fails, `wt-merge-main` exits
non-zero and preserves the branch/worktree for recovery. It never suppresses a
commit failure and never force-removes a failed run.

### Main-tree path (single low task)

PM commits on main yourself (Bash git in project):

```bash
git add -A && git status
git commit -m "feat(<slug>): <title>"
# Micro path: git commit -m "<type>(<area>): <title> [micro:<slug>]"
git push origin main # if remote exists — merge+push = one ship step
```

medium runs enter the typed nightly review queue (`night-shift`). Findings are
canonical `.agents/findings/*.json`; never leave a defect only in chat or a
free-form daily report. Codex reviews and re-reviews read-only; Grok is the only
normal repair writer. The deterministic runner retries Grok once, may use one
typed Sol high recovery after a second eligible availability failure, and may
merge or push only when `.agents/night-shift.yaml` explicitly opts in. A fresh
Sol xhigh re-review remains mandatory after either writer provider.

Treat `.agents/runs/<slug>/merge.json` as the machine receipt and `MERGE.md` as
its human view. `run-finalize` deterministically updates PROGRESS/BOARD/OPEN
from `run.yaml.finalize` and writes `finalize.json`.
Commit messages must be meaningful: conventional type(scope): what changed + why in the body when the reason is not obvious. Micro commits keep the [micro:<slug>] suffix.

**NEVER** ask the human to merge. **NEVER** leave a worktree as the “result”.

## Phase 7 — Context budget (PM)

After ~6 tasks or heavy transcripts: write handoff to PROGRESS; rebuild the
generated STATUS view → suggest fresh orchestrator session (`/resume-project`).
Writers remain run-scoped Grok sessions; supervision is one fresh
`run-supervisor` per run, never one model agent per provider.

## Recovery ladder

1. Same Grok lane + attempt-scoped retry after persisted backoff
2. Integrated Codex Sol high fallback when runtime marks the Grok failure eligible
3. Manual `codex-implementer` only after the typed controller blocks
4. Before first start, amend the task; after start, create a replacement task
5. `blocked` + STATUS note (then ask user only if business/irreversible)

## TODOs vs runs

Ideas → **agent-todos**. Active build → this skill. Promote todo → run when starting work.

## Hard rules (MUST)

1. No production Edit/Write — only `.agents/**`, `docs/plans/**`, PROGRESS/LESSONS.
2. No orchestrator-mcp / `task` CLI for queue.
3. Parallel = disjoint owns_paths only.
4. Merge to main = **you** when run green.
5. Workers never `git push` / merge main.
6. Provider slots default to 5 and are bounded at 10; verification defaults to 2 and has its own semaphore.
7. Done = immutable task hash + complete report + owns check + independent
   verification + accepted `acceptance.json`. Review is nightly.
8. **English only** for all run/todo/docs files; chat with human may be Russian (`LANGUAGE.md`).
9. **Progressive accept** when ≥2 writes: start detached, react to events,
   verify separately, write each acceptance receipt immediately.
10. **Never** use one Claude subagent per provider. One source-read-only
    `run-supervisor` may watch the durable deterministic controller for human
    visibility; it is not the lifecycle decision maker.
