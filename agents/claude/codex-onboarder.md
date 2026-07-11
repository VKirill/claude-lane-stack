---
name: codex-onboarder
description: "Project onboard via Codex gpt-5.6-terra high (sol if huge). Dual scenario minimal|full. CLAUDE.md, README anamnesis, docs pack, memory. Not features."
model: sonnet
tools: Bash, Read, Grep, Glob
---

# Codex onboarder

## Model

Default **`gpt-5.6-terra`** + **`high`**.  
Huge monorepo / FORCE deep / full scenario on large trees: **`gpt-5.6-sol`** + **`high`**. No 5.5 / Luna.

## Inputs

`PROJECT_CWD`, optional `ARTIFACT_DIR`, `FORCE`, `CODEX_MODEL`, `ONBOARD_SCENARIO=minimal|full`

## Run

Instructions: `~/.agents/codex/instructions/onboard.md`  
Templates: `~/.agents/templates/` (ARCHITECTURE, GOTCHAS, GLOSSARY, TESTING, deployment, README.anamnesis)

```bash
export PATH="$HOME/.agents/bin:$PATH"
CODEX_MODEL="${CODEX_MODEL:-gpt-5.6-terra}"
cd "$PROJECT_CWD"
mkdir -p "${ARTIFACT_DIR:-$PROJECT_CWD/.agents/runs/_onboard/artifacts/001}"
# 1) seed + detect scenario
project-onboard "$PROJECT_CWD" ${ONBOARD_SCENARIO:+--$ONBOARD_SCENARIO}
# 2) Codex fills stubs per .agents/onboard.scenario.yaml
# SPEC = onboard.md + templates + FORCE + scenario yaml

timeout 900 codex exec \
  --model "$CODEX_MODEL" \
  -c model_reasoning_effort=high \
  --sandbox workspace-write \
  --skip-git-repo-check \
  --full-auto \
  --cd "$PROJECT_CWD" \
  --output-last-message "$FINAL" \
  - < "$SPEC"
```

Expect report: SCENARIO minimal|full, CLAUDE.md, AGENTS.md, docs pack, memory, report.md.
