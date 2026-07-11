---
name: codex-implementer
description: Emergency GPT-5.6-sol write only if AGY and Grok unavailable. File task contract.
model: sonnet
tools: Bash, Read, Grep, Glob
---

# Codex emergency writer

Same I/O as grok-implementer (`PROJECT_CWD`, `TASK_FILE`, `ARTIFACT_DIR`).

Instructions: `/home/ubuntu/.agents/codex/instructions/writer-emergency.md`

```bash
timeout 570 codex exec \
  --model gpt-5.6-sol \
  -c model_reasoning_effort=xhigh \
  --sandbox workspace-write \
  --skip-git-repo-check \
  --cd "$PROJECT_CWD" \
  --output-last-message "$FINAL" \
  - < "$SPEC"
```

Report → `ARTIFACT_DIR/report.md` as CODEX REPORT. Prefer not to use this lane.
