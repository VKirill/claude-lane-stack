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

## Phase 3 — Dispatch (≤3 parallel)

One message, ≤3 Agents, **disjoint owns_paths**. High-risk solo.

```text
You are grok-implementer.
PROJECT_CWD: <worktree or repo>
TASK_FILE: .../tasks/001-….yaml
ARTIFACT_DIR: .../artifacts/001
Load karpathy-guidelines. Read TASK_FILE. Own only owns_paths. Never merge to main.
MUST: start the CLI via lane-bg (never long foreground Bash — host kills ~2m).
Poll with lane-wait --dir ARTIFACT_DIR --once until done.
Heartbeat: lane-heartbeat --repo PROJECT_CWD --run <slug> --task 001 --status running
Write report.md to ARTIFACT_DIR.
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
# implementer starts (returns immediately):
lane-bg --dir "$ARTIFACT_DIR" --label grok -- lane-exec ... -- grok ...

# implementer or PM checks (short Bash, safe):
lane-wait --dir "$ARTIFACT_DIR" --once   # exit 2 = running, 0 = done
```

Docs: `~/.agents/docs/LANE-EXEC.md`. Bins: `lane-bg`, `lane-wait`, `lane-exec`.

After dispatch: update task `status: running`, `STATUS.md`, `lane-heartbeat`, `run-board`.

## Phase 4 — Accept (Delegated Trust + ownership)

1. `report.md` STATUS complete + real VERIFIED / done_when evidence.  
2. `check-owns-paths "$TASK_FILE"` exit 0.  
3. No full-diff re-read on happy path.  
4. Weak/empty/partial → other write lane or fix prompt.  
5. Review tier:

| Tier   | Trigger                            | Reviewer |
|--------|------------------------------------|----------|
| none   | micro path / risk low              | verify field + check-owns-paths only |
| medium | risk medium                        | codex-reviewer (sol, medium) — nightly batch, off critical path |
| strong | risk high / high_risk_paths / ship | codex-reviewer (sol high; xhigh critical paths) — synchronous, pre-merge |

Medium-tier acceptance is report + `check-owns-paths` + verify, then merge;
review is deferred to the nightly `night-review` batch, and findings become
morning fix tasks. Strong tier stays synchronous before merge.

Medium review is mechanical only (bugs, style, dependencies, obvious logic);
auth/pay/schema/security always uses the strong tier. Medium FAIL -> writer
fixes or PM escalates to the strong tier; never ignore a FAIL.

Batch reviews: collect finished lanes, review in one dedicated pass — do not approve streaming output.

Micro path: acceptance is report + `check-owns-paths` only (no reviewer);
verify per the task `verify` field (none|smoke|tests).

Mark `status: done` only if 1–2 (and 5 if required).

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
6. Max 3 parallel write lanes.  
7. Done = report + owns check + done_when (+ codex if required).  
8. **English only** for all run/todo/docs files; chat with human may be Russian (`LANGUAGE.md`).
