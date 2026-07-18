# Event-driven Grok lanes

## Why this exists

Claude Code foreground Bash can be terminated after roughly two minutes. A
model subagent that stays alive to poll a provider also consumes an orchestration
slot and makes a parallel wave wait for its slowest member.

The lane stack therefore separates four responsibilities:

| Component | Responsibility |
|-----------|----------------|
| `lane-supervisor` | Source-read-only Claude control agent; issues one typed action and returns |
| `lane-ctl` | Validates v2 contracts, builds the prompt, registers immutable state, exposes status/retry/cancel/verify/accept |
| `lane-bg` + `lane-exec` | User-systemd process lifetime, activity timeouts, exact exit code, lifecycle events |
| `lane-session` | Run-scoped warm Grok sessions and bounded provider concurrency |

Grok is the code writer. The Claude supervisor has no `Write`, `Edit`, or
unrestricted `Bash` capability.

## Start a lane

```bash
export PATH="$HOME/.agents/bin:$PATH"

run-validate --run-dir "$RUN_DIR" --phase pre-dispatch

lane-ctl start \
  --run-dir "$RUN_DIR" \
  --task-file "$TASK_FILE" \
  --project-cwd "$PROJECT_CWD"
```

`start` returns after the detached job is registered. It hashes the immutable
task YAML, creates `state.json` plus `attempts/01/`, builds the attempt prompt
from the canonical Grok writer contract plus the raw task YAML, writes the
attempt control receipt, and launches this low-level chain:

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
log loop. A retry reuses the recorded argv array from the current attempt's
`control.json`; it never
reconstructs or shell-evaluates a free-form command. The argv schema and prompt
digest are revalidated, the task hash must still match, and the control plane
permits at most two attempts. Retry writes `attempts/02` without overwriting 01.

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

At `start`, the control plane snapshots exact structured `verification` entries
(`command`, absolute `cwd`, bounded `timeout_sec`) from the trusted task YAML.
`verify` rejects empty smoke/tests suites, can run only after the matching
provider attempt exits 0, and uses that immutable snapshot. It has a separate
file-lock semaphore: default 2 concurrent checks, configurable from 1–10.
Results are bound to the attempt in `attempts/NN/verification.json`.
Provider completion alone is never task acceptance.

## Accept independently

After verification, the PM produces the ownership receipt and invokes the
technical gate:

```bash
check-owns-paths "$TASK_FILE"
lane-ctl accept \
  --run-dir "$RUN_DIR" \
  --task-file "$TASK_FILE" \
  --project-cwd "$PROJECT_CWD"
```

`accept` checks the unchanged task hash, provider exit 0, canonical report
status, `owns-check.json`, current-attempt verification, and required review.
Only then does it write root `acceptance.json` and set state to accepted.

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
    state.json
    heartbeat.json
    report.md
    owns-check.json
    acceptance.json
    review.json
    attempts/01/
      control.json
      prompt.md
      lane-bg.pid
      lane-bg.exit
      lane-bg.supervisor.log
      lane-exec.log
      provider.out
      runtime.json
      verification.json
    attempts/02/
      ...
```

`lane-exec` appends atomic single-write JSONL records for start, timeout,
interruption, and exit. The final exit record and log line are written before
the log file is closed, so a successful child exits 0 instead of being masked by
supervisor cleanup.

Registered state and events distinguish live work from immutable task YAML.
`STATUS.md` is rebuilt from state/acceptance by `run-board`; heartbeat never
appends to it. A run with merge.json/MERGE.md is terminal and is not stalled.

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

`night-review <repo-root>` is the compatibility entry point for a typed,
read-only Codex batch. It reviews bounded chunks with the installed
`night-review` profile (`gpt-5.6-sol`, `xhigh`, read-only, approval `never`),
passes an API-compatible projection of the output schema, then validates the
result against the full local JSON Schema before persisting canonical findings
or advancing the checkpoint.

`night-shift <repo-root>` adds the bounded repair phase. Generated v2 tasks run
through the ordinary Grok provider pool in a dedicated worktree; deterministic
receipts, not a Claude polling subagent, drive retry/verify/re-review/accept.
Grok receives no-subagent and workspace-sandbox guardrails. Merge and push are
off unless the target repository explicitly opts in through
`.agents/night-shift.yaml`.

Automated Grok and Codex subprocesses carry a lane automation marker consumed
by the shared session-ledger hook, so neither writer nor read-only reviewer can
create `PROGRESS.md` or session-log files in the worktree. Grok additionally
disables imported Claude compatibility hooks while preserving shared skills,
rules, and native non-ledger safety hooks.

The fresh `review.json` is an identity-bound schema-v2 receipt, not only a model
verdict. It records the task hash, current attempt, full base commit and exact
reviewed diff/tree digests. `lane-ctl accept` recomputes the same state and
rejects stale receipts or any post-review tracked/untracked mutation.
