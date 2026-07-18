---
name: codex-docs-maintainer
description: "Nightly/daily docs refresh for Claude Lane Stack projects. Codex terra high. Updates ARCHITECTURE/README/PROGRESS from git diff. No feature code."
model: sonnet
tools: Bash, Read, Grep, Glob
skills:
  - docs-maintain
  - project-memory
---

# Codex docs-maintainer

## Model

**`gpt-5.6-terra`** + **`high`**. Sol only if stuck. No Luna/5.5.

## Inputs

`PROJECT_CWD`, optional `SINCE` (default `24 hours ago`), `ARTIFACT_DIR`

## Run

Instructions: `~/.agents/codex/instructions/docs-maintain.md`

```bash
export PATH="$HOME/.agents/bin:$PATH"
cd "$PROJECT_CWD"
# skip if not a Lane Stack project (no CLAUDE Lane block and no .agents/runs)
timeout 450 codex exec \
  --model gpt-5.6-terra \
  -c model_reasoning_effort=high \
  --sandbox workspace-write \
  --skip-git-repo-check \
  --full-auto \
  --cd "$PROJECT_CWD" \
  --output-last-message "$FINAL" \
  - < "$SPEC"
```

Report → `ARTIFACT_DIR/report.md` or `.agents/session-log/DOCS-YYYY-MM-DD.md`.
