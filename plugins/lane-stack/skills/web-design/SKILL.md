---
name: web-design
description: "Lane-stack web-designer router. Taste/slop review, layout rules, impeccable structure checks. Routes audits, clickable wireframes and branded mockups to design-lead. Use when: веб-дизайнер, UI слоп, нейрослоп дизайн, ревью экрана, прототип, цветной макет, верстка, иерархия, отступы, critique, audit UI, taste-skill, impeccable. SKIP: tokens-only DESIGN.md extract (project-design); live Vue/CSS (writer run); UX copy (copy-lead); SEO (seo-specialist)."
argument-hint: "[info]"
---

# Web design

Router. Role: web designer. Does not ship product UI.

Canon on disk is still `docs/DESIGN.md` + `apps/<app>/docs/DESIGN.md`.
This skill decides **which design skill to load** and **who may write**.

## Info (print and stop)

If `$ARGUMENTS` is `info`, or the user says `info` / `справка` / `как запускать` this skill:
print the block below **verbatim** (Russian), then **stop**. Do not spawn. Do not edit Vue.

```text
web-design — веб-дизайнер lane-stack. Роутер, не верстальщик.

Что делает
- Ревью экрана на визуальный слоп (taste) и структуру (impeccable).
- Инструкции по вёрстке для writer (references/layout.md).
- Don'ts в DESIGN.md. Серый прототип — page-prototype, цветной макет — MODE=mockup.

Кто пишет
- Аудит / канон: design-lead (MODE=audit|extract|seed). Продуктовый код не трогает.
- Прототип / цветной макет: design-lead (MODE=prototype|mockup), .agents/prototypes/.
- Живой сайт/кабинет: UI-ран, writer. read_first: DESIGN.md + этот скилл.
- Ты говоришь оркестратору. Оркестратор сам не верстает.

Маршрут
1) Живой UI без DESIGN.md     → project-design (design-lead extract/seed)
2) Слоп / «проверь дизайн»    → design-taste + impeccable-ui critique
                                 design-lead MODE=audit
3) a11y / адаптив / состояния → impeccable-ui audit (отчёт)
                                 чинить — ран
4) Серая структура / клики    → design-lead MODE=prototype + page-prototype
   Цветной HTML-макет        → design-lead MODE=mockup, отдельная visual/
5) Токены / бренд / баннер    → project-design + ui-ux-pro-max
6) Тексты кнопок / ошибки     → copy-lead (impeccable clarify)

Нельзя
- Продуктовый Vue/CSS из design-lead или оркестратора
- npx impeccable install, хуки, PRODUCT.md
- 23 слэш-команды impeccable в ~/.claude
- менять палитру в обход DESIGN.md

Шпаргалка: /lane-stack:web-design info
Каталог: /lane-stack:info
```

## Work (not info)

1. Apply only the skills needed for the selected mode. Do not load every reference.
   As design-lead, execute the assigned mode yourself; never spawn yourself or browser-qa.
   The spawning steps below are for the parent orchestrator.
2. Before product implementation, missing `DESIGN.md` → `project-design`.
   A gray prototype does not need a brand pack. For an isolated mockup without one,
   document a provisional direction; do not silently establish canonical tokens.
3. Review: spawn **design-lead** `MODE=audit` `APP=<surface>`. Live click / viewports: spawn **browser-qa**. Output (audit): Don'ts in that app's `DESIGN.md` + `.agents/session-log/DESIGN-AUDIT-YYYY-MM-DD.md`. Output (QA): `.agents/qa/<slug>/REPORT.md`.
4. After the human says **«делай»**: open a run. Writer `read_first`:
   - `docs/DESIGN.md`
   - `apps/<app>/docs/DESIGN.md`
   - this skill
   - `design-taste`
   - `impeccable-ui`
   - `references/layout.md` next to this file
5. Prototype/mockup: assign **design-lead** `MODE=prototype|mockup` with brief,
   slug/surface and references. Follow [designer-workflow](references/designer-workflow.md);
   gray kit rules apply only to prototype. Browser evidence comes from the parent
   through browser-qa. Live product edits still require a writer run.
6. Copy / SEO / tokens-only extract: other skills. See SKIP in the description.

## NEVER

- Product Vue / TS / CSS from this skill or from `design-lead`.
- `PRODUCT.md`, Impeccable edit-hooks, `npx impeccable install`.
- Invent hex when `DESIGN.md` already has tokens.
- Treat Russian text slop as this skill (`ru-check` / `copy-lead`).

## API Reference

| Need | Read |
|---|---|
| Brief, prototype/mockup scope, handoff and checks | [Designer workflow](references/designer-workflow.md) |
| Motion/gestures, shadows, a11y/adaptation; selection of ten upstream skills | [Specialist checks](references/specialist-checks.md) |
| Product writer layout guidance | [Layout rules](references/layout.md) |
