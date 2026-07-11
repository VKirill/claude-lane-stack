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

## Run — activity-aware timeout (not raw `timeout 570`)

```bash
cd "$PROJECT_CWD"
FINAL="$ARTIFACT_DIR/lane-final.log"
# SPEC = writer.md + TASK_FILE
HB=""
[[ -n "${RUN_SLUG:-}" ]] && HB="$ARTIFACT_DIR/heartbeat.json"

lane-exec --idle 900 --max 7200 --label grok \
  ${HB:+--heartbeat "$HB"} \
  --log "$ARTIFACT_DIR/lane-exec.log" \
  -- grok --prompt-file "$SPEC" \
    -m grok-4.5 \
    --reasoning-effort high \
    --permission-mode acceptEdits \
    --output-format plain \
    --cwd "$PROJECT_CWD" \
  > "$FINAL" 2>&1
echo GROK_EXIT=$? >> "$FINAL"
```

| Level | Default | Meaning |
|-------|---------|---------|
| idle | 900s (15m) | no output/CPU → stuck |
| max | 7200s (2h) | hard ceiling |

## Post

1. Re-run verification; write `ARTIFACT_DIR/report.md` (GROK REPORT).  
2. Empty diff → STATUS partial.  
3. `check-owns-paths`  
4. Heartbeat done if RUN_SLUG set.

No background. No self-implement. **Never merge/push main.**
