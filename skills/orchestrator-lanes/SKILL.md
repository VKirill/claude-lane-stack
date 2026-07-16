---
name: orchestrator-lanes
description: Solo file-based multi-lane orchestration. AGY/Grok write, Codex review, PM auto-merges to main. No task MCP.
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

Default lane: `agy-coder` / `agy-frontend` (Flash). Fallback: `grok`.

Target latency: < 3 minutes word-to-commit.

## Phase 1 — Files

**Not** `docs/plans/` for coding execution.  
`docs/plans/` = strategy (COCOON, product). Promote strategy → run when implementing.

```bash
mkdir -p .agents/runs/<slug>/{tasks,artifacts}
# PLAN.md + tasks with owns_paths + never_touch + done_when
run-board "$(pwd)"   # optional refresh
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

## Phase 3 — Dispatch (≤3 concurrent slots, progressive)

**Max 3 concurrent write lanes** (slot cap). Total tasks in a run may be 2–10+ —
**pipeline** them: free a slot as soon as a task finishes, start the next ready
task. High-risk write = solo (1 slot). Parallel only with **disjoint owns_paths**.

### Anti-pattern (forbidden join-wait)

**Do not** spawn N implementers that each poll-until-done in one PM turn when
N>1. Claude Agent tool **joins all Agents in a turn** — you would only continue
after the **slowest** task, and could not accept earlier finishers.

```text
# BAD (join-wait): 3 Agents, each MODE=full / poll loop → PM blocked until last
Agent(agy) + Agent(grok) + Agent(agy)   # waits for max(t1,t2,t3)
```

### Progressive protocol (required when ≥2 write tasks)

| MODE | Who | What |
|------|-----|------|
| `start` | implementer | preflight + `lane-bg` + return **STATUS: started** (do **not** poll) |
| `finish` | implementer | after CLI done: write `report.md`, owns/verify notes, return complete/partial |
| `full` | implementer | start+poll+report in one Agent — **only** micro / single-task express |

PM loop (repeat until all tasks `done` or blocked):

```text
1) Fill free slots (running < 3, ready DAG tasks, disjoint owns):
   Agent MODE=start  → mark task status: running
2) Short Bash (safe):
   lane-poll --run-dir .agents/runs/<slug>
   # exit 0 + finish_ready>0 → some CLI finished without report yet
   # exit 2 → still running, nothing finish-ready
3) For EACH finish_ready task (independently — do not wait for others):
   Agent MODE=finish → accept (Phase 4) immediately → status: done
   free slot → may start next ready task in same turn or next poll cycle
4) If only running: sleep ~20–30s (short Bash) → lane-poll again
5) Periodically: lane-stall-check ; run-board
```

```text
You are grok-implementer.
MODE: start          # or finish | full
PROJECT_CWD: <worktree or repo>
TASK_FILE: .../tasks/001-….yaml
ARTIFACT_DIR: .../artifacts/001
RUN_DIR: .../runs/<slug>
Load karpathy-guidelines. Read TASK_FILE. Own only owns_paths. Never merge to main.
MODE=start → lane-bg only, return STATUS: started (no poll loop).
MODE=finish → CLI must already be done; write report.md; return STATUS.
Heartbeat: lane-heartbeat --repo PROJECT_CWD --run <slug> --task 001 --status running|done
```

| `lane` | Agent |
|--------|--------|
| agy-coder | agy-implementer → lane-coder |
| agy-frontend | agy-implementer → lane-frontend |
| grok | grok-implementer |
| codex-review-medium | codex-reviewer (sol medium) |
| codex-review | codex-reviewer |

### Background rule (prevents 2-minute kills)

```bash
# MODE=start — implementer (returns immediately after detach):
lane-bg --dir "$ARTIFACT_DIR" --label grok -- lane-exec ... -- grok ...

# PM progressive poll (short Bash, multi-task):
lane-poll --run-dir "$RUN_DIR"          # finish_ready tasks → MODE=finish + accept now
lane-wait --dir "$ARTIFACT_DIR" --once  # single-dir; exit 2 = running, 0 = done
```

Docs: `~/.agents/docs/LANE-EXEC.md`. Bins: `lane-bg`, `lane-wait`, **`lane-poll`**, `lane-exec`.

After each start: task `status: running`, `STATUS.md`, `lane-heartbeat`, `run-board`.
After each accept: task `status: done`, free slot, unlock `depends_on` dependents.

## Phase 4 — Accept (per-task, as soon as ready)

**Progressive accept is mandatory for multi-task runs.** When task A finishes
while B and C still run: accept A **now**, mark done, free its slot, start the
next ready task if any. **Never** defer accept until the last concurrent task
completes.

1. `report.md` STATUS complete + real VERIFIED / done_when evidence.  
2. `check-owns-paths "$TASK_FILE"` exit 0.  
3. No full-diff re-read on happy path.  
4. Weak/empty/partial → other write lane or fix prompt.  
5. Gate (opt-in): pre-merge review is off by default; see the gate note below.

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

Micro path: single task `MODE=full` OK; acceptance is report + `check-owns-paths`
only (no reviewer); verify per the task `verify` field (none|smoke|tests).

Mark `status: done` only if 1–4 (and 5 if `gate: pre-merge` applies for this run).

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
git push origin main   # if remote exists
```

### Main-tree path (single low task)

PM commits on main yourself (Bash git in project):

```bash
git add -A && git status
git commit -m "feat(<slug>): <title>"
# Micro path: git commit -m "<type>(<area>): <title> [micro:<slug>]"
git push origin main   # if remote exists — merge+push = one ship step
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
2. Other write lane (agy ↔ grok)  
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
6. Max 3 **concurrent** write slots; pipeline more tasks via progressive accept.  
7. Done = report + owns check + done_when (+ codex if required).  
8. **English only** for all run/todo/docs files; chat with human may be Russian (`LANGUAGE.md`).  
9. **Progressive accept** when ≥2 writes: MODE=start / lane-poll / MODE=finish per task — never join-wait the slowest before accepting finished ones.
