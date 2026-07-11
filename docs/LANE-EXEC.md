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

# 1) Detach (returns immediately)
lane-bg --dir "$ARTIFACT_DIR" --label agy-frontend -- \
  lane-exec --idle 600 --max 5400 --log "$ARTIFACT_DIR/lane-exec.log" -- \
  agy --print "..." --agent lane-frontend --print-timeout 90m ...

# 2) Poll with short calls (each < 30s)
lane-wait --dir "$ARTIFACT_DIR" --once
# exit 0 = done, 2 = still running, 3 = not started, 124 = max-wait (loop mode)
```

| File | Meaning |
|------|---------|
| `artifacts/N/lane-bg.pid` | detached supervisor pid |
| `artifacts/N/lane-bg.exit` | exit code when finished |
| `artifacts/N/lane-bg.supervisor.log` | combined stdout/stderr of the job |
| `artifacts/N/lane-exec.log` | activity-aware wrapper log |

Optional: host `run_in_background=true` on the `lane-bg` Bash call — still prefer `lane-bg` so the job survives agent restarts.

## Heartbeat (optional)

`lane-heartbeat` can update `artifacts/<id>/heartbeat.json` during the run; mtime counts as activity even if the CLI is quiet.
