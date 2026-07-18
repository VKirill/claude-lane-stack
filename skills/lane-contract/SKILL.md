---
name: lane-contract
description: File-based task contracts under .agents/runs/ with owns_paths and solo merge rules.
---

# Lane contract (files only)

Canonical: `/home/ubuntu/.agents/docs/FILE-CONTRACT.md`.
Solo: `/home/ubuntu/.agents/docs/SOLO-ORCHESTRATION.md`.

## Orchestrator must

1. Create new runs with `run-init`, write strict schema-v2 tasks, then run
   `run-validate --phase pre-dispatch` before dispatch.
2. Set **`owns_paths`** + **`never_touch`** + behavioral `acceptance`.
3. Paste code excerpts into `interfaces` and declare `read_first`, `invariants`,
   `out_of_scope`, and `expected_outputs`.
4. Pass absolute `PROJECT_CWD` and `RUN_DIR` to one `run-supervisor` for the
   whole run. Use `lane-supervisor` only for an explicit one-lane diagnostic.
5. Ensure parallel tasks have **disjoint** owns_paths.
6. Start the durable `run-controller`. It must run `check-owns-paths`, verify,
   and accept evidence **immediately** after each lane finishes (progressive —
   do not wait for other concurrent tasks).
7. Treat `tasks/*.yaml` as immutable after first start. Runtime status belongs
   to `artifacts/<id>/state.json`; completion exists only in `acceptance.json`.
8. Before merge run `run-validate --phase pre-merge`; then **merge to main**
   (`wt-merge-main` or commit) — human never merges.
9. No task CLI / orchestrator MCP for queue.
10. Normal daytime work flows through `run-controller` and its typed `lane-ctl`
    actions. The run supervisor is source-read-only; the detached Grok process
    is the writer. There is no daytime LLM review.
11. Keep provider slots (default 5, range 1–10) separate from verification slots
    (default 2, range 1–10).
12. Run automated writers/reviewers with the lane automation marker. Imported
    Claude hooks are disabled for Grok and the shared native session-ledger
    exits without writing; skills, rules, and non-ledger safety hooks remain.
13. Treat `Cancelled`, `Error`, any unknown provider terminal reason, and exit
    zero without a root `report.md` whose `STATUS` is `complete` as retryable
    failure, never as ready for verification.

## Lane must

1. `Read` TASK_FILE first.
2. Work only in `PROJECT_CWD`.
3. Edit **only** `owns_paths` (or `files`). Honor `never_touch`.
4. Heartbeat: `lane-heartbeat --repo … --run … --task … --status running`.
   It never edits task YAML or appends to STATUS.md.
5. Write the canonical `ARTIFACT_DIR/report.md` and run focused checks —
   **report body in English**. The PM independently runs structured task
   `verification` commands via `lane-ctl verify`.
6. **Never** `git checkout main`, merge to main, or `git push` unless task says otherwise (default: never).
7. On build errors outside owns_paths: do not fix; note in report.
8. All durable files English (see LANGUAGE.md).

## Required schema-v2 task fields

`schema_version`, `id`, `title`, `risk`, `lane`, `project_cwd`, `read_first`,
`interfaces`, `invariants`, `out_of_scope`, `expected_outputs`, `owns_paths`,
`never_touch`, `depends_on`, `objective`, `acceptance`, `verify`, and structured
`verification` entries (`command`, absolute `cwd`, bounded `timeout_sec`).

Legacy task fields remain readable for existing runs. New runs must not include
mutable `status`, `done_when`, or free-form verification strings.

## `verify` levels

| Level | Meaning |
|-------|---------|
| none | No tests/build evidence needed (visual or trivial change) |
| smoke | Build passes / page renders / command runs once |
| tests | Real test run evidence required in report |

PM chooses `verify` at scoring time; the structured `verification` commands
must provide evidence appropriate to that level.
