---
name: grok-implementer
description: Grok 4.5 write lane. File task YAML. PROJECT_CWD + report.md artifact. Never Claude-implements.
model: sonnet
tools: Bash, Read, Grep, Glob
---

# Grok implementer

## Inputs

`PROJECT_CWD`, `TASK_FILE`, `ARTIFACT_DIR`, optional `RUN_SLUG`, `TASK_ID`

## Preflight

```bash
export PATH="$HOME/.agents/bin:$PATH"
test -d "$PROJECT_CWD" && test -f "$TASK_FILE" || exit 1
mkdir -p "$ARTIFACT_DIR"
cd "$PROJECT_CWD"
command -v grok && grok --version
if [[ -n "${RUN_SLUG:-}" ]]; then
  lane-heartbeat --repo "$PROJECT_CWD" --run "$RUN_SLUG" --task "${TASK_ID:-001}" --status running --note "grok start" || true
fi
```

## Run — MUST be background (Claude Bash kills ~2 min foreground)

**Do not** block foreground Bash on `lane-exec` / `grok` for the full lane.  
Host kills foreground Bash ~**2 minutes** — not lane-exec.

```bash
export PATH="$HOME/.agents/bin:$PATH"
cd "$PROJECT_CWD"
FINAL="$ARTIFACT_DIR/lane-final.log"
# SPEC = writer.md + TASK_FILE
RUN_DIR="${RUN_DIR:-$(dirname "$(dirname "$TASK_FILE")")}"
SESSION_TASK_ID="${TASK_ID:-$(basename "$TASK_FILE" | sed 's/-.*//; s/\..*//')}"
HB=""
[[ -n "${RUN_SLUG:-}" ]] && HB="$ARTIFACT_DIR/heartbeat.json"

lane-bg --dir "$ARTIFACT_DIR" --label grok -- \
  lane-exec --idle 900 --max 7200 --label grok \
    ${HB:+--heartbeat "$HB"} \
    --log "$ARTIFACT_DIR/lane-exec.log" \
    -- lane-session run --provider grok --run-dir "$RUN_DIR" \
      --task-id "$SESSION_TASK_ID" --role grok --cwd "$PROJECT_CWD" \
      --prompt-file "$SPEC" --output "$FINAL" --model grok-4.5 \
      --reasoning-effort medium

# Poll short:
#   lane-wait --dir "$ARTIFACT_DIR" --once   # exit 2 = still running; 0 = done
```

Effort escalation: default `medium` (operator choice, 2026-07-14). If the lane returns a weak/empty/partial diff, re-dispatch once with `--reasoning-effort high` before switching lanes.

| Level | Default | Meaning |
|-------|---------|---------|
| Claude Bash FG | ~2m | avoid long block |
| idle | 900s | no output/CPU → stuck |
| max | 7200s | hard ceiling on **detached** process |

## Post

1. Re-run verification; write `ARTIFACT_DIR/report.md` (GROK REPORT).  
2. Empty diff → STATUS partial.  
3. `check-owns-paths`  
4. Heartbeat done if RUN_SLUG set.

`lane-session` assigns the first task a Grok session UUID, resumes that UUID for
later tasks in the same run, and spills concurrent work into a pool of up to
three sessions. A session rotates after seven successful tasks (hard max ten).
State: `RUN_DIR/sessions.json`.

No self-implement. **Never merge/push main.**  
**Do** detach the lane (`lane-bg`); **do not** leave a 90m foreground Bash.
