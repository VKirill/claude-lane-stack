---
name: copy-project-life
description: "Карта копирайта сайта: шаблоны и цепочка файлов в .agents/copy/. Use when copy, копирайт, анамнез, buyer persona, заголовок лендинга, site-copy. SKIP: SEO-ключи (seo-copywriting); код и DESIGN.md."
argument-hint: "[info]"
---

# Copy project life

Templates live next to this file: `references/*.template.md`.
Copy them onto disk. Do not invent a second layout.

## Info (print and stop)

If `$ARGUMENTS` is `info`: print the block below **verbatim**, then **stop**.

```text
copy-project-life — файлы копирайта. Не SEO и не код.

Диск (шаблоны из references/)
<repo>/.agents/copy/
  ANAMNESIS.md
  audience.md
  buyer-personas/p1.md
  voice.md
  pages/<slug>.md

Первый полный анализ (нет .agents/copy/ или пустой product)
1 скопировать шаблоны
2 опрос пачками по 2–3 вопроса — references/first-interview.md
   оффер → ЦА → персона/доказательства
3 ответы сразу в файлы; «не знаю» = unknown
4 потом audience → headlines → ux
Без оффера H1 не писать.

Цепочка (повторный заход)
1 ANAMNESIS   → site-copy-audience
2 audience + персоны → site-copy-audience
3 pages/<slug> заголовки → site-copy-headlines
4 pages/<slug> UI      → site-copy-ux

Нельзя
- писать H1 без audience.md
- выдумывать цитаты
- дублировать DESIGN.md в voice.md
```

## MUST — seed + first interview

1. `mkdir -p .agents/copy/buyer-personas .agents/copy/pages`
2. If a file is missing, copy the matching template from this skill’s `references/`:

| Disk | Template |
|---|---|
| `ANAMNESIS.md` | `ANAMNESIS.template.md` |
| `audience.md` | `audience.template.md` |
| `buyer-personas/p1.md` | `buyer-persona.template.md` |
| `voice.md` | `voice.template.md` |
| `pages/<slug>.md` | `page-brief.template.md` |

3. First full analysis: `product:` empty **or** no `.agents/copy/` → load `references/first-interview.md`. Ask 2–3 questions per turn. Write answers after each batch. Do not re-ask what the site/passport already answers.
4. Fill only known fields. Unknown stays `unknown`.
5. After offer + audience are fillable: `site-copy-audience`. If the human asked full analysis: then headlines → ux. Chat Russian. Keys English.

## NEVER

- Invent buyer quotes
- Edit product Vue/CSS
- Start a run
