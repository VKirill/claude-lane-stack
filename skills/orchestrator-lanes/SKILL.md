---
name: orchestrator-lanes
description: Solo file-based multi-lane orchestration. Grok write, Codex review, PM auto-merges to main. No task MCP.
---

# Orchestrator lanes — solo operator

Load: **karpathy-guidelines**, **lane-contract**, **project-memory**, **resume-project**.

Docs: `FILE-CONTRACT.md`, `ROUTING.md`, `SOLO-ORCHESTRATION.md` under `/home/ubuntu/.agents/docs/`.

You are the **only** person who merges to `main`. Human never merges.

## Phase 0 — Score (announce once)

+2 multi-problem · +2 UI/state/auth/pay · +2 backend/API · +2 multi-surface · +2 needs verify · +3 prod/billing/security 

| Score | Path |
|------:|------|
| 0–2 | Micro: 1 task, no plan/board/heartbeat/review, **commit main** |
| 3–6 | Express: 1 task, dispatch, verify, **commit/merge main** |
| 7–8 | Brief: 2–4 tasks, PLAN.md, worktree if ≥2 writes |
| 9–10 | Full: SPEC + DAG + worktree |
| 11+ | Split feature; ask user |

### Micro path (score 0–2)

Trigger: score 0–2 **and** risk low **and** ≤2 files **and** no
`high_risk_paths` (auth/pay/schema/migrations/security).

Skips: PLAN.md, worktree, run-board, STATUS.md, lane-heartbeat, reviewer.

Keeps: minimal task YAML (`id`, `title`, `risk`, `lane`, `project_cwd`,
`owns_paths`, `objective`, `verify`), `lane-bg` for the CLI call,
`check-owns-paths`, PM commits to main.

Micro commit format: `<type>(<area>): <title> [micro:<slug>]`.

Default lane: `grok` (only write programmer). Fallback: re-dispatch grok once, then `codex-implementer`.

Target latency: < 3 minutes word-to-commit.

## Phase 1 — Files

**Not** `docs/plans/` for coding execution. 
`docs/plans/` = strategy (COCOON, product). Promote strategy → run when implementing.

```bash
mkdir -p .agents/runs/<slug>/{tasks,artifacts}
# PLAN.md + tasks with owns_paths + never_touch + done_when
run-board "$(pwd)" # optional refresh
```

Every write task **must** set `owns_paths` (or `files`). Parallel tasks: **disjoint** owns_paths.

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

## Phase 3 — Dispatch (event-driven, bounded)

Provider concurrency defaults to **5** and is configurable from **1–10**.
Verification has a separate pool, default **2**, also bounded at **10**. High
risk work remains solo. Parallel writers require **disjoint owns_paths**.

Claude subagents do not own provider lifetime and never poll in a loop. The
source-read-only `lane-supervisor` issues one typed `lane-ctl` action and
returns. `lane-bg`, `lane-exec`, and `lane-session` own the detached process.

```text
1) Fill free provider slots with ready, disjoint tasks:
   Agent lane-supervisor ACTION=start → returns started immediately
2) React to events/status on completion, failure, stall, or operator request.
3) Provider exit 0 → ACTION=verify (separate semaphore).
4) Accept each verified task immediately → free provider slot → refill DAG.
5) One failed/stalled lane may retry once; a second failure becomes blocked.
```

Required dispatch fields are `ACTION`, `RUN_DIR`, `TASK_FILE`, `PROJECT_CWD`,
and `TASK_ID` when it cannot be derived. `lane-ctl start` builds the Grok prompt
from `agents/grok/writer.md` plus the raw task YAML, registers immutable argv in
`control.json`, and appends lifecycle records to run-level `events.jsonl`.

```text
You are lane-supervisor.
ACTION: start | status | events | tail | retry | cancel | verify
RUN_DIR: /absolute/repo/.agents/runs/<slug>
TASK_FILE: /absolute/.../tasks/001-title.yaml
PROJECT_CWD: /absolute/worktree
TASK_ID: 001
Run one direct lane-ctl action. Never edit source or poll in a loop.
```

| `lane` | Agent |
|--------|--------|
| grok | lane-supervisor (read-only control); Grok process is the writer |
| codex-implementer | fallback write if Grok blocked |
| codex-review-medium | codex-reviewer (sol medium) |
| codex-review | codex-reviewer |

### Control-plane commands

```bash
lane-ctl start --run-dir "$RUN_DIR" --task-file "$TASK_FILE" --project-cwd "$PROJECT_CWD"
lane-ctl status --run-dir "$RUN_DIR" --task-id "$TASK_ID" --json
lane-ctl events --run-dir "$RUN_DIR" --task-id "$TASK_ID" --json
lane-ctl verify --run-dir "$RUN_DIR" --task-file "$TASK_FILE" --project-cwd "$PROJECT_CWD"
```

Docs: `~/.agents/docs/LANE-EXEC.md`. Primary control bin: `lane-ctl`; low-level
compatibility bins remain `lane-bg`, `lane-wait`, `lane-poll`, `lane-mode-check`,
`lane-exec`, and `lane-session`.

