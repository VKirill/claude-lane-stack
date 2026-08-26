# Todos — formats and rules

Ideas backlog. Not a run queue (runs live under `.agents/runs/`).
Canon layout notes: `~/.agents/docs/TODOS.md`.

## Create item

1. Slug: `YYYY-MM-DD-` + kebab 3–6 words from title (**ASCII**).
2. Files: `items/<slug>/README.md`, `AGENT.md`, `meta.yaml`. Fill **both**
   README and AGENT in English.
3. Update `INDEX.md`, tell user in Russian one sentence + path.

Optional: `inbox/<slug>.md` for a one-line capture you will promote the
same day; `links.md` inside an item for PRs/URLs.

## README.md (human-oriented)

```markdown
# <Short title>

## Why
…

## What we want
- …

## Not now
- …

## Open questions
- … # product/business only

## Done when
- …

## History
### YYYY-MM-DD
- Discussed: …
```

## AGENT.md (technical — another session must be able to start a run from it alone)

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
- lane: kimi | qwen | agy | grok | codex
- seed tasks:
  - [ ] …
- verification ideas:
  - …

## Do not
- …
```

## meta.yaml

```yaml
id: 2026-08-26-subscription-tz
title: "Subscription date timezone"
created: 2026-08-26T12:00:00+03:00
updated: 2026-08-26T12:00:00+03:00
status: open          # open | incubating | ready | parked | done | dropped
priority: medium      # low | medium | high
scope: project        # project | global
project: <folder name>
tags: []
source: chat          # chat | user-file | run-followup
related_runs: []      # .agents/runs/<slug> if spawned later
owner: user
```

## INDEX.md

```markdown
# TODOs — <project or Global>

| status | priority | id | title |
|--------|----------|----|-------|
| open | high | 2026-08-26-… | … |

## Recently done
- …
```

## Statuses

open (captured) → incubating (discussing, AGENT.md growing) → ready (clear
enough to plan/run) → done | dropped. `parked` = explicit later.

«Закрой / сделано» → `done`. «Не надо» → `dropped`. Bump `updated` + INDEX.

## Rules

- One idea = one folder; INDEX is only a thin board.
- Update `updated` + INDEX on every meaningful change; append History, don't
  rewrite it.
- Promote: «делай» → plan (if multi-step) or straight to run; set
  `related_runs`, status `ready`/`done`.
- Capture quality bar: human side readable in 3 months (why + success
  criteria); agent side sufficient to start work without the chat.
- No orchestrator MCP / `todo_add`.
