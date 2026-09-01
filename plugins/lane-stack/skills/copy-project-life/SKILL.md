---
name: copy-project-life
description: "Карта копирайта сайта: шаблоны и цепочка файлов в .agents/copy/. Агент copy-lead. Use when copy, копирайт, анамнез, buyer persona, заголовок лендинга, site-copy. SKIP: SEO-ключи (seo-copywriting); код и DESIGN.md."
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
  INDEX.md                  доска статусов
  ANAMNESIS.md
  audience.md
  buyer-personas/p1.md
  voice.md
  pages/<slug>.md
  research/inbox/           сырой ресёрч (дата-slug)
  research/used/            уже подняли в audience/pages
  research/dead/            шум

status: unknown → draft → fillable → approved → locked
locked = не переписывать. on_site (страницы) ≠ status.

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
5 серый HTML           → page-prototype  (.agents/prototypes/site/<slug>/index.html)

Агент
- copy-lead  /  LANE_PM_AGENT=copy-lead lane-pm
- claude --agent copy-lead
- стиль /config → copywriter (только в этой сессии; не делать дефолтом проекта)
- профессий в модели нет — шляпы в craft.md

Нельзя
- писать H1 без audience.md
- выдумывать цитаты
- дублировать DESIGN.md в voice.md
- трогать locked
- писать весь ресёрч в один web.md
```

## MUST — seed + first interview

1. `mkdir -p .agents/copy/buyer-personas .agents/copy/pages .agents/copy/research/inbox .agents/copy/research/used .agents/copy/research/dead`
2. If a file is missing, copy the matching template from this skill’s `references/`:

| Disk | Template |
|---|---|
| `INDEX.md` | `INDEX.template.md` |
| `ANAMNESIS.md` | `ANAMNESIS.template.md` |
| `audience.md` | `audience.template.md` |
| `buyer-personas/p1.md` | `buyer-persona.template.md` |
| `voice.md` | `voice.template.md` |
| `pages/<slug>.md` | `page-brief.template.md` |

Move leftover dumps out of the research root (once):

```bash
d=.agents/copy/research
mkdir -p "$d/inbox"
for f in web.md web.json x.md deep.md deep.json deep-job.json; do
  [ -f "$d/$f" ] && mv "$d/$f" "$d/inbox/$(date +%F)-$f"
done
```

3. First full analysis: `product:` empty **or** no `.agents/copy/` → load `references/first-interview.md`. Ask 2–3 questions per turn. Write answers after each batch. Do not re-ask what the site/passport already answers.
4. Fill only known fields. Unknown stays `unknown`.
5. After offer + audience are fillable: `site-copy-audience`. If the human asked full analysis: then headlines → ux. Wireframe only if they asked: `page-prototype`. Chat Russian. Keys English.
6. After any status change: update `INDEX.md` and `updated:`. Do not rewrite `locked`.

## NEVER

- Invent buyer quotes
- Edit product Vue/CSS (`.agents/prototypes/` gray HTML is OK)
- Start a run
- Rewrite a `locked` file
- Append research into one `web.md`
