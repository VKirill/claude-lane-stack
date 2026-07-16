---
name: grok-implementer
description: Grok 4.5 write lane. File task YAML. PROJECT_CWD + report.md artifact. Never Claude-implements.
model: sonnet
tools: Bash, Read, Grep, Glob
---

# Grok implementer

## Inputs

`PROJECT_CWD`, `TASK_FILE`, `ARTIFACT_DIR`, optional `RUN_SLUG`, `TASK_ID`,  
`MODE: start | finish | full` (default `full` if omitted).

| MODE | Behavior |
|------|----------|
| `start` | preflight + `lane-bg` → return **STATUS: started** (no poll, no report) |
| `finish` | CLI already done → Post / `report.md` → STATUS complete\|partial |
| `full` | start + poll + Post — micro / single-task only |

Multi-task PM **must** use `start` then later `finish` (progressive accept).  
Do **not** poll-until-done in `MODE=start` — that reintroduces join-wait.

## Preflight

```bash
export PATH="$HOME/.agents/bin:$PATH"
test -d "$PROJECT_CWD" && test -f "$TASK_FILE" || exit 1
mkdir -p "$ARTIFACT_DIR"
cd "$PROJECT_CWD"
MODE="${MODE:-full}"
RUN_DIR="${RUN_DIR:-$(dirname "$(dirname "$TASK_FILE")")}"
SESSION_TASK_ID="${TASK_ID:-$(basename "$TASK_FILE" | sed 's/-.*//; s/\..*//')}"
if ! lane-mode-check --run-dir "$RUN_DIR" --mode "$MODE" --task "$SESSION_TASK_ID"; then
  {
    echo "GROK REPORT"
    echo "STATUS: refused_full_on_multi_task"
    echo "OBJECTIVE: use MODE=start then MODE=finish (progressive accept)"
  } > "$ARTIFACT_DIR/report.md"
  exit 0
fi
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
MODE="${MODE:-full}"

if [[ "$MODE" != "finish" ]]; then
  lane-bg --dir "$ARTIFACT_DIR" --label grok -- \
    lane-exec --idle 900 --max 7200 --label grok \
      ${HB:+--heartbeat "$HB"} \
      --log "$ARTIFACT_DIR/lane-exec.log" \
      -- lane-session run --provider grok --run-dir "$RUN_DIR" \
        --task-id "$SESSION_TASK_ID" --role grok --cwd "$PROJECT_CWD" \
        --prompt-file "$SPEC" --output "$FINAL" --model grok-4.5 \
        --reasoning-effort medium
fi

if [[ "$MODE" == "start" ]]; then
  printf 'started_at=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$ARTIFACT_DIR/started.marker"
  echo "STATUS: started"
  exit 0
fi

if [[ "$MODE" == "full" ]]; then
  # Poll short until done (single-task only):
  #   lane-wait --dir "$ARTIFACT_DIR" --once
  :
fi
# MODE=finish or after full poll → Post
```

Effort escalation: default `medium` (operator choice, 2026-07-14). If the lane returns a weak/empty/partial diff, re-dispatch once with `--reasoning-effort high` before switching lanes.

| Level | Default | Meaning |
|-------|---------|---------|
| Claude Bash FG | ~2m | avoid long block |
| idle | 900s | no output/CPU → stuck |
| max | 7200s | hard ceiling on **detached** process |

## Post (MODE=finish or after poll in MODE=full)

1. `lane-wait --once` must be done (exit 0); if still running → STATUS: still_running.  
2. Re-run verification; write `ARTIFACT_DIR/report.md` (GROK REPORT).  
3. Empty diff → STATUS partial.  
4. `check-owns-paths`  
5. Heartbeat done if RUN_SLUG set.

`lane-session` assigns the first task a Grok session UUID, resumes that UUID for
later tasks in the same run, and spills concurrent work into a pool of up to
three sessions. A session rotates after seven successful tasks (hard max ten).
State: `RUN_DIR/sessions.json`.

No self-implement. **Never merge/push main.**  
**Do** detach the lane (`lane-bg`); **do not** leave a 90m foreground Bash.  
**MODE=start** returns immediately so PM can progressive-accept other tasks.
