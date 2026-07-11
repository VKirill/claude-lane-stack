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

## Run

1. Read task YAML + `/home/ubuntu/.agents/grok/instructions/writer.md`.  
2. Write combined prompt to temp SPEC. Include: only owns_paths; never merge main.  
3. Blocking:

```bash
cd "$PROJECT_CWD"
FINAL=$(mktemp -t grok-final.XXXXXX)
timeout 570 grok --prompt-file "$SPEC" \
  -m grok-4.5 \
  --reasoning-effort high \
  --permission-mode acceptEdits \
  --output-format plain \
  --cwd "$PROJECT_CWD" \
  > "$FINAL" 2>&1
echo GROK_EXIT=$? >> "$FINAL"
```

4. Re-run verification yourself; write `ARTIFACT_DIR/report.md` (GROK REPORT).  
5. Empty diff → STATUS partial.  
6. `check-owns-paths "$TASK_FILE" --cwd "$PROJECT_CWD"` — fail → STATUS partial.  
7. Heartbeat done if RUN_SLUG set.

No background. No self-implement. **Never merge/push main.**
