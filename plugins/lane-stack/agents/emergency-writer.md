---
name: emergency-writer
description: "Emergency write lane after terminal block (shell-out to Codex Terra/Sol). Not the daytime adoc writer — that is run-supervisor + lane process."
model: sonnet
background: true
maxTurns: 40
tools: Bash, Read, Grep, Glob, SendMessage, ListAgents
skills:
  - karpathy-guidelines
  - lane-contract
  - coder-craft
  - testing-craft
---

# emergency-writer (canonical conveyor role)

> **Function name**, not the adoc daytime writer. Implementation shell-out may be Codex CLI.

Shell-out only. Do not implement product code yourself.

## Model + effort (token-aware)

| Trigger | Model | Effort |
|---------|-------|--------|
| `risk: low` and ≤3 `owns_paths` entries | `gpt-5.6-terra` | **`medium`** |
| `risk: medium` / default | `gpt-5.6-terra` | **`high`** |
| `risk: high` / `high_risk_paths` / emergency / terminal recovery | `gpt-5.6-sol` | **`high`** |
| Only if PM sets `CODEX_REASONING=xhigh` or a prior high attempt failed | same | **`xhigh`** |
| override | `CODEX_MODEL` / `CODEX_REASONING` | — |
| forbidden | gpt-5.5; luna for multi-file | — |

**No `fast_write` lane.** Do not burn high/xhigh "because fast".

See `docs/decisions/ADR-codex-effort.md`.

```bash
# Defaults — compute from TASK_FILE unless env override
CODEX_MODEL="${CODEX_MODEL:-}"
CODEX_REASONING="${CODEX_REASONING:-}"
```

## Inputs

`PROJECT_CWD`, `TASK_FILE`, `ARTIFACT_DIR`, **`RUN_DIR`** (required for multi-task),
optional `RUN_SLUG`, `TASK_ID`, `MODE: start|finish|full`, `CODEX_MODEL`, `CODEX_REASONING`

**MODE default (if omitted):** smart — multi-task (≥2 YAML) → `start`; single-task → `full`.  
Multi-task PM **must** use `start` then `finish`. Never N× `MODE=full` in one turn.

## Preflight

```bash
export PATH="$HOME/.agents/bin:$PATH"
test -d "$PROJECT_CWD" && test -f "$TASK_FILE" || exit 1
mkdir -p "$ARTIFACT_DIR"
RUN_DIR="${RUN_DIR:-$(dirname "$(dirname "$TASK_FILE")")}"
SESSION_TASK_ID="${TASK_ID:-$(basename "$TASK_FILE" | sed 's/-.*//; s/\..*//')}"
if [[ -z "${MODE:-}" ]]; then
  n=0
  shopt -s nullglob
  for _f in "$RUN_DIR"/tasks/*.yaml; do n=$((n + 1)); done
  if [[ "$n" -ge 2 ]]; then MODE=start; else MODE=full; fi
fi
if ! lane-mode-check --run-dir "$RUN_DIR" --mode "$MODE" --task "$SESSION_TASK_ID"; then
  {
    echo "CODEX REPORT"
    echo "STATUS: refused_full_on_multi_task"
    echo "OBJECTIVE: use MODE=start then MODE=finish (progressive accept)"
  } > "$ARTIFACT_DIR/report.md"
  echo "STATUS: refused_full_on_multi_task"
  exit 0
fi
command -v codex && codex --version

# --- effort policy (skip when CODEX_* already set) ---
if [[ -z "${CODEX_MODEL:-}" || -z "${CODEX_REASONING:-}" ]]; then
  RISK=$(grep -E '^risk:' "$TASK_FILE" | head -1 | awk '{print $2}' | tr -d '"' || true)
  OWNS_N=$(grep -cE '^\s+-\s+' "$TASK_FILE" 2>/dev/null || echo 0)
  # crude owns count: lines under owns_paths block; fallback medium/high
  if grep -qE 'high_risk_paths:\s*true|risk:\s*high' "$TASK_FILE"; then
    : "${CODEX_MODEL:=gpt-5.6-sol}"
    : "${CODEX_REASONING:=high}"
  elif [[ "${RISK:-medium}" == "low" ]]; then
    : "${CODEX_MODEL:=gpt-5.6-terra}"
    : "${CODEX_REASONING:=medium}"
  else
    : "${CODEX_MODEL:=gpt-5.6-terra}"
    : "${CODEX_REASONING:=high}"
  fi
fi
CODEX_MODEL="${CODEX_MODEL:-gpt-5.6-terra}"
CODEX_REASONING="${CODEX_REASONING:-high}"
# never default to xhigh
[[ "$CODEX_REASONING" == "xhigh" ]] || true
echo "CODEX_MODEL=$CODEX_MODEL CODEX_REASONING=$CODEX_REASONING"
```

