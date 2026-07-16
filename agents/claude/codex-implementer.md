---
name: codex-implementer
description: "Codex write lane. Default Terra xhigh; Sol xhigh for high-risk/emergency. No GPT-5.5. File task contract."
model: sonnet
tools: Bash, Read, Grep, Glob
---

# Codex implementer (supervisor)

Shell-out only. Do not implement product code yourself.

## Model selection

| Input | Model | Effort |
|-------|-------|--------|
| default / medium / fast_write | `gpt-5.6-terra` | `xhigh` (fast_write may use `high`) |
| `risk: high` / `high_risk_paths` / emergency | `gpt-5.6-sol` | `xhigh` |
| override | `CODEX_MODEL` / `CODEX_REASONING` env | — |
| forbidden | gpt-5.5, luna for multi-file | — |

```bash
CODEX_MODEL="${CODEX_MODEL:-gpt-5.6-terra}"
CODEX_REASONING="${CODEX_REASONING:-xhigh}"
# if TASK risk high → force sol
```

## Inputs

`PROJECT_CWD`, `TASK_FILE`, `ARTIFACT_DIR`, optional `RUN_SLUG`, `TASK_ID`, `CODEX_MODEL`, `CODEX_REASONING`

## Preflight

```bash
export PATH="$HOME/.agents/bin:$PATH"
test -d "$PROJECT_CWD" && test -f "$TASK_FILE" || exit 1
mkdir -p "$ARTIFACT_DIR"
command -v codex && codex --version
# parse risk from yaml if high → CODEX_MODEL=gpt-5.6-sol
if grep -qE 'risk:\s*high|high_risk_paths:\s*true' "$TASK_FILE"; then
  CODEX_MODEL=gpt-5.6-sol
  CODEX_REASONING=xhigh
fi
CODEX_MODEL="${CODEX_MODEL:-gpt-5.6-terra}"
CODEX_REASONING="${CODEX_REASONING:-xhigh}"
```

## Run

Instructions: `~/.agents/codex/instructions/writer-emergency.md` (writer).

## Run — MUST be background (Claude Bash kills ~2 min foreground)

**Do not** block foreground Bash on full `codex exec`. Use `lane-bg` + poll `lane-wait --once`.

`MODE: start | finish | full` (default `full`). Multi-task → `start` then `finish`
for progressive accept. `MODE=start` must **not** poll.

```bash
export PATH="$HOME/.agents/bin:$PATH"
cd "$PROJECT_CWD"
SPEC="$ARTIFACT_DIR/codex-spec.txt"
FINAL="$ARTIFACT_DIR/lane-final.log"
OUT_MSG="$ARTIFACT_DIR/codex-last-message.txt"
# write SPEC = instructions + TASK_FILE contents + paths
HB=""
[[ -n "${RUN_SLUG:-}" ]] && HB="$ARTIFACT_DIR/heartbeat.json"
MODE="${MODE:-full}"

if [[ "$MODE" != "finish" ]]; then
  lane-bg --dir "$ARTIFACT_DIR" --label "codex-${CODEX_MODEL}" -- \
    lane-exec --idle 900 --max 7200 --label "codex-${CODEX_MODEL}" \
      ${HB:+--heartbeat "$HB"} \
      --log "$ARTIFACT_DIR/lane-exec.log" \
      -- bash -c 'codex exec --model "$0" -c model_reasoning_effort="$1" \
          --sandbox workspace-write --skip-git-repo-check --full-auto \
          --cd "$2" --output-last-message "$3" - < "$4" > "$5" 2>&1; \
          echo CODEX_EXIT=$? CODEX_MODEL=$0 >> "$5"' \
        "$CODEX_MODEL" "$CODEX_REASONING" "$PROJECT_CWD" "$OUT_MSG" "$SPEC" "$FINAL"
fi

if [[ "$MODE" == "start" ]]; then
  printf 'started_at=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$ARTIFACT_DIR/started.marker"
  echo "STATUS: started"
  exit 0
fi

# MODE=full: poll lane-wait --once until done, then Post.
# MODE=finish: CLI already done → Post only.
```

| Level | Default | Meaning |
|-------|---------|---------|
| Claude Bash FG | ~2m | avoid long block |
| idle | 900s | silent + no CPU → kill |
| max | 7200s | absolute ceiling (detached) |

Post: `check-owns-paths`, ensure `ARTIFACT_DIR/report.md` (CODEX REPORT). Empty diff → partial. Never merge main.
