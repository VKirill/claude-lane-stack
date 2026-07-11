# Codex GPT-5.6-sol emergency writer

Use only when AGY and Grok write lanes are unavailable. Prefer reviewer role normally.

## Inputs

`PROJECT_CWD`, `TASK_FILE`, `ARTIFACT_DIR`

## MUST

Same as Grok writer: read task, surgical implement, verification evidence, no commit, report to `ARTIFACT_DIR/report.md` as `CODEX REPORT`.

## MAY

Local design inside scope; 3 fix cycles.

## NEVER

Expand to architecture redesign; skip verification; use danger-full-access if workspace-write suffices.