After each start: task `status: running`, `STATUS.md`, and `run-board`.
After each accept: task `status: done`, free slot, unlock `depends_on` dependents.

**Detached heartbeat:** `lane-exec --heartbeat ARTIFACT/heartbeat.json` writes
only on real activity (stdout/CPU). Run-level events distinguish registered live
work from old task YAML and completed historical runs.

## Phase 4 — Accept (per-task, as soon as ready)

**Progressive accept is mandatory for multi-task runs.** When task A verifies
while B and C still run: accept A **now**, mark done, free its slot, start the
next ready task if any. **Never** defer accept until the last concurrent task
completes.

1. `report.md` STATUS complete + provider evidence.
2. `check-owns-paths "$TASK_FILE"` exit 0. 
3. `lane-ctl verify` exit 0 + `verified.txt` / `verification.json`.
4. No full-diff re-read on happy path.
5. Weak/empty/partial → one retry or recovery lane.
6. Gate (opt-in): pre-merge review is off by default; see the gate note below.

Acceptance for **all** tiers is report + `check-owns-paths` + verify.
Merge to main only when **all** tasks in the run are `done` (Phase 6) — but
individual tasks become `done` as they finish, not as a batch.

| Tier    | Trigger                            | Review |
|---------|-------------------------------------|--------|
| none    | micro path / risk low               | verify field + check-owns-paths only |
| nightly | everything else (medium/high/ship)  | night-review batch (sol): verdicts + Morning fix plan; FAIL -> morning fix task, never ignored |

Pre-merge gate is OFF by default (solo, no-user products). When a project
serves real users or money, re-enable per project: add `gate: pre-merge` to
PROGRESS.md Pointers (or set `gate: pre-merge` in a task YAML) — then
codex-reviewer (sol high; xhigh for auth/pay/schema/migrations/security)
must pass BEFORE merge for high-risk work in that project.

Nightly/batch **reviews** may still group finished work later. That is not
join-wait on write accept — write accept stays per-task progressive.

Micro path still uses one detached Grok task through `lane-ctl start`. Acceptance
is report + owns check + independent verification; no reviewer for low risk.

Mark `status: done` only if 1–5 pass and item 6 passes when the configured
pre-merge gate applies.

## Phase 5 — Stall recovery

```bash
lane-stall-check "$(pwd)" --minutes 5
```

Stalled → mark task `stalled` → re-dispatch same lane once → else other write lane → else blocked in STATUS.

## Phase 6 — Ship to main (PM only — always)

When **all** tasks in the run are `done` (and required reviews passed):

### Worktree path

```bash
# optional final suite in worktree
wt-merge-main "$(pwd)" <slug>
# merges agent/<slug> → main, removes worktree, writes MERGE.md
run-board "$(pwd)"
git push origin main # if remote exists
```

### Main-tree path (single low task)

PM commits on main yourself (Bash git in project):

```bash
git add -A && git status
git commit -m "feat(<slug>): <title>"
# Micro path: git commit -m "<type>(<area>): <title> [micro:<slug>]"
git push origin main # if remote exists — merge+push = one ship step
```

medium runs enter the nightly review queue (night-review)

Write `.agents/runs/<slug>/MERGE.md` with branch/commit/time. 
Update `PROGRESS.md` Now/Next + project-memory. 
Commit messages must be meaningful: conventional type(scope): what changed + why in the body when the reason is not obvious. Micro commits keep the [micro:<slug>] suffix.

**NEVER** ask the human to merge. **NEVER** leave a worktree as the “result”.

## Phase 7 — Context budget (PM)

After ~6 tasks or heavy transcripts: write handoff to PROGRESS + STATUS → suggest fresh orchestrator session (`/resume-project`). 
Workers: **always** fresh Agent spawn per task (never continue a fat worker chat).

## Recovery ladder

1. Same lane + note in YAML 
2. Fallback write lane: `codex-implementer` 
3. Amend task file + re-dispatch 
4. `blocked` + STATUS note (then ask user only if business/irreversible)

## TODOs vs runs

Ideas → **agent-todos**. Active build → this skill. Promote todo → run when starting work.

## Hard rules (MUST)

1. No production Edit/Write — only `.agents/**`, `docs/plans/**`, PROGRESS/LESSONS. 
2. No orchestrator-mcp / `task` CLI for queue. 
3. Parallel = disjoint owns_paths only. 
4. Merge to main = **you** when run green. 
5. Workers never `git push` / merge main. 
6. Provider slots default to 5 and are bounded at 10; verification defaults to 2 and has its own semaphore.
7. Done = report + owns check + done_when (+ codex if required). 
8. **English only** for all run/todo/docs files; chat with human may be Russian (`LANGUAGE.md`). 
9. **Progressive accept** when ≥2 writes: start detached, react to events, verify separately, accept per task.
10. **Never** use a live Claude subagent or polling loop as the provider process supervisor.
