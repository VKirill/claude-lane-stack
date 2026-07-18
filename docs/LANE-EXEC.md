# Event-driven Grok lanes

## Why this exists

Claude Code foreground Bash can be terminated after roughly two minutes. A
model subagent that stays alive to poll a provider also consumes an orchestration
slot and makes a parallel wave wait for its slowest member.

The lane stack therefore separates four responsibilities:

| Component | Responsibility |
|-----------|----------------|
| `lane-supervisor` | Source-read-only Claude control agent; issues one typed action and returns |
| `lane-ctl` | Validates paths, builds the prompt, registers immutable control state, exposes status/retry/cancel/verify |
| `lane-bg` + `lane-exec` | User-systemd process lifetime, activity timeouts, exact exit code, lifecycle events |
| `lane-session` | Run-scoped warm Grok sessions and bounded provider concurrency |

Grok is the code writer. The Claude supervisor has no `Write`, `Edit`, or
unrestricted `Bash` capability.

## Start a lane

```bash
export PATH="$HOME/.agents/bin:$PATH"

lane-ctl start \
  --run-dir "$RUN_DIR" \
  --task-file "$TASK_FILE" \
  --project-cwd "$PROJECT_CWD"
```

`start` returns after the detached job is registered. It creates the task
artifact directory, builds `prompt.md` from the canonical Grok writer contract
plus the raw task YAML, writes `control.json`, and launches this low-level chain:

```text
lane-bg → lane-exec → lane-session → grok
```

No model is kept alive merely to hold or poll the process. On Linux with a user
systemd manager, `lane-bg` launches a transient service so host tool cleanup
cannot reap the provider after `start` returns. `LANE_BG_BACKEND=nohup` is kept
as a compatibility/test fallback.

## Observe and control

Use short, typed calls:

```bash
lane-ctl status --run-dir "$RUN_DIR" --task-id "$TASK_ID" --json
lane-ctl events --run-dir "$RUN_DIR" --task-id "$TASK_ID" --json
lane-ctl tail --run-dir "$RUN_DIR" --task-id "$TASK_ID" --lines 80
lane-ctl retry --run-dir "$RUN_DIR" --task-id "$TASK_ID"
lane-ctl cancel --run-dir "$RUN_DIR" --task-id "$TASK_ID"
```

Normal orchestration reacts to compact `events.jsonl` records. `tail` is for an
error, stall, or explicit diagnostic request, not a continuous token-expensive
log loop. A retry reuses the recorded argv array from `control.json`; it never
reconstructs or shell-evaluates a free-form command. The argv schema and prompt
digest are revalidated, and the control plane permits at most two attempts.

Status deliberately distinguishes `awaiting_verification`, `verified`, and
`verification_failed`. Provider exit 0 is never reported as accepted work.

## Verify independently

After provider exit 0:

```bash
lane-ctl verify \
  --run-dir "$RUN_DIR" \
  --task-file "$TASK_FILE" \
  --project-cwd "$PROJECT_CWD"
```

At `start`, the control plane snapshots the exact `verification` commands from
the trusted task YAML. `verify` can run only after the matching provider attempt
exits 0, uses that immutable snapshot, and applies a per-command timeout (30
minutes by default, configurable with `--command-timeout`). It has a separate
file-lock semaphore: default 2 concurrent checks, configurable from 1–10.
Results are bound to the attempt in `verification.json` and `verified.txt`.
Provider completion alone is never task acceptance.

## Concurrency

- Provider pool: default 5, configurable 1–10.
- Verification pool: default 2, configurable 1–10.
- One warm session slot serves one task at a time.
- Parallel write tasks require disjoint `owns_paths`.
- High-risk write work remains serial even when capacity is available.
- Accept a verified task immediately and refill the next ready DAG task; never
  join-wait for the slowest sibling.

`lane-session` rotates a warm slot after seven successful tasks by default,
after a provider failure, or when cwd/model changes. Sessions are scoped to the
exact run directory, role, worktree, and model; review never reuses them.
If `XDG_RUNTIME_DIR` is unavailable or read-only, session locks fall back to a
private per-user directory under `/tmp`.

## Artifacts and events

```text
.agents/runs/<slug>/
  events.jsonl
  sessions.json
  artifacts/<task-id>/
    control.json
    prompt.md
    lane-bg.pid
    lane-bg.exit
    lane-bg.supervisor.log
    lane-exec.log
    provider.out
    heartbeat.json
    verification.json
    verified.txt
    report.md
```

`lane-exec` appends atomic single-write JSONL records for start, timeout,
interruption, and exit. The final exit record and log line are written before
the log file is closed, so a successful child exits 0 instead of being masked by
supervisor cleanup.

Registered control artifacts and events distinguish live work from historical
task YAML. A run with `MERGE.md` is complete and must not be reported as stalled.

## Timeouts

`lane-exec` has independent limits:

| Level | Typical Grok value | Behavior |
|-------|--------------------|----------|
| idle | 900s | terminate only after no stdout, CPU, or external heartbeat activity |
| max | 7200s | absolute wall-clock ceiling |
| grace | 80% of max | log a warning; do not terminate |

Exit 124 means idle or maximum timeout. Exit codes from normal provider failure
are propagated exactly. Read events and the bounded log tail before the one
allowed retry.

## Compatibility tools

`lane-wait`, `lane-poll`, `lane-mode-check`, and legacy `MODE` prompts remain
for older runs. New orchestration uses `lane-ctl` and `lane-supervisor`.

## Night review

`night-review <repo-root>` remains a detached, read-only batch review and may be
started through `lane-bg`. It is not part of the writer session or verification
pool.
