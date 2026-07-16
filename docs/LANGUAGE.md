# Language policy (Claude Lane Stack)

## Rule

| Surface | Language |
|---------|----------|
| **All agent-written project files** | **English only** |
| **Canonical stack docs / skills / agent.md / templates** | **English only** |
| **Chat with the human (PM / orchestrator)** | **Russian** (or user's language) |
| Human may still keep personal notes in RU | Outside agent pipelines |

## What “agent-written files” means

Always English:

- `CLAUDE.md`, `AGENTS.md`, `README.md` agent sections 
- `docs/**` (ARCHITECTURE, decisions, plans, COCOON strategy if agent-authored) 
- `.agents/runs/**` (PLAN, SPEC, STATUS, task YAML, report.md, review.md, MERGE.md) 
- `.agents/todos/**` (README, AGENT.md, meta.yaml titles/descriptions) 
- `PROGRESS.md`, `LESSONS.md`, session-log, DOCS-*.md, BOARD.md 
- Heartbeat notes, commit messages produced by agents (prefer EN)

## Chat

- User speaks Russian → PM answers Russian. 
- When quoting or creating files, PM **writes English** into the repo, then can summarize in Russian. 
- Translation is for the human UI only — **source of truth in git is English**.

## Why

1. Multi-region / multi-tool agents (Claude, Codex, Grok) share one corpus. 
2. English instruction-following for coding agents is more stable. 
3. Human still gets RU dialogue without polluting durable state.

## Enforcement

- `dev-orchestrator` and all lane instructions MUST state this. 
- Onboard / docs-maintain / todos skills MUST emit English. 
- Do not auto-rewrite entire legacy Russian human docs unless asked; new agent output is EN.

## Exceptions

- Legal/marketing copy that is product content for RU users (app UI strings, customer emails) — product locale, not agent ops docs. 
- User explicitly asks for a RU human-facing doc (blog post, client brief) — then that artifact may be RU; still keep CLAUDE/runs/todos in EN.
