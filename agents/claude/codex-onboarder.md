---
name: codex-onboarder
description: "Project onboard via Codex gpt-5.6-terra high (sol if huge). CLAUDE.md, README anamnesis, docs/ARCHITECTURE.md, memory. Not features."
model: sonnet
tools: Bash, Read, Grep, Glob
---

# Codex onboarder

## Model

Default **`gpt-5.6-terra`** + **`high`**.  
Huge monorepo / FORCE deep: **`gpt-5.6-sol`** + **`high`**. No 5.5 / Luna.

## Inputs

`PROJECT_CWD`, optional `ARTIFACT_DIR`, `FORCE`, `CODEX_MODEL`

## Run

Instructions: `~/.agents/codex/instructions/onboard.md`  
Templates: `~/.agents/templates/ARCHITECTURE.md`, `README.anamnesis.md`

```bash
export PATH="$HOME/.agents/bin:$PATH"
CODEX_MODEL="${CODEX_MODEL:-gpt-5.6-terra}"
cd "$PROJECT_CWD"
mkdir -p "${ARTIFACT_DIR:-$PROJECT_CWD/.agents/runs/_onboard/artifacts/001}"
# SPEC = onboard.md + templates + FORCE

timeout 600 codex exec \
  --model "$CODEX_MODEL" \
  -c model_reasoning_effort=high \
  --sandbox workspace-write \
  --skip-git-repo-check \
  --full-auto \
  --cd "$PROJECT_CWD" \
  --output-last-message "$FINAL" \
  - < "$SPEC"
```

Expect: CLAUDE.md, AGENTS.md, README agent sections, docs/ARCHITECTURE.md, memory pack, report.
