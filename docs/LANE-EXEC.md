# Durable daytime writer runs

## Why this exists

Claude Code foreground Bash can be terminated after roughly two minutes. A
model subagent per provider also consumes orchestration slots and can disappear
before the provider produces acceptance evidence.

The lane stack therefore separates six responsibilities:

| Component | Responsibility |
|-----------|----------------|
| `run-supervisor` | One visible source-read-only Claude agent per run; bounded watch only |
| `run-controller` | Durable deterministic DAG, retry, ownership, verification, and acceptance loop |
| `lane-supervisor` | Manual one-action lane diagnostic/recovery agent |
| `lane-ctl` | Validates v2 contracts, builds the prompt, registers immutable state, exposes status/retry/cancel/verify/accept |
| `lane-bg` + `lane-exec` | User-systemd process lifetime, activity timeouts, exact exit code, lifecycle events |
| `lane-session` | Warm AGY/Grok plus one-shot Codex fallback, provider isolation, validated report transport, and bounded concurrency |

Grok 4.5 is the default code writer and AGY 3.6 remains selectable. A classified second availability failure may
use one Codex Sol high writer attempt; that is recovery, not daytime review.
Both Claude supervisor profiles have no `Write`,
`Edit`, or unrestricted `Bash` capability. There is no daytime LLM review.

## Start and visibly watch a run

```bash
export PATH="$HOME/.agents/bin:$PATH"

run-validate --run-dir "$RUN_DIR" --phase pre-dispatch
run-controller start \
  --run-dir "$RUN_DIR" \
  --project-cwd "$PROJECT_CWD" \
  --provider grok # or: agy
run-controller watch --run-dir "$RUN_DIR" --timeout 240
run-controller status --run-dir "$RUN_DIR" --json
```

`run-controller start` returns after the run-level worker is registered under
`RUN_DIR/controller/`. It is idempotent and survives Claude or subagent exit.
The worker validates the run contract at startup and again before every new
dispatch wave, so a task file changed between dependency waves fails closed.
The controller releases ready DAG tasks through `lane-ctl`, which hashes the
immutable task YAML, creates `state.json` plus `attempts/01/`, and launches:

```text
lane-bg → lane-exec → lane-session → agy|grok
```

One `run-supervisor` remains visible and repeats bounded `watch` calls until a
terminal state; it does not make lifecycle decisions. On Linux with a user
systemd manager, `lane-bg` launches a transient service so host tool cleanup
cannot reap the controller or provider after `start` returns. `LANE_BG_BACKEND=nohup` is kept
as a compatibility/test fallback.

## Observe and control

Use short, typed calls:

```bash
lane-ctl status --run-dir "$RUN_DIR" --task-id "$TASK_ID" --json
lane-ctl events --run-dir "$RUN_DIR" --task-id "$TASK_ID" --json
lane-ctl tail --run-dir "$RUN_DIR" --task-id "$TASK_ID" --lines 80
lane-ctl retry --run-dir "$RUN_DIR" --task-id "$TASK_ID"
lane-ctl fallback --run-dir "$RUN_DIR" --task-id "$TASK_ID" # typed recovery only
lane-ctl cancel --run-dir "$RUN_DIR" --task-id "$TASK_ID"
```

Normal orchestration reacts to compact `events.jsonl` records. `tail` is for an
error, stall, or explicit diagnostic request, not a continuous token-expensive
log loop. A retry reuses the recorded argv array from the current attempt's
`control.json`; it never
reconstructs or shell-evaluates a free-form command. The argv schema and prompt
digest are revalidated, the task hash must still match, and the control plane
permits two attempts by the selected primary provider. Retry writes
`attempts/02` without overwriting 01. After a second sanitized
`fallback_eligible` primary-provider failure, the controller alone
may create `attempts/03` with fixed provider/model/effort: `codex`,
`gpt-5.6-sol`, `high`. No fourth attempt is permitted.

Grok runs with `bypassPermissions`; AGY runs with `always-proceed` because headless interactive approval cannot
wait for an operator. This does not grant control-plane ownership: an outer
Bubblewrap boundary mounts the repository `.agents` tree read-only only for the
provider. To avoid nested-sandbox denial of terminal commands, the primary provider's native
sandbox is `off` inside that boundary; Bubblewrap itself exposes the project,
private temp directories, and only its conversation state (`~/.grok` or
`~/.gemini/antigravity-cli`) as writable, the rest of the host as
read-only, and then over-mounts `.agents` read-only. Host `/run`, `/tmp`, and
`/var/tmp` are not shared; when `/etc/resolv.conf` targets a file below `/run`,
only that resolved file is restored with a read-only bind so OIDC and provider
DNS continue to work. Active pathname Unix sockets that would reappear through
a writable bind are masked, and the provider environment is allowlisted.
`agents-doctor` reproduces this structural resolver probe before routing AGY or Grok.
This boundary does not claim network-egress isolation. The `owns_paths`
contract remains the narrower behavioral boundary. The final response carries
one task/prompt-bound report envelope; trusted `lane-session` validates it and
atomically materializes root `report.md`.
Codex uses its inner `workspace-write` sandbox and approval `never` inside the
same outer Bubblewrap boundary. It is ephemeral, has multi-agent disabled, and
cannot write `.agents`; `lane-session` parses its JSON event stream and writes
the canonical report only after `turn.completed`.

