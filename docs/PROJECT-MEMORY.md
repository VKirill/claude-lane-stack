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
| `.agents/findings/` | Canonical typed review findings, including prior-programmer context | `night-review` |
| `.agents/night-review/checkpoint.json` | Last completely reviewed source boundary | `night-review` |
| `.agents/runs/<slug>/night-fix-state.json` | Resumable dispatch/verify/re-review state | `night-fix-runner` |
| `.agents/runs/<slug>/artifacts/<task>/review.json` | Identity-bound Codex re-review receipt | `night-review-engine` |
| `.agents/runs/<slug>/artifacts/<task>/attempts/<n>/runtime.json` | Sanitized Grok protocol/runtime receipt | `lane-session` |
| `.agents/runs/<slug>/artifacts/<task>/outcome.json` | CLI-agnostic result manifest (exit_status, failure_class, files_changed) for supervisors | `run-controller` |
| `.agents/night-fix-current.json` | Pointer to current/last repair state | `night-fix-runner` |
| `.agents/todos/` | Ideas backlog | Humans + PM agents |
| `.agents/runs/` | Immutable task specs + machine receipts + reports | Orchestrator + lanes |
| `.agents/runs/BOARD.md` | Generated multi-run board | `run-board` |
| `docs/` wiki (if any) | Architecture truth | Humans + wiki pipeline / docs-maintain |

**Solo:** orchestrator auto-merges worktrees to `main` (`wt-merge-main`). See `SOLO-ORCHESTRATION.md`.  
`run-finalize` applies declared PROGRESS/BOARD/OPEN updates after merge and
records them in `finalize.json`; it never guesses which checklist lines are stale.
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
~/.agents/bin/night-shift /path/to/repo
# → typed findings + optional isolated Grok repair run
```

Review observations must not remain only in a transcript. A concrete or
systemic defect is stored once under `.agents/findings/` and linked from its
daily report, OPEN projection, TODO, generated fix task, and closure receipt.
This makes the next reviewer start from prior evidence instead of rediscovering
the same failure.

## Community names

session ledger · agent handoff log · coding journal · ADR · agent notes · progress file · lessons log
