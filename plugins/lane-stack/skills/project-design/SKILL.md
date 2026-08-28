---
name: project-design
description: Lane-stack router for design/brand. Load ui-ux-pro-max. Full DESIGN.md at root and every UI app. Use when user says info, справка, как запускать project-design, lane-stack:project-design info, дизайн, токены, DESIGN.md, brand, UI, баннер, соцсети, or a UI run has no DESIGN.md.
argument-hint: "[info]"
---

# Project design

Load **`ui-ux-pro-max`**. One kit: Google DESIGN.md files. No `MASTER.md`.

## Info (print and stop)

If `$ARGUMENTS` is `info`, or the user says `info` / `справка` / `как запускать` this skill:
print the block below **verbatim** (Russian), then **stop**. Do not extract. Do not spawn `design-lead`.

```text
project-design — роутер дизайна lane-stack

Что делает
- Грузит ui-ux-pro-max (поиск стилей, a11y, стек, brand/, banner-design/).
- Пишет полные Google DESIGN.md: корень + каждый UI-app.
- Не пишет design-system/**/MASTER.md и не вызывает --persist.

Кто пишет файлы
- Агент design-lead (сессия = dev-orchestrator, cwd = проект).
- Онбординг: project-onboarder, если has_ui и DESIGN.md ещё нет.
- Lane writer — только если owns_paths включает DESIGN.md. Иначе match, не invent.

Файлы (все полные, не указатели)
- docs/DESIGN.md — общий бренд, voice, Surfaces (web + social).
- apps/<name>/docs/DESIGN.md — полный файл той поверхности
  (cabinet, marketing, …). Те же секции, что у корня. Токены из кода этого app.

Как открыть эту шпаргалку
- /lane-stack:project-design info
- или: lane-stack:project-design info
- или: project-design справка
- каталог всех процессов: /lane-stack:info

Как запустить работу (новая сессия оркестратора)

1) Весь продукт (сайт + кабинет + остальные UI-apps)
Первичный дизайн-анализ. Spawn design-lead, MODE=extract.
Пройди все UI-apps. Полные файлы в docs/DESIGN.md и apps/<name>/docs/DESIGN.md.
Палитру не выдумывай. Ран не открывай.

2) Одна поверхность + корень
Первичный дизайн-анализ. Spawn design-lead, MODE=extract, APP=cabinet.
Обнови docs/DESIGN.md и apps/cabinet/docs/DESIGN.md. Ран не открывай.

3) Новый продукт, UI ещё нет
Spawn design-lead, MODE=seed. Search --design-system, пиши DESIGN.md.
Не --persist, не MASTER.md.

4) Новая страница в живом UI
«планируем, не запускай». Сверь корневой и app DESIGN.md.
Search --design-system только дыры, вмержи в DESIGN.md этой поверхности.
После «делай» — ран. Writer match DESIGN.md того app.

5) Баннер / соцсети
Load ui-ux-pro-max → brand/ + banner-design/.
Размеры и voice → Surfaces в корневом и marketing DESIGN.md.

UI-ран
- Нет нужного DESIGN.md → сначала design-lead, потом run-init.
- Task read_first: docs/DESIGN.md и apps/<app>/docs/DESIGN.md.
- Не клади DESIGN.md в owns_paths, если исход не токены/доки.

Поиск (локально, без сети)
python3 ~/.agents/skills/ui-ux-pro-max/scripts/search.py "<query>" --domain ux
python3 ~/.agents/skills/ui-ux-pro-max/scripts/search.py "<query>" --design-system -p "Name" -f markdown
python3 ~/.agents/skills/ui-ux-pro-max/scripts/search.py "<query>" --stack nuxtjs

Нельзя
- «см. корень» вместо полного apps/*/docs/DESIGN.md
- Claude Plan mode и ~/.claude/plans/
- выдумывать hex при MODE=extract
```

## Work (not info)

- Existing UI: full extract into `docs/DESIGN.md` **and** `apps/<name>/docs/DESIGN.md` for each UI app.
- App files are complete (same sections as root), not a one-line pointer.
- New page: `--design-system` then merge into the DESIGN.md of that surface. No `--persist`.
- Social / voice: `brand/` + `banner-design/` → Surfaces on root and on marketing/social apps.
- Writers: match the DESIGN.md of the app they edit (`apps/cabinet/docs/DESIGN.md` in cabinet).
- Orchestrator: missing any required DESIGN.md → `design-lead` before `run-init`.
