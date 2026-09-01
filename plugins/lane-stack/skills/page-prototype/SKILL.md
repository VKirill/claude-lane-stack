---
name: page-prototype
description: "Axure-like gray HTML wireframe of one page. Not DESIGN.md, not product Vue. Use when: прототип страницы, вайрфрейм, axure, html mock, кликабельный макет. SKIP: live UI (dev-orchestrator run); tokens (project-design); copy brief only (site-copy-headlines)."
argument-hint: "[info]"
---

# Page prototype

One self-contained HTML file per screen. Gray boxes. Real copy if a brief exists. Open in a browser.

Not a designed page. Not a writer lane. Not Vue.

## Info (print and stop)

If `$ARGUMENTS` is `info`: print the block below **verbatim**, then **stop**.

```text
page-prototype — серый HTML-вайрфрейм, не дизайн.

Диск
<repo>/.agents/prototypes/
  INDEX.md
  site/<slug>/index.html           публичная страница (копирайт / SEO)
  site/<slug>/empty.html           состояние той же страницы
  app/<app>/<slug>/index.html      экран продукта (= apps/<app>)
  flows/<flow>/01-<slug>.html      клик-путь (01, 02, …)

Куда класть (первый матч)
- лендинг / статья / оффер          → site/<slug>/
- кабинет / apps/<имя>              → app/<имя>/<slug>/
- воронка / несколько шагов         → flows/<flow>/NN-<slug>.html
Не плодить copy/ и seo/ — одна URL = одна папка site/.

Источник текста (первый найденный)
1 .agents/copy/pages/<slug>.md
2 .agents/seo/** brief / snapshot той URL
3 одно уточнение у человека — иначе [LABEL]

Кто пишет
copy-lead · seo-specialist · dev-orchestrator (сам, .agents/**)
Субагента нет. Ран / Vue / DESIGN.md — не сюда.

Нельзя
- файлы россыпью в корне prototypes/
- hex из бренда, Tailwind, картинки
- писать в apps/ или src/
```

## Disk

```text
.agents/prototypes/
  INDEX.md
  site/<slug>/index.html
  app/<app>/<slug>/index.html
  flows/<flow>/01-<slug>.html
```

| Ask | Path |
|---|---|
| Публичная страница | `site/<slug>/index.html` |
| Состояние той же (empty / error) | `site/<slug>/<state>.html` |
| Экран продукта | `app/<app>/<slug>/index.html` — `<app>` = folder under `apps/` if it exists |
| Клик-путь | `flows/<flow>/01-<slug>.html`, `02-…` — two digits, same flow folder |

1. `mkdir -p` only the folder you will write. Do not pre-create empty trees.
2. If `INDEX.md` missing, copy `references/INDEX.template.md`.
3. Copy `references/shell.html` into that folder. Fill slots. Do not invent a second CSS language.
4. Add/update the INDEX row (`path` = repo-relative). If a copy brief exists, one-line `prototype:` there.

## MUST

1. Keep the shell: system font, gray `#eee` / `#ccc` boxes, 1px `#999` borders, yellow notes.
2. Every block has a type chip: `HEADER` `NAV` `HERO` `PROOF` `FORM` `LIST` `CTA` `FOOTER` `IMAGE`.
3. One `<h1>`. One primary CTA (verb + object). Image = empty box + label, no URL.
4. Put real strings from the brief. Missing string = `[H1]` / `[CTA]` — do not invent a campaign.
5. Notes (`aside.note`) explain job of the block, not decoration.
6. Links: same page state `./empty.html`; sibling page `../other/index.html`; flow step `./02-pay.html` or `../../site/<slug>/index.html`. No live site URLs unless the brief has them.
7. Extra state = extra file in the **same** folder. No JavaScript. No fourth top-level kind.

## NEVER

- Flat files in `.agents/prototypes/*.html`
- Folders `copy/` or `seo/` (use `site/`)
- DESIGN.md tokens, brand hex, Google fonts, Tailwind, Vue/React
- Files under `apps/`, `src/`, or `public/`
- Stock photos, SVG illustrations, gradients, shadows-as-beauty
- Lorem ipsum paragraphs when a brief already has headlines
- Two primary CTAs / “Learn more”
- `run-init` or a writer lane for this file
