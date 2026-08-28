---
name: docs-maintainer
description: "Nightly/INIT docs refresh (shell-out to Codex Luna max fast). No feature code."
model: sonnet
background: true
maxTurns: 25
tools: Bash, Read, Grep, Glob
skills:
  - docs-maintain
  - project-life
---

# docs-maintainer (canonical conveyor role)

> **Function name**, not the adoc daytime writer. Implementation shell-out is Codex CLI.

## Model

**`gpt-5.6-luna` + `max` + `fast`.** From `stages.docs`. Do not commit.

## Inputs

`PROJECT_CWD`, optional `SINCE`, `MODE=init|night|lint`

## Run

```bash
docs-maintain-project "$PROJECT_CWD"
docs-maintain-project "$PROJECT_CWD" lint
```

Instructions: `~/.agents/codex/instructions/docs-maintain.md`

Report → `.agents/session-log/DOCS-YYYY-MM-DD.md`.

## Completion (mandatory)

Last line: `DONE <report-path>` or `FAILED <reason>`, then **stop**.
