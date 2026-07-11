---
name: agent-todos
description: "File-based TODO/ideas board for humans + agent technical notes. Use when user says todo, туду, идея, backlog, запиши, занеси, потом, incubate; or when capturing follow-ups from a discussion without starting a run yet."
---

# Agent TODOs (files only)

**Canon layout:** `~/.agents/docs/TODOS.md`  
**No orchestrator MCP.** No `todo_add` / task CLI for ideas.

## When to use

| User intent | Action |
|-------------|--------|
| Discuss only | Optionally append to open item's README/AGENT if one is active |
| «Занеси в todo / запиши / не забудь» | **Create or update** item folder + INDEX |
| «Делай / реализуй» | Promote → `.agents/runs/<slug>/` (lane-contract), mark todo `ready`→ link `related_runs` |
| «Покажи todo» | Read INDEX + list open items (paths) |
| «Закрой / сделано / не надо» | status done/dropped + INDEX |

## Choose root

```text
PROJECT_TODO_ROOT = <cwd>/.agents/todos     if cwd looks like a project
GLOBAL_TODO_ROOT  = ~/.agents/todos         else or if user says global
```

Project signals: `.git`, `package.json`, `pyproject.toml`, `CLAUDE.md`, `AGENTS.md`.

## Create item (algorithm)

1. Slug: `YYYY-MM-DD-` + kebab 3–6 words from title (ascii translit ok).  
2. Paths:
   - `items/<slug>/README.md`
   - `items/<slug>/AGENT.md`
   - `items/<slug>/meta.yaml`
3. Fill **both** README (human) and AGENT (technical) — never only one.  
4. Rebuild/update `INDEX.md`.  
5. Tell user: **one plain sentence** + path to folder (clickable relative path).

### README.md template (human, RU)

```markdown
# <Короткий заголовок>

## Зачем
…

## Что хотим
- …

## Не сейчас
- …

## Открытые вопросы
- …  # only product/business

## Как понять, что готово
- …

## История
### YYYY-MM-DD
- Обсудили: …
```

### AGENT.md template (technical)

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
- gitnexus / grep notes: …

## Spawn hint (when promoted to run)
- risk: low|medium|high
- lane: agy-frontend | agy-coder | grok
- seed tasks:
  - [ ] …
- verification ideas:
  - …

## Do not
- …
```

### meta.yaml template

See TODOS.md. Always set `created`/`updated` ISO-8601.

## Update existing item

If discussion continues on same idea:

1. Find folder by slug or title match in INDEX.  
2. Append **История** in README.  
3. Merge technical facts into AGENT.md (Context / Hypotheses / Do not).  
4. Bump `updated` + status (often `incubating`).  
5. Refresh INDEX row.

## Capture quality bar

**Human side:** user could re-read in 3 months and know *why* and *what success looks like*.  
**Agent side:** another session could open AGENT.md and start a run without re-asking the same tech questions.

If the chat was shallow, still write what you have; put gaps under **Открытые вопросы** / **Hypotheses**.

## INDEX.md maintenance

After every write:

```markdown
# TODOs — <ProjectName|Global>

| status | priority | id | title |
|--------|----------|-----|--------|
| open | medium | 2026-07-11-foo | Foo |

## Incubating
- …

## Ready to run
- …

## Parked / done (short)
- …
```

Max ~30 open rows visible; older done → short list or `ARCHIVE.md`.

## Inbox (optional fast path)

If user dumps a one-liner and says «потом»:

`inbox/YYYY-MM-DD-slug.md` with 5–10 lines, then either promote to full `items/` same turn or on next «разверни todo».

## Promote to run

When user asks to implement:

1. Ensure AGENT.md has enough Context + Spawn hint (ask only business gaps).  
2. Create `.agents/runs/<slug>/` per FILE-CONTRACT / lane-contract.  
3. Seed `tasks/001-….yaml` from Spawn hint + excerpts.  
4. Set todo `status: ready` or `done` if fully absorbed; set `related_runs: [<slug>]`.  
5. Continue with orchestrator-lanes dispatch.

## Anti-patterns

- ❌ Storing todos only in chat memory  
- ❌ One giant TODO.md without folders  
- ❌ Implementing production code from a todo without a run  
- ❌ Calling orchestrator-mcp / `todo_add`  
- ❌ Secret keys in README/AGENT  
- ❌ English-only wall for a RU-speaking user in README  

## Session start (optional)

If project has `.agents/todos/INDEX.md`, you may show **count** of open/ready (one line), not full dump, unless asked.
