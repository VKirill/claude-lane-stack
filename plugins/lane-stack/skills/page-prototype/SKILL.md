---
name: page-prototype
description: "Axure-like gray HTML wireframe of one page. Shared proto.css/js: slider, tabs, accordion, modal, toggle. Use when: прототип страницы, вайрфрейм, axure, html mock, кликабельный макет, слайдер. SKIP: live UI (dev-orchestrator run); tokens (project-design); copy brief only (site-copy-headlines)."
argument-hint: "[info]"
---

# Page prototype

One HTML file per screen + shared kit. Gray boxes. Real copy if a brief exists. Open in a browser.

Not a designed page. Not a writer lane. Not Vue. Not npm.

## Info (print and stop)

If `$ARGUMENTS` is `info`: print the block below **verbatim**, then **stop**.

```text
page-prototype — серый HTML-вайрфрейм + общий kit.

Диск
<repo>/.agents/prototypes/
  _kit/proto.css  proto.js         один раз, не править под страницу
  INDEX.md
  site/<slug>/index.html           публичная страница
  site/<slug>/empty.html
  app/<app>/<slug>/index.html      экран продукта (= apps/<app>)
  flows/<flow>/01-<slug>.html

Куда класть
- лендинг / статья / оффер  → site/<slug>/
- кабинет / apps/<имя>      → app/<имя>/<slug>/
- воронка                   → flows/<flow>/NN-<slug>.html
Не плодить copy/ и seo/.

Kit (только эти виджеты)
slider · tabs · accordion · toggle · modal · mobile menu
Разметка: data-proto-* как в references/shell.html
href kit: site/ и flows/ → ../../_kit/ · app/ → ../../../_kit/
Превью 24ч: html.vechkasov.pro
  один файл:  publish.py --one
  пачка:      publish.py --bundle  (index.html + style.css + script.js + _kit)
  повтор:     тот же URL из .host.json · новая страница — новая папка · --new = новый URL

Источник текста
1 .agents/copy/pages/<slug>.md
2 .agents/seo/** brief
3 иначе [LABEL]

Нельзя
- россыпь html в корне · hex бренда · Tailwind · Vue · npm/CDN
- своя анимация вместо proto.css
```

## Disk

```text
.agents/prototypes/
  _kit/proto.css
  _kit/proto.js
  INDEX.md
  site/<slug>/index.html
```

| Ask | Path |
|---|---|
| Публичная страница | `site/<slug>/index.html` |
| Состояние | `site/<slug>/<state>.html` |
| Экран продукта | `app/<app>/<slug>/index.html` |
| Клик-путь | `flows/<flow>/01-<slug>.html` |

1. If `_kit/` missing: copy `references/kit/proto.css` and `proto.js` there. Do not edit the kit per page.
2. If `INDEX.md` missing: copy `references/INDEX.template.md`.
3. Copy `references/shell.html` into the page folder. Fix the two `../../_kit/` paths if this is `app/` (`../../../_kit/`). Fill slots. Delete unused widgets. Do not invent a second CSS/JS stack.
4. Update INDEX. If a copy brief exists, one-line `prototype:`.
5. If the human asked to **open / share / preview**, publish to `https://html.vechkasov.pro` (24h, then gone; disk stays).
   Same page folder → same URL (script writes `.host.json` and sends `id`). New slug/folder → new POST, new URL. Expired id → new URL, rewrite `.host.json`. `--new` only if they asked for a fresh link.

```bash
# one HTML (kit inlined) — short page, no extra css/js
python3 <this-skill>/references/publish.py --one .agents/prototypes/site/<slug>/index.html

# separate files so the browser loads CSS/JS like a real site
python3 <this-skill>/references/publish.py --bundle .agents/prototypes/site/<slug>/index.html

# force a new URL (do not reuse .host.json)
python3 <this-skill>/references/publish.py --new .agents/prototypes/site/<slug>/index.html
```

No flag: `--bundle` if the folder has `style.css` / `script.js` / extra `.css`/`.js`, else `--one`.

**Bundle layout on the host** (`POST /api/pages` `{"files":{...}}`):

| Disk | Uploaded as |
|---|---|
| `index.html` | `index.html` (kit hrefs rewritten to `_kit/proto.css` / `_kit/proto.js`) |
| `style.css` | `style.css` — page-local extras only |
| `script.js` | `script.js` |
| `_kit/proto.css` `proto.js` | `_kit/…` if the HTML still links them |

Complex page: put extras in that folder as `style.css` / `script.js` (or more `.css`/`.js` names). Do not invent Vue. Kit stays the widget runtime.

API without the script: `{"html":"<html>…"}` or `{"files":{"index.html":"…","style.css":"…","script.js":"…"}}`. Update: add `"id"` from that page’s `.host.json`. Host: `HTML_HOST_BASE` (default `https://html.vechkasov.pro`). Optional `HTML_HOST_TOKEN`.
Write `url` + `files` into INDEX notes. Host down → say so, keep local files. Do not commit `.host.json` if the repo treats it as local.

## Widgets

| Need | Markup |
|---|---|
| Slider | `[data-proto-slider]` + `.proto-slider-track` + `[data-proto-prev]` / `[data-proto-next]` + `.proto-dots` |
| Tabs | `[data-proto-tabs]` + `[role=tab]` / `[role=tabpanel]` |
| Accordion | `[data-proto-acc]` (add `data-proto-many` to keep several open) |
| Show/hide | `.proto-toggle` + `[data-proto-toggle]` + `[data-proto-panel]` |
| Modal | `.proto-modal#id` + `[data-proto-open="id"]` + `[data-proto-close]` |
| Narrow nav | `[data-proto-menu-btn="[data-proto-menu]"]` + `[data-proto-menu]` |

Image = `.img` gray box + label, no URL. Motion = kit fade / slide only.

## MUST

1. Link the kit. No `<style>` of your own except a one-off layout gap.
2. Chips on blocks: `HEADER` `HERO` `SLIDER` `TABS` `ACCORDION` `TOGGLE` `FORM` `MODAL` `FOOTER` `IMAGE`.
3. One `<h1>`. One primary CTA (verb + object).
4. Brief strings when they exist. Else `[H1]` / `[CTA]`.
5. Notes (`aside.note`) = job of the block.
6. Links: `./empty.html`, `../other/index.html`, `./02-pay.html`. No live URLs unless the brief has them.
7. Extra state = extra file in the same folder.

## NEVER

- Flat `.agents/prototypes/*.html`
- Folders `copy/` or `seo/`
- DESIGN.md tokens, brand hex, Google fonts, Tailwind, Vue/React, npm, CDN (Swiper, jQuery, Alpine)
- A second `proto.css` / inline animation kit
- Files under `apps/`, `src/`, `public/`
- Stock photos, SVG art, gradients
- Lorem when a brief already has headlines
- Two primary CTAs / “Learn more”
- `run-init` or a writer lane
- Secrets or `.env` values inside published HTML
