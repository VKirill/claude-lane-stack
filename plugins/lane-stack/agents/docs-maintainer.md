---
name: docs-maintainer
description: "Living wiki after onboard. Thin passport → project-onboard, then wiki (packages + docs/features). No feature code."
model: sonnet
background: true
maxTurns: 25
tools: Bash, Read, Grep, Glob, SendMessage, ListAgents
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

Night runner onboard+wiki. Do not stop on a thin passport.

```bash
docs-maintain-project "$PROJECT_CWD"
```

Instructions: `~/.agents/codex/instructions/docs-maintain.md`

Report → `.agents/session-log/DOCS-YYYY-MM-DD.md`.

## Completion (mandatory)

`DONE` if the runner wrote `.agents/session-log/DOCS-YYYY-MM-DD.md` (or skip/partial). Passport stubs are Luna's job on that pass.  
Last line: `DONE <report-path>` or `FAILED <reason>`, then **stop**.
