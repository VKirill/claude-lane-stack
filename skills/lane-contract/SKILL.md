---
name: lane-contract
description: File-based task contracts under .agents/runs/ with owns_paths and solo merge rules.
---

# Lane contract (files only)

Canonical: `/home/ubuntu/.agents/docs/FILE-CONTRACT.md`.  
Solo: `/home/ubuntu/.agents/docs/SOLO-ORCHESTRATION.md`.

## Orchestrator must

1. Write contracts before dispatch; set **`owns_paths`** + **`never_touch`** + **`done_when`**.  
2. Paste code excerpts into `interfaces` / `objective`.  
3. Pass `PROJECT_CWD`, `TASK_FILE`, and `RUN_DIR` (absolute) to `lane-supervisor`.
4. Ensure parallel tasks have **disjoint** owns_paths.  
5. After **each** lane finishes: `check-owns-paths`; accept report evidence **immediately**
   (progressive — do not wait for other concurrent tasks).  
6. When run complete: **merge to main** (`wt-merge-main` or commit) — human never merges.  
7. No task CLI / orchestrator MCP for queue.  
8. Start and observe work through typed `lane-ctl` actions. The supervisor is
   source-read-only; the detached Grok process is the writer.
9. Keep provider slots (default 5, range 1–10) separate from verification slots
   (default 2, range 1–10).

## Lane must

1. `Read` TASK_FILE first.  
2. Work only in `PROJECT_CWD`.  
3. Edit **only** `owns_paths` (or `files`). Honor `never_touch`.  
4. Heartbeat: `lane-heartbeat --repo … --run … --task … --status running`.  
5. Write `ARTIFACT_DIR/report.md` and run focused checks — **report body in English**. The PM independently runs task `verification` commands via `lane-ctl verify`.
6. **Never** `git checkout main`, merge to main, or `git push` unless task says otherwise (default: never).  
7. On build errors outside owns_paths: do not fix; note in report.  
8. All durable files English (see LANGUAGE.md).

## Minimal fields

`id`, `title`, `risk`, `lane`, `status`, `project_cwd`, `owns_paths` (or `files`), `objective`, `verify`, `verification`/`done_when`, `acceptance`.

## `verify` levels

| Level | Meaning |
|-------|---------|
| none | No tests/build evidence needed (visual or trivial change) |
| smoke | Build passes / page renders / command runs once |
| tests | Real test run evidence required in report |

PM chooses `verify` at scoring time; `done_when` must match it.
