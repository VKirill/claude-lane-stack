---
name: agent-todos
description: "File-based TODO/ideas board for humans + agent technical notes. Use when user says todo, туду, идея, backlog, запиши, занеси, потом, incubate; or when capturing follow-ups from a discussion without starting a run yet."
---

# Agent TODOs (files only)

**Canon layout:** `~/.agents/docs/TODOS.md`  
**Language:** **all todo files in English** (README, AGENT.md, meta, INDEX). Chat with the user may be Russian — summarize in RU, write EN to disk.  
See `~/.agents/docs/LANGUAGE.md`.  
**No orchestrator MCP.** No `todo_add` / task CLI for ideas.

## When to use

| User intent | Action |
|-------------|--------|
| Discuss only | Optionally append to open item README/AGENT if active |
| «Занеси в todo / запиши / не забудь» | **Create or update** item folder + INDEX (**English body**) |
| «Делай / реализуй» | Promote → `.agents/runs/<slug>/` (lane-contract), link `related_runs` |
| «Покажи todo» | Read INDEX + list open items; explain in **Russian** if user speaks RU |
| «Закрой / сделано / не надо» | status done/dropped + INDEX |

## Choose root

```text
PROJECT_TODO_ROOT = <cwd>/.agents/todos     if project
GLOBAL_TODO_ROOT  = ~/.agents/todos         else or user says global
```

## Create item

1. Slug: `YYYY-MM-DD-` + kebab 3–6 words from title (**ASCII**).  
2. Paths: `items/<slug>/README.md`, `AGENT.md`, `meta.yaml`  
3. Fill **both** README and AGENT in **English**.  
4. Update `INDEX.md` (English titles).  
5. Tell user in **Russian** one sentence + path.

### README.md (human-oriented, **English**)

```markdown
# <Short title>

## Why
…

## What we want
- …

## Not now
- …

## Open questions
- …  # product/business only

## Done when
- …

## History
### YYYY-MM-DD
- Discussed: …
```

### AGENT.md (technical, **English**)

```markdown
# Agent notes — <slug>

## Intent
…

## Context
- paths: …
- symbols: …
- related systems: …

## Hypotheses
1. …

## Constraints / risks
- …

## Suggested approach (non-binding)
1. …

## Discovery
- …

## Spawn hint (when promoted to run)
- risk: low|medium|high
- lane: agy-frontend | agy-coder | grok | codex
- seed tasks:
  - [ ] …
- verification ideas:
  - …

## Do not
- …
```

### meta.yaml

English `title` / fields. ISO-8601 dates. See TODOS.md.

## Update existing

Append **History** in README; merge tech into AGENT.md; bump `updated`; refresh INDEX.

## Capture quality

Human side: re-read in 3 months, know *why* and success criteria.  
Agent side: another session can start a run from AGENT.md alone.

## Promote to run

Per FILE-CONTRACT / lane-contract. Task YAML **English**.

## Anti-patterns

- ❌ Chat-only todos  
- ❌ One giant TODO.md without folders  
- ❌ Production code without a run  
- ❌ Orchestrator MCP / `todo_add`  
- ❌ Secrets in README/AGENT  
- ❌ **Russian (or any non-EN) as the durable file language** for todos/runs  

## Session start

Optional one-line count of open/ready in Russian; files stay English.
