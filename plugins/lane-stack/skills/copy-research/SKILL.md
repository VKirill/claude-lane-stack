---
name: copy-research
description: "Dispatch copy-lead helpers: Tavily, Codex luna/terra, grok/X, OpenCode DeepSeek, Cursor Grok 4.6 medium-fast. Use when: глубокий ресёрч, firecrawl, tavily, сподручные, конкуренты, twitter, язык ЦА. SKIP: SEO SERP (seo-specialist); one URL (WebFetch)."
---

# Copy research

Write notes to `.agents/copy/research/inbox/YYYY-MM-DD-<slug>.md`. Then **you** fill audience/page files and `mv` the note to `used/`. Research ≠ buyer quote. Never one `web.md`.

First load `references/helpers.md` (who runs the CLI). Then `references/search-playbook.md` for query rules.  
Do **not** `npx skills add` unless the human has the key **and** asked. Twitter/OAuth skills: never.

## Who runs what

| Need | Runner |
|---|---|
| Одна страница | You: `WebFetch` |
| Короткий поиск с цитатами / URL | skill **`tavily`** → `/search` |
| Отчёт: рынок / ЦА / ландшафт | skill **`tavily`** `/research` **or** Firecrawl (key) |
| Открытый веб, несколько URL | **Codex `gpt-5.6-luna` + fast** (`terra` if thin) |
| X / Twitter, живой сленг | **grok** CLI |
| Пачка вариантов / дешёвый черновик | **OpenCode** `deepseek-v4-flash` |
| 2–3 сильных угла | **OpenCode** `deepseek-v4-pro` |
| Второй проход с репо | **cursor-agent** `cursor-grok-4.6-medium-fast` |
| Уже в репо | `Agent(Explore)` |
| Неясно, с чего начать | `Agent(general-purpose)` first, then CLI |

Recipes: `references/helpers.md`. Helper writes inbox only. You lift.

## Tavily

Load skill `tavily`. Key: `~/secrets/tavily.env`. Search = `/search`. Cited report = `/research` (ask duration).

## Firecrawl deep-research (report-scale)

Official skill: https://www.skills.sh/firecrawl/firecrawl-workflows/firecrawl-deep-research  
Source: `firecrawl/firecrawl-workflows` · skill `firecrawl-deep-research`. Needs `FIRECRAWL_API_KEY`.

Use **only** when the human wants a cited report (landscape, how the category talks, multi-angle + sources). Not for one URL, top-N, or «найди 3 заголовка».

1. If `FIRECRAWL_API_KEY` is unset → stop. Tell the human to export it. Do not invent sources.
2. If the skill is not installed:

```bash
npx skills add https://github.com/firecrawl/firecrawl-workflows --skill firecrawl-deep-research
```

3. Ask one question if duration is unknown: «Сколько крутить ресёрч?» (их онбординг).
4. Load skill `firecrawl-deep-research`. Output also copy to `research/inbox/YYYY-MM-DD-<slug>.md`.
5. Lift language into `audience.md`. Do not treat report sentences as buyer quotes. Then `mv` the note to `used/`.

## CLI helpers

Load `references/helpers.md` and run that recipe. Do not paste a second copy here.

## After the worker

1. Read the inbox note.
2. Lift **language** into `audience.md` / persona `words_they_use`.
3. Do not paste a tweet as `happy_customer_pattern`.
4. `mv` the note to `research/used/` (noise → `dead/`). Refresh `INDEX.md`.
5. Then headlines / UX as usual.

## NEVER

- Twitter/OAuth/post skills from skill.sh
- Firecrawl deep-research for a single URL or a top-N list
- Firecrawl without `FIRECRAWL_API_KEY`
- `run-init` / writer lanes
- Treat scraped text as a confirmed customer quote
- Append into one `web.md`
- Let a helper edit canon / `locked` files
- Pick a Cursor model other than `cursor-grok-4.6-medium-fast`
