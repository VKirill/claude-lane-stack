# Project memory pack (2026-07)

Files every serious agent project should keep so a cold session is useful in minutes.

| File | Purpose | Who writes |
|------|---------|------------|
| `AGENTS.md` / `CLAUDE.md` | Hard rules + non-obvious gotchas | Human + onboard / rare agent edits |
| `PROGRESS.md` | Now / blocked / next / last verify | Agents after work; human anytime |
| `LESSONS.md` | Mistakes → do/don't | Agents after corrections |
| `docs/decisions.md` | ADR-light durable choices | Human or agent on big forks |
| `.agents/onboard.scenario.yaml` | minimal\|full + fast\|deep + score | `project-onboard` |
| `.agents/routing.profile.yaml` | which CLIs / lanes | `agents-doctor --apply` |
| `.agents/session-log/` | Auto handoff evidence (files/shell/git) | Hooks |
| `.agents/agent-notes/OPEN.md` | Open debt from code TODOs | Hooks + agents |
| `.agents/todos/` | Ideas backlog | Humans + PM agents |
| `.agents/runs/` | Task contracts + reports | Orchestrator + lanes |
| `.agents/runs/BOARD.md` | Live multi-run board | `run-board` |
| `docs/` wiki (if any) | Architecture truth | Humans + wiki pipeline / docs-maintain |

**Solo:** orchestrator auto-merges worktrees to `main` (`wt-merge-main`). See `SOLO-ORCHESTRATION.md`.  
**Language:** all of the above agent-written files are **English** (`LANGUAGE.md`).

## Init a repo

```bash
export PATH="$HOME/.agents/bin:$PATH"
project-memory-init /path/to/repo
# full passport (preferred first time):
project-onboard /path/to/repo          # or /project-onboard in Claude
# force forensic:
project-onboard /path/to/repo --deep
```

## Skills

- `project-memory` — when to update which file after a task/session
- `project-onboard` — dual scenario + depth passport
- `resume-project` — cold start (`resume-project .`)
- `agent-todos` — ideas board
- `lane-contract` / `orchestrator-lanes` — runs + solo merge + lane-bg

## Cold start / night audit

```bash
~/.agents/bin/resume-project /path/to/repo
~/.agents/bin/night-audit /path/to/repo
# → .agents/session-log/AUDIT-YYYY-MM-DD.md
```

## Community names

session ledger · agent handoff log · coding journal · ADR · agent notes · progress file · lessons log
