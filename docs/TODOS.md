# File-based TODOs / ideas (no orchestrator MCP)

Human-readable ideas + agent technical memory.

**Language: all todo files English only** (see LANGUAGE.md). Chat may be Russian. Not a run queue (runs live under `.agents/runs/`).

## Where

| Scope | Path |
|-------|------|
| **Project** (default when cwd is a project) | `<project>/.agents/todos/` |
| **Global** (cross-project / no project) | `~/.agents/todos/` |

Prefer **project** if `package.json` / `.git` / `CLAUDE.md` present. Use **global** when user says «глобально», «вообще», or cwd is home.

## Layout

```text
.agents/todos/                    # or ~/.agents/todos/
  INDEX.md                        # human board (always maintain)
  inbox/
    YYYY-MM-DD-short-slug.md      # quick capture (optional)
  items/
    YYYY-MM-DD-short-slug/
      README.md                   # human-oriented, English (chat may be RU)
      AGENT.md                    # technical, English
      meta.yaml                   # machine fields
      links.md                    # optional: related runs, PRs, URLs
```

## meta.yaml

```yaml
id: 2026-07-11-subscription-tz
title: "Часовой пояс в дате подписки"
created: 2026-07-11T12:00:00+03:00
updated: 2026-07-11T12:00:00+03:00
status: open                      # open | incubating | ready | parked | done | dropped
priority: medium                  # low | medium | high
scope: project                    # project | global
project: selfystudio              # folder name or abs path
tags: [billing, i18n, ux]
source: chat                      # chat | user-file | run-followup
related_runs: []                  # .agents/runs/<slug> if spawned later
owner: user
```

## README.md (human)

Sections (always, in Russian, plain language):

1. **Зачем** — one paragraph  
2. **Что хотим** — bullets, user-visible outcomes  
3. **Не сейчас** — out of scope / parked ideas  
4. **Открытые вопросы** — only business/product  
5. **Как проверить, что готово** — observable  
6. **История** — dated notes of discussion turns  

No jargon unless user uses it first.

## AGENT.md (agent)

Sections (always, technical, EN or RU ok):

1. **Intent** — compressed goal  
2. **Context** — files, modules, symbols (paths)  
3. **Hypotheses** — technical options considered  
4. **Constraints** — stack, invariants, risks  
5. **Suggested approach** — if any (not binding)  
6. **Discovery notes** — gitnexus hits, links to code  
7. **Spawn hint** — if promoted to run: suggested `risk`, `lane`, seed task YAML bullets  
8. **Do not** — traps  

## INDEX.md

Keep short:

```markdown
# TODOs — <project or Global>

| status | priority | id | title |
|--------|----------|-----|--------|
| open | high | 2026-07-11-… | … |

## Recently done
- …
```

## Triggers (user language)

Create/update item when user says approximately:

- «занеси в todo / туду / идеи»  
- «запиши мысль»  
- «потом сделаем»  
- «не теряй»  
- «incubate / backlog»  

Promote to **run** when user says «делай / реализуй / в работу» → create `.agents/runs/<slug>/` from AGENT.md + README (orchestrator-lanes).

## Status meanings

| status | meaning |
|--------|---------|
| open | captured, not refined |
| incubating | discussing, AGENT.md growing |
| ready | clear enough to spawn a run |
| parked | explicit later / blocked on product |
| done | shipped or rejected with note |
| dropped | won't do |

## Rules

- One idea = one folder. Don't dump everything into INDEX only.  
- Update `updated` + INDEX on every meaningful change.  
- Never put secrets.  
- Don't implement production code from a TODO alone — spawn a **run** first.  
- Human README and agent AGENT.md stay dual: never merge into one wall of text.