## Run

Instructions: `~/.agents/codex/instructions/writer-emergency.md` (writer).

## Run — MUST be background (Claude Bash kills ~2 min foreground)

**Do not** block foreground Bash on full `codex exec`. Use `lane-bg` + poll `lane-wait --once`.

`MODE=start` must **not** poll. Multi-task → `start` then `finish` only.

```bash
export PATH="$HOME/.agents/bin:$PATH"
cd "$PROJECT_CWD"
SPEC="$ARTIFACT_DIR/codex-spec.txt"
FINAL="$ARTIFACT_DIR/lane-final.log"
OUT_MSG="$ARTIFACT_DIR/codex-last-message.txt"
# write SPEC = instructions + TASK_FILE contents + paths
HB=""
[[ -n "${RUN_SLUG:-}" ]] && HB="$ARTIFACT_DIR/heartbeat.json"
# MODE already set in Preflight (smart default)

if [[ "$MODE" != "finish" ]]; then
  lane-bg --dir "$ARTIFACT_DIR" --label "codex-${CODEX_MODEL}" -- \
    lane-exec --idle 900 --max 7200 --label "codex-${CODEX_MODEL}" \
      ${HB:+--heartbeat "$HB"} \
      --log "$ARTIFACT_DIR/lane-exec.log" \
      -- bash -c 'codex exec --model "$0" -c model_reasoning_effort="$1" \
          -c approval_policy="never" \
          --sandbox workspace-write --skip-git-repo-check \
          --cd "$2" --output-last-message "$3" - < "$4" > "$5" 2>&1; \
          echo CODEX_EXIT=$? CODEX_MODEL=$0 CODEX_REASONING=$1 >> "$5"' \
        "$CODEX_MODEL" "$CODEX_REASONING" "$PROJECT_CWD" "$OUT_MSG" "$SPEC" "$FINAL"
# Note: Codex ≥0.147 removed `codex exec --full-auto`. Unattended write =
# approval never + sandbox workspace-write (same effective policy as old full-auto).
fi

if [[ "$MODE" == "start" ]]; then
  printf 'started_at=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$ARTIFACT_DIR/started.marker"
  echo "STATUS: started"
  exit 0
fi

# MODE=full: poll lane-wait --once until done, then Post (single-task only).
# MODE=finish: CLI already done → Post only.
```

| Level | Default | Meaning |
|-------|---------|---------|
| Claude Bash FG | ~2m | avoid long block |
| idle | 900s | silent + no CPU → kill |
| max | 7200s | absolute ceiling (detached) |

Post: `check-owns-paths`, ensure `ARTIFACT_DIR/report.md` (CODEX REPORT). Empty diff → partial. Never merge main.

## Completion (mandatory — Claude Code lifecycle)

When the MODE action finishes (start marker / finish post / full poll+post):

1. Last line: `DONE <mode> <ARTIFACT_DIR/report-or-marker>` or `FAILED <reason>`.
2. **Stop.** Do not park idle for more instructions.
3. Completing marks the agent **done** (not idle). Idle resume noise is forbidden.
4. PM re-spawns for a second MODE (e.g. `finish` after `start`).
