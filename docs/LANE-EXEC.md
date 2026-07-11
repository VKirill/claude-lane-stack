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

## Heartbeat (optional)

`lane-heartbeat` can update `artifacts/<id>/heartbeat.json` during the run; mtime counts as activity even if the CLI is quiet.
