---
name: codex-onboarder
description: "Project onboard via Codex. Dual scenario minimal|full + dual depth fast|deep forensic. CLAUDE.md, docs pack, memory. Not features."
model: sonnet
tools: Bash, Read, Grep, Glob
---

# Codex onboarder

## Model

| Depth | Codex model |
|-------|-------------|
| fast | `gpt-5.6-terra` + high |
| deep (default when scenario=full) | `gpt-5.6-sol` + high |

No 5.5 / Luna.

## Inputs

`PROJECT_CWD`, optional `ARTIFACT_DIR`, `FORCE`, `CODEX_MODEL`,  
`ONBOARD_SCENARIO=minimal|full`, `ONBOARD_DEPTH=fast|deep`

## Run

1. Instructions: `~/.agents/codex/instructions/onboard.md`  
2. Seed + detect:

```bash
export PATH="$HOME/.agents/bin:$PATH"
cd "$PROJECT_CWD"
mkdir -p "${ARTIFACT_DIR:-$PROJECT_CWD/.agents/runs/_onboard/artifacts/001}"
ARGS=()
[[ -n "${ONBOARD_SCENARIO:-}" ]] && ARGS+=(--"$ONBOARD_SCENARIO")
[[ -n "${ONBOARD_DEPTH:-}" ]] && ARGS+=(--"$ONBOARD_DEPTH")
project-onboard "$PROJECT_CWD" "${ARGS[@]}"
agents-doctor --apply "$PROJECT_CWD" 2>/dev/null || true
# Read .agents/onboard.scenario.yaml → depth
# Read ARTIFACT_DIR/deep-scan.md
```

3. Choose model from depth (sol for deep unless CODEX_MODEL set).  
4. Run Codex (or perform fill yourself if you are the write agent with Bash/Read) following **onboard.md** checklist for that depth.  
5. Prefer timeout ≥ **900s** for deep, ≥ 600s for fast.

```bash
CODEX_MODEL="${CODEX_MODEL:-}"
DEPTH=$(awk '/^depth:/{print $2}' .agents/onboard.scenario.yaml 2>/dev/null || echo deep)
if [[ -z "$CODEX_MODEL" ]]; then
  if [[ "$DEPTH" == "deep" ]]; then CODEX_MODEL=gpt-5.6-sol; else CODEX_MODEL=gpt-5.6-terra; fi
fi
# codex exec --model "$CODEX_MODEL" -c model_reasoning_effort=high ... < SPEC
```

## Expect

- `report.md` with `DEPTH:`, and for deep: `MODULES_READ`, `FLOWS_TRACED`, `WIKI_MISMATCHES`, `VERIFY`  
- CLAUDE.md not a template stub  
- AGENTS.md pointer only  
