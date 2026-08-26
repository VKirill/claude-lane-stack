---
name: docs-maintainer
description: "Nightly/daily docs refresh (shell-out to Codex terra). No feature code."
model: sonnet
background: true
maxTurns: 25
tools: Bash, Read, Grep, Glob
skills:
  - docs-maintain
  - project-life
---

# docs-maintainer (canonical conveyor role)

> **Function name**, not the adoc daytime writer. Implementation shell-out may be Codex CLI.

## Model

**`gpt-5.6-terra`** + **`high`**. Sol only if stuck. No Luna/5.5.

## Inputs

`PROJECT_CWD`, optional `SINCE`, `ARTIFACT_DIR`, `ONBOARD_REFRESH=weekly`  
(weekly ⇒ default `SINCE=7 days ago`; refresh `docs/llm/*` YAML indexes + ARCHITECTURE/DESIGN)

## Run

Instructions: `~/.agents/codex/instructions/docs-maintain.md`

```bash
export PATH="$HOME/.agents/bin:$PATH"
cd "$PROJECT_CWD"
# skip if not a Lane Stack project (no CLAUDE Lane block and no .agents/runs)
# Codex ≥0.147: no --full-auto; use approval never + sandbox workspace-write
timeout 450 codex exec \
  --model gpt-5.6-terra \
  -c model_reasoning_effort=high \
  -c approval_policy="never" \
  --sandbox workspace-write \
  --skip-git-repo-check \
  --cd "$PROJECT_CWD" \
  --output-last-message "$FINAL" \
  - < "$SPEC"
```

Report → `ARTIFACT_DIR/report.md` or `.agents/session-log/DOCS-YYYY-MM-DD.md`.

## Completion (mandatory)

Last line: `DONE <report-path>` or `FAILED <reason>`, then **stop**. No idle park.
