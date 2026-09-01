# Search playbook (copy)

Load before any web/X research. Distilled from popular skills.sh research skills (Firecrawl CLI, Firecrawl deep-research, Tavily research/search). We do **not** vendor those repos.

## Pick a scenario

| Human said | Scenario | Runner |
|---|---|---|
| «открой этот URL» | one page | `WebFetch` |
| «что пишут на главной у X» | few URLs | Codex luna fast **or** cursor-grok-4.6-medium-fast |
| «как говорят / сленг / твиты» | social language | grok `-p` |
| «обзор рынка / ЦА / ландшафт, отчёт» | report-scale | skill `tavily` `/research` **or** `firecrawl-deep-research` (key) |
| «найди 3 примера» | short search | skill `tavily` `/search`. **Not** `/research` |

Escalate, do not jump:

```text
search / WebSearch  →  scrape one URL  →  map a site  →  crawl a section  →  deep-research report
```

Deep-research only after the human wants a **cited report** and a time budget.

## How to query

From Tavily search skill (method, not their CLI):

- Query = search string, **< 400 chars**, not a prompt-essay.
- Split one fat question into 2–4 sub-queries.
- Prefer recent language: add year / «отзывы» / «жалобы» when hunting voice.
- Domain filter when you already know the site (`site:example.com`).
- Do not pull raw HTML into chat. One file per query: `.agents/copy/research/inbox/YYYY-MM-DD-<slug>.md`.

## What to keep

Each note file:

- claim
- URL
- date if visible
- language snippet (their words)

Empty field = skip. Invented slang = delete.

## skills.sh we may load (not shipped)

| Skill | Installs (2026-08) | Key | When |
|---|---|---|---|
| `firecrawl/cli` → `firecrawl` | ~100k | Firecrawl (free tier exists) | scrape / map / crawl |
| `firecrawl-deep-research` | ~34k | `FIRECRAWL_API_KEY` | report-scale only |
| `tavily-research` (skills.sh) | ~17k | skip | we ship skill `tavily` (REST) |
| `tavily-dynamic-search` | ~8k | skip | same |

Skip: Twitter/OAuth/post skills (`x-research-skill` ~340). Grok covers X.

Shipped: skill `tavily` (`~/secrets/tavily.env`). Do not `npx skills add` Tavily packs.

Install Firecrawl skills only when the human has that key and asked:

```bash
npx skills add https://github.com/firecrawl/cli --skill firecrawl
npx skills add https://github.com/firecrawl/firecrawl-workflows --skill firecrawl-deep-research
```
