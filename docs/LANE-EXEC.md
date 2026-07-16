# lane-exec — activity-aware timeouts for AGY / Grok / Codex

## Problem

Hard `timeout 570` / short `--print-timeout` kills agents that are **still thinking or working**. Supervisors then re-dispatch and waste money.

## Solution

`~/.agents/bin/lane-exec` wraps the CLI with **three levels**:

| Level | Flag | Default | Behavior |
|-------|------|---------|----------|
| **1. Idle** | `--idle SEC` | 600–900 | Kill only if **no stdout** and **no CPU** (and no heartbeat mtime) for SEC |
| **2. Max** | `--max SEC` | 5400–7200 | Absolute wall clock — always kills |
| **3. Grace** | (auto) | 80% of max | Log warning only; does not kill |

Any new output **or** CPU tick on the child **resets idle**.

## Usage

```bash
export PATH="$HOME/.agents/bin:$PATH"

lane-exec --idle 600 --max 5400 --label agy-frontend \
  --log "$ARTIFACT_DIR/lane-exec.log" \
  --heartbeat "$ARTIFACT_DIR/heartbeat.json" \
  -- agy --print "..." --agent lane-frontend \
       --print-timeout 90m \   # must be ≥ max so agy does not self-kill
       --mode accept-edits --dangerously-skip-permissions \
       --add-dir "$PROJECT_CWD"
```

Exit `124` = idle or max timeout (same convention as GNU `timeout`).

## Defaults by lane (in implementer agents)

| Lane | idle | max |
|------|------|-----|
| AGY | 10m | 90m |
| Grok | 15m | 2h |
| Codex write | 15m | 2h |
| Codex review | 15m | 90m |

## What supervisors must NOT do

- `timeout 570 agy ...` for production runs  
- `--print-timeout 9m` while max wall is longer (agy will die first)  
- Kill and re-dispatch after a single 124 without reading `lane-exec.log`  
- **Long foreground Claude Bash** wrapping `lane-exec` / `agy` / `grok` / `codex` — host kills ~**2 minutes** (this is the #1 false “timeout”)

## Background + poll (required under Claude Code)

Claude’s Bash tool kills **foreground** commands around ~2 minutes.  
`lane-exec` idle/max only apply to the **child** process. If Bash is killed first, the whole tree dies.

**Always:**

```bash
export PATH="$HOME/.agents/bin:$PATH"

# 1) Detach (returns immediately); AGY/Grok keep run-scoped warm context.
lane-bg --dir "$ARTIFACT_DIR" --label agy-frontend -- \
  lane-exec --idle 600 --max 5400 --log "$ARTIFACT_DIR/lane-exec.log" -- \
  lane-session run --provider agy --run-dir "$RUN_DIR" \
    --task-id "$TASK_ID" --role lane-frontend --cwd "$PROJECT_CWD" \
    --prompt-file "$SPEC" --output "$ARTIFACT_DIR/lane-final.log" \
    --model "Gemini 3.5 Flash (High)"

# 2) Poll with short calls (each < 30s)
lane-wait --dir "$ARTIFACT_DIR" --once
# exit 0 = done, 2 = still running, 3 = not started, 124 = max-wait (loop mode)

# Multi-task progressive (PM): scan all artifacts under a run
lane-poll --run-dir "$RUN_DIR"
# finish_ready>0 → those CLIs finished; dispatch MODE=finish + accept NOW
# do not wait for other still-running siblings
```

| File | Meaning |
|------|---------|
| `artifacts/N/lane-bg.pid` | detached supervisor pid |
| `artifacts/N/lane-bg.exit` | exit code when finished |
| `artifacts/N/lane-bg.supervisor.log` | combined stdout/stderr of the job |
| `artifacts/N/lane-exec.log` | activity-aware wrapper log |
| `sessions.json` | current AGY/Grok session IDs, slot ownership, successful-turn counts, rotation history |

Optional: host `run_in_background=true` on the `lane-bg` Bash call — still prefer `lane-bg` so the job survives agent restarts.

## Progressive accept (multi-task)

When ≥2 write tasks share a run, implementers use **`MODE=start`** (detach only)
and **`MODE=finish`** (report after CLI done). PM owns the poll loop via
**`lane-poll`**, accepts each task as soon as it is finish_ready, frees the slot,
and may start the next ready task. Cap remains **3 concurrent** writers;
total tasks may be larger via pipeline refill.

**Forbidden join-wait:** spawning N Agents that each poll-until-done in one PM
turn — the host joins all Agent tool calls, so you only continue after the
slowest.

**Hard guard:** `lane-mode-check --run-dir RUN --mode full` exits **2** when the
run has ≥2 task cards. Implementers call it in preflight and refuse with
`STATUS: refused_full_on_multi_task`. Override (tests only): `LANE_ALLOW_FULL=1`.

**Detached heartbeat:** pass `--heartbeat ARTIFACT_DIR/heartbeat.json` to
`lane-exec`. On real activity (stdout / CPU) it rewrites the file (throttled)
so `lane-stall-check` works after `MODE=start` when the Claude supervisor is
gone. Idle kill still uses *real* activity — heartbeat is not written on a
timer alone.

## night-review

`night-review <repo-root>` batches today's merged runs and micro commits into one read-only Codex review.
For an unattended run, start it through `lane-bg`:

```bash
lane-bg --dir "$ART" --label night-review -- night-review "$(pwd)"
```

### night-review-all

`night-review-all` auto-discovers projects under `~/apps`, `~/sites`, and `~/tools` using the same lane-stack markers as `docs-maintain-all`. It reviews only repositories active in the last 24 hours (recent commits on the current branch or today's session-log directory).

Cron example:
```text
0 3 * * * $HOME/.agents/bin/night-review-all >> $HOME/.agents/logs/night-review.log 2>&1
```

## Warm session affinity (AGY / Grok)

`lane-session` removes the cognitive cold start without giving up safe
parallelism:

- the first Grok task gets a preassigned UUID; later tasks use `--resume`;
- Grok headless calls use `--prompt-file` and `--no-auto-update`, keeping task
  contents out of process argv while avoiding background update checks;
- the first AGY task's open conversation DB is detected and later tasks use
  `--conversation`;
- the warmest free slot is preferred; a busy slot is never used concurrently;
- up to three slots may exist per provider/role, matching the PM parallel cap;
- default rotation is seven successful tasks; `LANE_SESSION_MAX_TASKS` may set
  1–10 and `LANE_SESSION_POOL_SIZE` may set 1–3; retries count as successful
  turns even when they reuse the same task ID;
- provider failure, stale interrupted state, cwd change, or model change forces
  a fresh session;
- session IDs are stored under the exact absolute run directory, so two runs in
  the same repository/cwd never resume each other's conversations; neither
  provider uses its ambiguous global `--continue` mode;
- locks live under the runtime temp directory, not inside the repository.
- SIGINT/SIGTERM invalidates the lease and terminates the provider's full
  process group before another task may reuse that slot.

Inspect a run without modifying it:

```bash
lane-session status --run-dir .agents/runs/<slug>
```

## Heartbeat (optional)

`lane-heartbeat` can update `artifacts/<id>/heartbeat.json` during the run; mtime counts as activity even if the CLI is quiet.
