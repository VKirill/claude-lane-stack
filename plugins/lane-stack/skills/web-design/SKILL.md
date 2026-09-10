---
name: web-design
description: "Lane-stack web-designer router. Taste/slop review, layout rules, impeccable structure checks. Routes to design-taste, impeccable-ui, project-design, page-prototype. Use when: веб-дизайнер, UI слоп, нейрослоп дизайн, ревью экрана, верстка, иерархия, отступы, critique, audit UI, taste-skill, impeccable. SKIP: tokens-only DESIGN.md extract (project-design); live Vue/CSS (writer run); UX copy (copy-lead); SEO (seo-specialist)."
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
- Don'ts в DESIGN.md. Серый прототип — page-prototype.

Кто пишет
- Аудит / канон: агент design-lead (MODE=audit|extract|seed). Код не трогает.
- Живой сайт/кабинет: UI-ран, writer. read_first: DESIGN.md + этот скилл.
- Ты говоришь оркестратору. Оркестратор сам не верстает.

Маршрут
1) Нет DESIGN.md              → project-design (design-lead extract/seed)
2) Слоп / «проверь дизайн»    → design-taste + impeccable-ui critique
                                 design-lead MODE=audit
3) a11y / адаптив / состояния → impeccable-ui audit (отчёт)
                                 чинить — ран
4) Новая страница, ещё серая  → page-prototype
5) Токены / бренд / баннер    → project-design + ui-ux-pro-max
6) Тексты кнопок / ошибки     → copy-lead (impeccable clarify)

Нельзя
- Vue/CSS из design-lead или оркестратора
- npx impeccable install, хуки, PRODUCT.md
- 23 слэш-команды impeccable в ~/.claude
- менять палитру в обход DESIGN.md

Шпаргалка: /lane-stack:web-design info
Каталог: /lane-stack:info
```

## Work (not info)

1. Load **one** child skill from the table. Do not load all of them.
2. Existing UI without `DESIGN.md` → `project-design` first, then come back.
3. Review: spawn **design-lead** `MODE=audit` `APP=<surface>`. Need a screenshot or URL (orchestrator captures via chrome-devtools). Output: Don'ts in that app's `DESIGN.md` + `.agents/session-log/DESIGN-AUDIT-YYYY-MM-DD.md`.
4. After the human says **«делай»**: open a run. Writer `read_first`:
   - `docs/DESIGN.md`
   - `apps/<app>/docs/DESIGN.md`
   - this skill
   - `design-taste`
   - `impeccable-ui`
   - `references/layout.md` next to this file
5. Copy / SEO / tokens-only extract: other skills. See SKIP in the description.

## NEVER

- Product Vue / TS / CSS from this skill or from `design-lead`.
- `PRODUCT.md`, Impeccable edit-hooks, `npx impeccable install`.
- Invent hex when `DESIGN.md` already has tokens.
- Treat Russian text slop as this skill (`ru-check` / `copy-lead`).
