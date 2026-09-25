---
name: codex-lane
description: Operate Claude Lane Stack schema-v2 runs from Codex. Use for lane status, start, resume, review, verification, evidence, or acceptance.
---

# Codex Lane

Use the installed typed wrappers under `~/.agents/bin`. Keep the run directory,
task file, and project root supplied by the user or existing run state. Do not
invent a run, task id, path, model, or receipt.

## Dependencies

Check the wrappers before acting when the installation is uncertain:

```bash
command -v run-controller lane-ctl night-review
run-controller --help
lane-ctl --help
```

The wrappers may be invoked by absolute path (`~/.agents/bin/...`) when `PATH`
does not include `~/.agents/bin`. Their lifecycle state lives under the run's
`.agents/runs/<slug>/` directory.

## Run and resume

For an existing schema-v2 run, validate and start the durable controller. Keep
the run's configured writer by default; add `--provider codex` only when Codex
is the explicitly selected writer:

```bash
run-validate --run-dir "$RUN_DIR" --phase pre-dispatch
run-controller start --run-dir "$RUN_DIR" --project-cwd "$PROJECT_CWD"
run-controller watch --run-dir "$RUN_DIR" --timeout 240 --json
```

`run-controller start` is idempotent and resumes persisted controller state.
Use a fresh bounded `watch` call after an interrupted session. Read the
controller receipt with:

```bash
run-controller status --run-dir "$RUN_DIR" --json
```

Preserve the run's selected native profile, provider, model, reasoning effort,
and service tier unless the operator explicitly asks for a change. Do not
silently route a run to Codex or override those values.

For one typed lane instead of the DAG controller (use `--provider codex` only
when explicitly selected):

```bash
lane-ctl start --run-dir "$RUN_DIR" --task-file "$TASK_FILE" \
  --project-cwd "$PROJECT_CWD"
```

## Status and evidence

Read compact state first, then inspect the bounded journal or a specific log:

```bash
lane-ctl status --run-dir "$RUN_DIR" --task-id "$TASK_ID" --json
lane-ctl events --run-dir "$RUN_DIR" --task-id "$TASK_ID" --json
lane-ctl tail --run-dir "$RUN_DIR" --task-id "$TASK_ID" --source report --lines 80
```

Require a trusted complete `report.md`, matching `report_sha256`, provider
exit 0, and the current attempt before treating a writer as ready for L1.
The writer's report is evidence; it is not acceptance.

## Review, verify, accept

`lane-ctl` has no `review` subcommand. Run the installed read-only review
entrypoint when a review is requested:

```bash
night-review "$PROJECT_CWD" --project-cwd "$PROJECT_CWD" --run-slug "$RUN_SLUG"
```

Run the task's immutable verification and ownership checks:

```bash
lane-ctl verify --run-dir "$RUN_DIR" --task-file "$TASK_FILE" \
  --project-cwd "$PROJECT_CWD"
check-owns-paths "$TASK_FILE" --run-scope
```

When the task/run requires review, produce the task-specific receipt before
acceptance. Use the immutable pre-task commit recorded by the run as
`BASE_REF`; if it is missing, report the missing baseline. A repository-wide
night review does not substitute for this receipt:

```bash
night-review-engine review-task --repo "$PROJECT_CWD" --run-dir "$RUN_DIR" \
  --task-file "$TASK_FILE" --base-ref "$BASE_REF" \
  --output "$RUN_DIR/artifacts/$TASK_ID/review.json"
```

Finally apply the typed acceptance gate:

```bash
lane-ctl accept --run-dir "$RUN_DIR" --task-file "$TASK_FILE" \
  --project-cwd "$PROJECT_CWD"
```

Acceptance must produce `artifacts/<task-id>/acceptance.json` and a current
accepted state. If any receipt is stale or missing, stop and report the exact
gate failure instead of editing control-plane artifacts.

Do not run provider commands directly, rewrite `report.md`, bypass
`lane-ctl`, or claim browser or user-specific verification from a fixture.
This plugin does not replace native Codex compaction or add an MCP server.