Status deliberately distinguishes `provider_incomplete`,
`awaiting_verification`, `verified`, and `verification_failed`. Provider exit 0
with a partial root report becomes `provider_incomplete → retry`. A missing,
duplicate, malformed, oversized, wrong-task, or wrong-prompt report envelope is
a provider protocol failure (exit 65) and is also retryable; neither case is
ready for verification.

For schema v2, `status`, `verify`, and `accept` also require the current
attempt's trusted `runtime.json` and matching `report_sha256`. Changing a root
report after the provider exits makes it untrusted. Retry archives that root
report under the old attempt before launching the next one; acceptance stores
the same digest in `acceptance.json`.

## Verify independently

After provider exit 0 plus a complete report (normally driven by the controller):

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
check-owns-paths "$TASK_FILE" --run-scope # shared daytime run worktree
lane-ctl accept \
  --run-dir "$RUN_DIR" \
  --task-file "$TASK_FILE" \
  --project-cwd "$PROJECT_CWD"
```

`accept` checks the unchanged task hash, provider exit 0, canonical report
status, `owns-check.json`, and current-attempt verification. Daytime runs do not
invoke an LLM reviewer; historical explicit review gates stop for an operator
decision.
Only then does it write root `acceptance.json` and set state to accepted.

The controller uses `--run-scope` because concurrent tasks share one worktree:
the gate checks the union of every repeatedly pre-dispatch-validated, disjoint
`owns_paths`. This prevents sibling changes from creating false violations
while still rejecting every change outside the run contract. Direct and night
single-task calls remain strict per-task checks.

Independently of scope, the gate ignores the `.agents/` control plane and the
root living-memory files (`PROGRESS.md`, `LESSONS.md`). The shared
session-ledger hook flushes `PROGRESS.md` from any concurrent orchestrator or
supervisor session in the same worktree, so treating those files as writer
changes would create false `owns_paths` violations during a clean task.

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
  controller.json
  controller/
    lane-bg.pid
    lane-bg.exit
    lane-bg.supervisor.log
  events.jsonl
  sessions.json
  artifacts/<task-id>/
    state.json
    heartbeat.json
    report.md
    owns-check.json
    acceptance.json
    outcome.json # aggregated result manifest for supervisors (exit_status, files_changed)
    review.json
    attempts/01/
      control.json
      prompt.md
      lane-bg.pid
      lane-bg.exit
      lane-bg.supervisor.log
      lane-exec.log
      provider.out
      runtime.json # includes prompt/report digests and isolation mode
      verification.json
    attempts/02/
      ...
    attempts/03/ # optional fixed Codex Sol high fallback
      ...
```

`lane-exec` appends atomic single-write JSONL records for start, timeout,
interruption, and exit. The final exit record and log line are written before
the log file is closed, so a successful child exits 0 instead of being masked by
supervisor cleanup.

Registered state and events distinguish live work from immutable task YAML.
`STATUS.md` is rebuilt from state/acceptance by `run-board`; heartbeat never
appends to it. A run with merge.json/MERGE.md is terminal and is not stalled.

## Gate observability

Per-run receipts (`owns-check.json`, `outcome.json`) record the *terminal* state
of a task, so a transient block that later clears leaves no trace there. To
review gates over time, every gate evaluation also appends one line to a
durable, append-only log:

```text
~/.agents/logs/gate-events.jsonl   # schema: schemas/gate-event-v1.schema.json
```

`check-owns-paths` (owns-paths), `run-validate` (validate), `lane-ctl accept`
(accept), and `lane-ctl verify` (verification) all write through the shared
best-effort `bin/gate_log.py` — a failed write never breaks the gate. Override
the path with `CLAUDE_LANE_GATE_LOG`; set it to `off` to disable (the test
suite does).

Review the last N days (default 7) with `gate-report`:

```bash
gate-report                       # markdown summary
gate-report --days 14 --json      # machine-readable
gate-report --project my-app --gate owns-paths
```

It aggregates pass/reject/fail counts per gate, top `owns_paths` violations,
top `never_touch` hits, top blocking reasons, and a per-project breakdown — the
weekly loop for spotting recurring blocks and false positives, then fixing the
contracts or the gate. Schedule it with the `loop` skill or cron.

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

Only `EndTurn` is a successful Grok terminal reason. `Cancelled`, `Error`, and
unknown terminal reasons are protocol failures with a non-zero wrapper exit;
raw unknown values remain sanitized in runtime receipts.
Even a complete-looking report received before `Cancelled` is discarded.

## Compatibility tools

`lane-wait`, `lane-poll`, `lane-mode-check`, and legacy `MODE` prompts remain
for older runs. New orchestration uses `run-controller` plus `run-supervisor`;
`lane-ctl` and `lane-supervisor` remain the typed low-level/recovery path.

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
After two classified Grok availability failures, the runner may start the one
fixed Codex Sol high recovery attempt through the same receipt chain. Grok
receives no-subagent and outer workspace-sandbox guardrails. Merge and push are
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
