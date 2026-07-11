---
description: Onboard project — Codex gpt-5.6-sol xhigh fills CLAUDE.md, docs, lane stack files
---

Онбординг репозитория делает **только Codex** (`gpt-5.6-sol` + `xhigh`), не AGY/Grok.

1. `PROJECT_CWD` = текущий cwd или путь из `$ARGUMENTS`
2. Spawn **Agent → codex-onboarder** with:

```text
PROJECT_CWD: <abs>
ARTIFACT_DIR: <abs>/.agents/runs/_onboard/artifacts/001
FORCE: 0
```

3. After report: short RU — что создано, profile doctor, gaps для человека.
4. Do **not** implement features in this command.

If codex missing: fall back to `project-onboard` shell script only and warn.
