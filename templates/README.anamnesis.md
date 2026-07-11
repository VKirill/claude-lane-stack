# {{PROJECT_NAME}}

## One-liner

What this product does for the end user (1–2 sentences).

## Current focus (agents: read first)

- See **[PROGRESS.md](./PROGRESS.md)** for Now / Blocked / Next.
- Hot areas this week: …
- Do not touch without asking: …

## Product & domain

- Primary users / jobs-to-be-done  
- Important domain terms (or → `docs/` glossary if any)

## Stack & layout

- **Stack:** …  
- **Top-level:**

```
apps/   …
packages/ …
docs/   architecture, plans, decisions
.agents/  runs (execution), todos (ideas)
```

## For coding agents (anamnesis)

1. Read **[CLAUDE.md](./CLAUDE.md)** — invariants, verify commands, Lane Stack rules.  
2. Architecture map → **[docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)**.  
3. Active implementation → `.agents/runs/` (not `docs/plans/`).  
4. Strategy / SEO / long plans → `docs/plans/` — promote to a run when implementing.  
5. Discipline: skill `karpathy-guidelines` on non-trivial code.  
6. Cold start: `resume-project .` or `/resume-project`.

## How to run (humans)

```bash
# install / dev / test — fill from package manifests
```

## Links

- Decisions: `docs/decisions.md`  
- Deployment: `docs/deployment.md` (if any)  
- Claude Lane Stack: PM `claude --agent dev-orchestrator`
