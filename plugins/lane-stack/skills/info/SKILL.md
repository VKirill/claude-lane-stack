---
name: info
description: Lane-stack work-process cheat sheet. Catalog of resume, onboard, architect a new app, design, docs. Use when user says info, справка, lane-stack:info, /lane-stack:info, что умеет стек, как запускать.
argument-hint: "[info]"
user-invocable: false
---

# lane-stack info

Render the card below **exactly** (Russian markdown). Then **stop**.
No intro. No extra sections. Do not start a run, onboard, or design extract.

---

# lane-stack

Рабочие процессы. Одна сессия = `dev-orchestrator`.

```
resume ──► onboard? ──► туду / план ──► архитектор? ──► дизайн? ──► ран ──► доки
```

| | Как открыть |
|---|---|
| Этот каталог | `/lane-stack:info` · `/info` · «справка» |
| Один процесс | `/lane-stack:<имя> info` |

---

## Процессы

### 1. `resume-project` — где мы остановились

Нужен в новой сессии на уже живом репо. Собирает коротко: что сейчас, что застряло, какой следующий шаг. Не пишет код и не открывает ран.

`/lane-stack:resume-project` · `/resume-project` · шпаргалка: `/lane-stack:resume-project info`

### 2. `project-onboard` — первичная карта репо

Нужен, когда нет `CLAUDE.md` или репо чужое. Делает понятную карту: что за продукт, какие части, где тесты. Живой UI без DESIGN.md — это не он, а `design-lead`.

`/project-onboard` · `/project-onboard deep` · `/lane-stack:project-onboard info`

### 3. `app-architect` — новое приложение или сервис

Нужен, когда ещё обсуждаете, *что* строить. Говорит обычными словами. Каждый ответ сразу пишет в файлы плана (`brief`, как части связаны, данные, риски). Ран не открывает.

`/app-architect` · `/lane-stack:app-architect info`

### 4. `project-design` — как это выглядит

Нужен, если будут экраны. Пишет полные `docs/DESIGN.md` и `apps/<имя>/docs/DESIGN.md` (агент `design-lead`): цвета, шрифты, компоненты. Без этих файлов UI-ран не стартует.

`/lane-stack:project-design info`

**`ui-ux-pro-max`** — справочник рядом: стили, удобство, баннеры. Сами DESIGN.md не пишет. `/lane-stack:ui-ux-pro-max info`

### 5. `docs-maintain` — доки после кода

Нужен, когда код уже изменился, а описание устарело. Обновляет живые доки по диффу. Не вики, не старые планы, не новые фичи.

`/lane-stack:docs-maintain info`

### 6. `lane-memory` — факты, которые нельзя вывести из кода

Крутилки в adoc уже рекомендуемые (субагент, Codex terra, inject). Корпус живой после `Enabled`. Одно правило = один файл. Ядро грузится каждую сессию. Пишет только `lane-memory write`.

`/lane-stack:lane-memory info`

### 7. `seo-project-life` — жизнь SEO-проекта

Где лежат паспорт, доска, фазы, модули. Не код сайта и не 18 модулей подряд.

`/lane-stack:seo-project-life info` · агент `seo-specialist`

### 8. `copy-project-life` — копирайт сайта

Не SEO-ключи. Файлы: `.agents/copy/` — `INDEX.md`, `ANAMNESIS.md`, `audience.md`, `buyer-personas/p1.md`, `voice.md`, `pages/<slug>.md`, `research/inbox|used|dead`. `locked` не трогать.

Первый полный анализ (нет папки или пустой оффер): скилл **сам ведёт опрос** пачками по 2–3 вопроса — оффер → ЦА → персона/доказательства (`first-interview.md`). Ответы сразу в шаблоны. «не знаю» = `unknown`. Без оффера H1 не пишет.

Повторно: audience → headlines → ux. Серый HTML-вайрфрейм: `page-prototype` (`site/` · `app/` · `flows/` под `.agents/prototypes/`). Ресёрч: `tavily` · сподручные `copy-research/helpers.md` (luna/terra, grok/X, OpenCode DeepSeek, Cursor Grok 4.6 medium-fast).

`/lane-stack:copy-project-life` · агент `copy-lead` · `/lane-stack:tavily` · `/lane-stack:site-copy-audience` · `/lane-stack:site-copy-headlines` · `/lane-stack:site-copy-ux` · шпаргалка: `/lane-stack:copy-project-life info`

---

## Агенты

Не скиллы. Оркестратор сам их спавнит.

| Агент | Зачем |
|---|---|
| `design-lead` | полные DESIGN.md |
| `run-supervisor` | смотрит один ран |
| `lane-supervisor` | одно действие `lane-ctl` |
| `emergency-writer` | Codex после terminal block |
| `project-onboarder` | онбординг паспорта (первый) |
| `docs-maintainer` | wiki после онборда (второй) |
| `night-reviewer` | ночной review |
| `seo-specialist` | SEO harness (не код) |
| `copy-lead` | копирайт, ЦА, страницы (не SEO, не код) |
| `tavily` | поиск Tavily, отчёт с URL (не копирайт, не SEO) |

---

## Нельзя

- Claude Plan mode и `~/.claude/plans/`
- `run-init`, пока не сказано **«делай»**
- UI-ран без нужных `docs/DESIGN.md` / `apps/<app>/docs/DESIGN.md`
