---
description: Bootstrap project for Claude Lane Stack — CLAUDE.md, AGENTS.md pointer, memory, doctor
---

Запусти онбординг репозитория (cwd или $ARGUMENTS):

```bash
export PATH="$HOME/.agents/bin:$PATH"
project-onboard ${ARGUMENTS:-.}
```

Затем skill `project-onboard`: проверь результат, коротко по-русски что создано, profile doctor, напомни:

- execution → `.agents/runs/`
- strategy (COCOON и т.п.) → `docs/plans/`
- AGENTS.md = pointer на CLAUDE.md
- karpathy-guidelines на любой нетривиальный код

Не раздувай CLAUDE.md.