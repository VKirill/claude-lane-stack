---
name: codex-onboarder
description: "DEPRECATED alias for `project-onboarder`. Use `project-onboarder` in new dispatches. Same tools and behavior."
model: sonnet
background: true
maxTurns: 30
tools: Bash, Read, Grep, Glob, SendMessage, ListAgents
skills:
  - project-onboard
  - project-docs
  - project-life
---

# codex-onboarder → `project-onboarder` (compat alias)

> **Deprecated name.** Prefer **`project-onboarder`**. This agent is identical for one release cycle.


# project-onboarder (canonical conveyor role)

> **Function name**, not the adoc daytime writer. Implementation shell-out may be Codex CLI.
> Compatibility alias still installed: `codex-onboarder`.

## Model + effort (token-aware)

| Depth | Codex model | Effort |
|-------|-------------|--------|
| minimal | `gpt-5.6-terra` | **medium** |
| deep (default when scenario=full) | `gpt-5.6-sol` | **high** |

No 5.5 / Luna. No default **xhigh**. No "fast" write lane.
See `docs/decisions/ADR-codex-effort.md`.

## Inputs

`PROJECT_CWD`, optional `ARTIFACT_DIR`, `FORCE`, `CODEX_MODEL`, `CODEX_REASONING`,  
`ONBOARD_SCENARIO=minimal|full`, `ONBOARD_DEPTH=minimal|deep`

## Run

1. Instructions: `~/.agents/codex/instructions/onboard.md`  
2. Seed + detect:

```bash
export PATH="$HOME/.agents/bin:$PATH"
cd "$PROJECT_CWD"
mkdir -p "${ARTIFACT_DIR:-$PROJECT_CWD/.agents/runs/_onboard/artifacts/001}"
ARGS=()
[[ -n "${ONBOARD_SCENARIO:-}" ]] && ARGS+=(--"$ONBOARD_SCENARIO")
# map legacy ONBOARD_DEPTH=fast → minimal
if [[ "${ONBOARD_DEPTH:-}" == "fast" ]]; then ONBOARD_DEPTH=minimal; fi
[[ -n "${ONBOARD_DEPTH:-}" ]] && ARGS+=(--"$ONBOARD_DEPTH")
project-onboard "$PROJECT_CWD" "${ARGS[@]}"
agents-doctor --apply "$PROJECT_CWD" 2>/dev/null || true
# Read .agents/onboard.scenario.yaml → depth
# Read ARTIFACT_DIR/deep-scan.md
```

3. Choose model + effort from depth (unless env override).  
4. Run Codex following **onboard.md** checklist for that depth.  
5. Prefer timeout ≥ **900s** for deep, ≥ 600s for minimal.

```bash
CODEX_MODEL="${CODEX_MODEL:-}"
CODEX_REASONING="${CODEX_REASONING:-}"
DEPTH=$(awk '/^depth:/{print $2}' .agents/onboard.scenario.yaml 2>/dev/null || echo deep)
[[ "$DEPTH" == "fast" ]] && DEPTH=minimal
if [[ -z "$CODEX_MODEL" ]]; then
  if [[ "$DEPTH" == "deep" ]]; then CODEX_MODEL=gpt-5.6-sol; else CODEX_MODEL=gpt-5.6-terra; fi
fi
if [[ -z "$CODEX_REASONING" ]]; then
  if [[ "$DEPTH" == "deep" ]]; then CODEX_REASONING=high; else CODEX_REASONING=medium; fi
fi
# codex exec --model "$CODEX_MODEL" -c model_reasoning_effort="$CODEX_REASONING" ... < SPEC
```

## Expect

- `report.md` with `DEPTH:`, and for deep: `MODULES_READ`, `FLOWS_TRACED`, `WIKI_MISMATCHES`, `VERIFY`  
- CLAUDE.md not a template stub  
- AGENTS.md pointer only  

## Completion (mandatory)

Last line: `DONE <path-to-report-or-CLAUDE.md>` or `FAILED <reason>`, then **stop**.
No idle park / no "ready for more docs work".
