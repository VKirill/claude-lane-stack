# Живая документация кода: чертёж этапа `docs`

Самодостаточный чертёж. Его можно отдать агенту с задачей «собери это».
Не библиотека. Законы + раскладка + шапки + индексы + ночь + шаблоны.

Сверено с тем, что уже есть в стеке на 2026-08-28:

- методология страниц: `docs-methodology`, `wiki-methodology` (Karpathy INIT/INGEST/QUERY/LINT)
- ночной детектор: `bin/docs-stale` (цитаты ∩ `git log --since`)
- раннер: `bin/docs-maintain-project` / `docs-maintain-all` (сейчас terra/high, cron-пример 03:30)
- LLM-pack: `docs/llm/{MANIFEST,MODULE_MAP,API_SURFACE,INDEX,TAXONOMY,FLOWS,TEST_INDEX}`
- граф кода: GitNexus (File/Function/Class/Process/Route/Community + CALLS/IMPORTS)
- сосед: этап `stages.memory` (факты). Docs — не память. Memory не пишет `docs/`.
- внешние законы (не копировать продукты): Karpathy LLM Wiki gist; Cherny lean CLAUDE + ablation + verify; Howard `llms.txt`; Procida Diátaxis; Horthy own-context / dumb zone; Every compound (learn → не в wiki кода); Willison versioned concat только для мелких либ; Yegge Beads = трекер, не `docs/`; [agents.md](https://agents.md/).

**Какие боли лечит**

1. Wiki из 400 файлов, модель грузит всё или ничего.
2. После дневного диффа из 5 файлов ночь переписывает ARCHITECTURE целиком.
3. Связи «кто кого зовёт» живут в прозе и врут через неделю.
4. Один сайт, один бот, один Swift-таргет — разные выдуманные схемы шапок.
5. `wiki/` и `docs/` дублируют одно и то же.

Спойлер: **паутину руками не ведут.** Проза — файлы. Рёбра, INDEX, backlinks — производные.
Модель пишет только тело. Ночь трогает только страницы, связанные с вчерашними коммитами.

---

## 1. Десять канонов

1. **Код + GitNexus — единственная правда.** Страница без `file:line` не факт. Запрещено класть в `sources:` другие md (`PROJECT.md`, `CLAUDE.md`, `docs/**`, `wiki/**`).
2. **Файлы — хранение. Индексы — производные.** Стерли `docs/INDEX.md`, `docs/web.yaml`, шапку `web:` — пересобрали скриптом. Прозу не восстановить из индекса: её пишет модель/человек.
3. **Два блока в каждом файле.** `web:` машине. Редакция и `<!-- body -->` — модели. Кто правил не своё — линт падает.
4. **Язык не поле схемы.** Нет `swift:` / `django:`. Роли: `unit | surface | hub | process | store`. Вход снаружи: `via: http|cli|bot|ui|queue|job|rpc`.
5. **Одна страница — один ответ** (Karpathy / EPPO). Модель грузит страницу целиком и действует. Нет «см. ещё три файла, иначе не понять».
6. **Ночь = вчерашний git ∩ владение.** Не полный regen. Нет кода в окне → модель не зовётся.
7. **Luna max fast на узкий список.** В промпт — stale-страницы + их `owns`, не весь `docs/`. Terra не нужна для точечной правки.
8. **Архив не живой.** `wiki/`, `TODO/`, `docs/plans/` ночь не пишет. После переноса уникального `wiki/` удаляют явно («сноси»).
9. **Нет эмбеддингов в горячем пути.** Поиск страницы: манифест + `web.yaml` + GitNexus. Смысловой поиск по уже написанной wiki — опционально позже, не v1.
10. **Честная деградация.** Нет GitNexus → `owns` из манифестов/glob, `uses` пустой, в отчёте `web: degraded`. Нет манифеста → fallback `DEFAULT_LIVE`. Незакоммиченное вчера не существует для 05:00.

---

## 2. Слои (три, не четыре)

```
1. Sources     код + git + GitNexus          неизменяемая правда
2. Wiki        docs/**/*.md тела             модель / человек
3. Schema      шапка web + builders + MANIFEST   конфиг и проекции
```

Memory (`.agents/memory/`) — другой продукт: факты, CORE, FTS5. Сюда не смешивать.
GitNexus — call-graph. `docs/web.yaml` — **читаемая проекция** того же графа для модели без MCP.

Не строить вторую графовую БД.

---

## 3. Что уже есть / что дописать

| Уже есть | Роль в чертеже | Дыра |
|----------|----------------|------|
| Frontmatter `title/type/sources` | редакция + stale-контракт | нет паутины |
| `docs-stale` | цитаты ∩ git | нет `owns:` / хабов / CALLS |
| `docs-maintain-project` | ночной LLM | зашиты terra, high, 450s, cron 03:30 |
| `docs/llm/*` | machine indexes onboard | нет `web.yaml`, нет `stages.docs` |
| GitNexus | граф символов | не проецируется в шапки |
| wiki-methodology INIT/INGEST | операции | stub-файлы не генерятся скриптом |
| `templates/llm/MANIFEST.yaml` | live pack | SelfyStudio root MANIFEST нет |

Дописать в стеке (не в каждом проекте): `docs-web`, `stages.docs`, Luna max fast, cron 05:00, расширение stale через `owns`+хабы.

---

## 4. Раскладка на диске

### 4.1. Одно приложение

```
docs/
  INDEX.md                 # builder, модель не пишет
  web.yaml                 # builder, все рёбра
  log.md                   # append-only ночь/INIT, префикс grep
  llms.txt                 # корень репо ИЛИ docs/ — карта Howard
  ARCHITECTURE.md
  RUNBOOK.md
  gotchas.md
  glossary.md              # термины проекта, не энциклопедия
  patterns.md              # только повтор ≥3 unit
  data-model.md            # если есть store
  decisions/               # ADR, не дневник
  analyses/                # редкий QUERY→страница
  components/<unit>.md
  hubs/<сквозное>.md
  surfaces/<вход>.md       # опционально, если surface ≠ unit
  llm/
    MANIFEST.yaml          # live vs archive
    MODULE_MAP.yaml
    API_SURFACE.yaml
    INDEX.md
    TAXONOMY.yaml
    FLOWS.md
    TEST_INDEX.yaml
```

### 4.2. Монорепо

```
docs/
  INDEX.md
  web.yaml
  ARCHITECTURE.md
  apps/<app>.md            # kind: unit, owns: apps/api/**
  packages/<pkg>.md
  hubs/<id>.md             # creditAfterPayment, AuthContext
  llm/                     # карта монорепо
apps/<app>/
  CLAUDE.md                # ≤60 строк: Owns, Never, Verify, → ./docs/
  AGENTS.md                # только если never/verify отличаются от корня
  docs/
    INDEX.md
    ARCHITECTURE.md        # это приложение, не монорепо
    GOTCHAS.md
    llm/API_SURFACE.yaml
    llm/FLOWS.md
```

Корень `docs/` — карта монорепо + хабы + `web.yaml`.  
`apps/<name>/docs/` — **полная** документация этого приложения, не stub. После fill агент из cwd=`apps/api` отвечает без корневых эссе: что владеет, never, verify, свои surface, свои 2–5 потоков, свои gotcha — всё с `file:line`. Тонкий pack (5 строк «это API») = fail INIT.

Не копировать в app то, что **не его**: чужие приложения, корневой C4 всего монорепо, все hubs целиком, glossary, `web.yaml`, `docs/plans/`. На сквозное — ссылка `hubs: [id]` + одна строка «зачем нам». Хаб живёт в корне.

Stub (`status: stub`) — только пока ночь/агент не заполнили. Это стадия, не формат.

Тот же конвейер, что у корня, **с префиксом** `apps/<name>/`:

| Локально сеет `docs-web` / stale | Не дублировать, брать из корня |
|----------------------------------|--------------------------------|
| `INDEX.md` из локальных страниц | `docs/web.yaml` (фильтр `owns` по префиксу) |
| шапки `web:` на локальных md | `glossary.md`, `patterns.md`, все `hubs/` |
| stub/fill ARCHITECTURE, GOTCHAS, FLOWS | корневой C4 / чужие apps |
| `llm/API_SURFACE.yaml` — строки path ∈ app | `docs/log.md` (одна лента на репо) |
| `llms.txt` опционально, если pack толстый | `docs/plans/` |

Ночь: вчерашние файлы под `apps/api/**` → stale только `apps/api/docs/**` (+ корневые страницы, чей `owns` пересекся). Чужие app-pack не трогать.

`CLAUDE.md` — в каждом живом `apps/*` (есть `package.json` + исходники).  
`AGENTS.md` — один в корне репо. Второй во вложении, только если команды/never другие. Ближайший к файлу побеждает ([agents.md](https://agents.md/)).

`packages/*` — страница в корневом `docs/packages/`, не полный app-pack.
Исключение: жёсткое ядро (domain) может иметь вложенный CLAUDE.

### 4.3. Запретные деревья для ночи

```
wiki/
TODO/
docs/plans/
docs/compliance/          # если legal — archive в MANIFEST
docs/seo/                 # черновики SEO — archive
```

---

## 5. Виды страниц (`kind`)

Языково-слепые. Питон, Swift, бот, сайт — одни и те же значения.

| kind | Что это | Откуда берётся без LLM |
|------|---------|------------------------|
| `unit` | Кусок владения | `package.json` workspaces, `pyproject.toml`, `Package.swift` target, `Cargo.toml` member, `go.mod`+`cmd/`, `*.xcodeproj`, иначе папка `src\|app\|apps\|lib` с ≥N файлами |
| `surface` | Вход снаружи | GitNexus `Route`/`Tool`/`ENTRY_POINT`; CLI `bin/`; bot handler; SwiftUI `@main`; queue consumer |
| `hub` | Символ/тип с callers в ≥N разных unit | GitNexus impact / CALLS, порог N=3 |
| `process` | Именованный поток | GitNexus Process (`heuristicLabel`) |
| `store` | Схема/持久 | `schema.prisma`, `*.xcdatamodeld`, SQL migrations, Redis key module |

`via` у surface (не схема, фасет): `http | cli | bot | ui | queue | job | rpc`.

Не класть в шапку: язык, фреймворк, «class vs struct», полный dump символов.

---

## 6. Контракт шапки

Каждая живая страница = YAML frontmatter + тело между маркерами.

```markdown
---
# --- editorial (модель/человек) ---
title: Auth
type: reference              # reference | explanation | how-to | troubleshooting | adr
status: stub                 # stub | active | stale | deprecated
confidence: low              # low | medium | high
created: 2026-08-28
updated: 2026-08-28
tags: [auth, security]
sources: []                  # файлы, которые модель реально открыла

# --- web (только docs-web) ---
id: auth
kind: unit
owns:
  - packages/auth/**
uses: [persistence-prisma]
used_by: [api, bot-thin, cabinet]
surfaces:
  - {via: http, at: /v1/admin/sse-auth}
hubs: [auth-context]
processes: [login]
symbols:
  - {name: requireAuth, file: packages/auth/src/index.ts}
web_hash: sha256:…
web_status: ok               # ok | degraded
---

# Auth

<!-- body:start -->
TL;DR: …

<!-- fill:purpose -->
<!-- fill:public-api -->
<!-- fill:gotchas -->
<!-- body:end -->

<!-- backlinks:start -->
<!-- backlinks:end -->
```

### Правила полей

| Поле | Кто пишет | Закон |
|------|-----------|--------|
| `title type status confidence created tags` | модель при fill; `created` не менять | `confidence: high` только если `len(sources) ≥ 15` |
| `updated` | builder если web/body hash сменился | иначе старое |
| `sources` | модель | только код, пути существуют, ≥1 после fill |
| `id kind owns uses used_by surfaces hubs processes symbols web_*` | `docs-web` | модель тронула → lint fail |
| `symbols` | `docs-web` | потолок 15; public API или hub, не утилиты |
| тело вне `body` / `backlinks` | никто | |

`sources:` и `owns:` — разные вещи. `owns` = владение (glob). `sources` = «я это читал» (stale-контракт прозы).

---

## 7. Индексы

Все, что модель или ночь читают. Ни один не источник правды.

### 7.1. GitNexus (внешний, уже есть)

Узлы: `File`, `Folder`, `Function`, `Class`, `Interface`, `Method`, `Process`, `Route`, `Tool`, `Community`, плюс `` `Struct` `` / `` `Enum` `` / `` `Trait` `` / `` `Impl` ``.

Рёбра: `CALLS`, `IMPORTS`, `EXTENDS`, `IMPLEMENTS`, `HAS_METHOD`, `HAS_PROPERTY`, `ACCESSES`, `HANDLES_ROUTE`, `HANDLES_TOOL`, `ENTRY_POINT_OF`, `STEP_IN_PROCESS`.

Инструменты для сборщика и для модели при fill:

| Инструмент | Зачем |
|------------|--------|
| `query` | процессы по теме |
| `context` | callers/callees символа |
| `impact` | хабы, blast radius |
| `route_map` / `tool_map` | surfaces |
| `detect_changes` | ночь: какие процессы задеты вчерашним diff |
| `cypher` | fan-in ≥ N unit для хабов |

Нет индекса → `web_status: degraded`, рёбра из import-строк/glob.

### 7.2. `docs/web.yaml` — паутина одним файлом

Производная. Модель без MCP глотает целиком.

```yaml
version: 1
generated: 2026-08-28T02:00:00Z
gitnexus: ok                 # ok | missing | stale
nodes:
  - id: auth
    kind: unit
    page: docs/packages/auth.md
    owns: [packages/auth/**]
  - id: auth-context
    kind: hub
    page: docs/hubs/auth-context.md
edges:
  - {from: api, to: auth, rel: uses}
  - {from: bot-thin, to: auth, rel: uses}
  - {from: auth, to: auth-context, rel: hub}
```

### 7.3. `docs/INDEX.md`

Builder из frontmatter + первая строка после H1 (TL;DR). Группы: foundation → systems → units → hubs → processes. Модель файл не пишет.

### 7.4. `docs/llm/MANIFEST.yaml` — что живое

Уже шаблон стека. Для ночи обязателен `pack.always_load` + `pack.on_demand`.
Страница не в манифесте и не попадает под glob live → ночь её не видит.

```yaml
version: 1
project: selfystudio
refresh:
  cadence: nightly
  last_refresh: null
  last_full_onboard: 2026-08-01
  owner_role: docs-maintainer
pack:
  always_load:
    - CLAUDE.md
    - AGENTS.md
    - docs/INDEX.md
    - docs/llm/INDEX.md
  on_demand:
    - docs/ARCHITECTURE.md
    - docs/web.yaml
    - docs/packages/*.md
    - docs/apps/*.md
    - docs/hubs/*.md
    - docs/glossary.md
    - docs/patterns.md
    - docs/gotchas.md
    - docs/data-model.md
    - docs/log.md
    - docs/llm/MODULE_MAP.yaml
    - docs/llm/API_SURFACE.yaml
    - docs/llm/FLOWS.md
archive:
  - wiki/**
  - docs/plans/**
  - docs/compliance/**
  - docs/seo/**
```

`docs-stale` уже читает `pack.always_load` + `on_demand` + `live`. Добавить чтение `archive` только как запрет, не как live.

### 7.5. Machine indexes onboard (не дублировать паутину)

| Файл | Держит | Не держит |
|------|--------|-----------|
| `MODULE_MAP.yaml` | ответственность, may_import, verify | callers каждого символа |
| `API_SURFACE.yaml` | http/cli/webhook/queue ряды | проза why |
| `TEST_INDEX.yaml` | как проверять | смысл теста |
| `FLOWS.md` | 2–5 критических цепочек | все Process из GitNexus |
| `TAXONOMY.yaml` | Diátaxis × load | рёбра |

Хабы и `used_by` живут в `web.yaml` + шапках, не копировать в MODULE_MAP.

### 7.6. Эфемерный индекс ночи

`docs-stale` печатает JSON в stdout, в файл не кладёт. Раннер отдаёт его модели как `STALE_JSON`.

```json
{
  "status": "stale",
  "since": "yesterday",
  "changed": ["packages/auth/src/index.ts"],
  "stale_docs": ["docs/packages/auth.md", "docs/hubs/auth-context.md"],
  "hits": [{"doc": "docs/packages/auth.md", "changed": ["packages/auth/src/index.ts"]}]
}
```

### 7.7. Чего нет в v1

FTS по docs, векторный поиск, отдельная graph-DB, индекс в `.cls/` (это memory).

---

## 8. Детерминированные сборщики

Модель эти артефакты не пишет. Publish/lint отвергает, если написала.

| Команда | Вход | Выход |
|---------|------|--------|
| `docs-web` | манифесты unit + GitNexus | шапки `web:`, `docs/web.yaml`, stub-файлы если страницы нет |
| `docs-index` | все живые md | `docs/INDEX.md` |
| `docs-backlinks` | markdown-ссылки | блоки `<!-- backlinks -->` |
| `docs-stale` | git since + live pack + `owns` + web | JSON stale |
| `docs-lint` | страницы | fail: модель правила web, битый owns, запретный sources, archive в live; weekly: orphans, glossary gaps |
| `docs-log` | результат ночи/lint | append `docs/log.md` |
| glossary seed | hubs + schema + unit ids | строки Term, Means пустой |

Существующие `docs-stale` расширить:

1. Цитаты в теле / `sources:` (как сейчас).
2. Glob `owns:` из шапки или `web.yaml`.
3. Хабы: из `web.yaml` рёбра `hub` / GitNexus CALLS от вчерашних файлов.
4. Новые файлы без страницы → `docs-web` создаёт stub `status: stub`, попадает в stale.

---

## 9. Заготовка → обход модели

Karpathy: INIT = stubs+web. INGEST = fill + ночь.

```
docs-web          # 0 LLM: единицы, рёбра, stubs
docs-stale        # 0 LLM: что fill/refresh
luna max fast     # только status:stub или stale_docs
docs-index
docs-backlinks
docs-lint
```

Модель за один проход — **одна страница**. Читает `owns` + до 3 `uses`. Пишет только `<!-- body -->` и редакционные поля. Ставит `status: active`, заполняет `sources`.

Пустой день: шаги 3 нет.

Потолок за ночь: 12 страниц (как memory writes). Остальное — следующая ночь или явный `docs-maintain-project . "7 days ago"`.

---

## 10. Ночь 05:00

```
0 5 * * * $HOME/.agents/bin/docs-maintain-all yesterday \
  >>$HOME/.agents/logs/docs-maintain.log 2>&1
```

Окно: **закоммиченное** с `yesterday` 00:00 до 05:00. Грязное дерево невидимо (канон 10).

Порядок:

1. `git log --since=yesterday --name-only` — список файлов.
2. `docs-web` — обновить шапки, чей `owns` пересёкся; создать stub для нового unit.
3. `docs-stale` — цитаты ∪ owns ∪ хабы.
4. Пусто → SKIP, отчёт одна строка, без Codex.
5. Codex **gpt-5.6-luna** + `reasoning_effort=max` + `service_tier=fast` + `--ignore-user-config` + `CLAUDE_LANE_AUTOMATION=1` + timeout ≥1800s.
6. Промпт содержит только `STALE_JSON` + тексты этих страниц. Не весь docs.
7. Отчёт `.agents/session-log/DOCS-YYYY-MM-DD.md`.

Пять файлов за день → обычно 1–3 страницы + 0–1 хаб. Не «пересобрать docs/».

---

## 11. Этап adoc `stages.docs`

Как memory: opt-in. Выкл → cron skip.

```yaml
stages:
  docs:
    enabled: false          # только это включает корпус/ночь
    maintain: true
    provider: codex
    model: gpt-5.6-luna
    reasoning_effort: max
    service_tier: fast
    page_cap: 0              # 0 = all stale pages; optional cap if set
    since: yesterday
```

TUI: крутилки как у memory. По умолчанию выкл. Включили — Luna max fast уже стоят.

---

## 12. Шаблоны файлов

### 12.1. Stub unit (пишет `docs-web`, тело пустое)

```markdown
---
title: Auth
type: reference
status: stub
confidence: low
created: 2026-08-28
updated: 2026-08-28
tags: [auth]
sources: []
id: auth
kind: unit
owns:
  - packages/auth/**
uses: []
used_by: []
surfaces: []
hubs: []
processes: []
symbols: []
web_hash: sha256:pending
web_status: ok
---

# Auth

<!-- body:start -->
TL;DR: _stub — fill from owns_

<!-- fill:purpose -->
<!-- fill:public-api -->
<!-- fill:flow -->
<!-- fill:gotchas -->
<!-- body:end -->

<!-- backlinks:start -->
<!-- backlinks:end -->
```

### 12.2. Заполненный hub (сквозной символ)

```markdown
---
title: AuthContext
type: reference
status: active
confidence: medium
created: 2026-08-28
updated: 2026-08-28
tags: [auth, hub]
sources:
  - packages/auth/src/index.ts
  - apps/api/src/routes/v1/admin/sse-auth/routes.ts
  - apps/bot-thin/src/context.ts
id: auth-context
kind: hub
owns:
  - packages/auth/src/index.ts
uses: []
used_by: [auth, api, bot-thin, cabinet]
surfaces: []
hubs: []
processes: [login, admin-sse]
symbols:
  - {name: AuthContext, file: packages/auth/src/index.ts}
web_status: ok
---

# AuthContext

<!-- body:start -->
TL;DR: subject + role + permissions; raw credentials не входят (`packages/auth/src/index.ts:29`).

Пронизывает api, bot-thin, cabinet. Менять форму — смотреть `used_by`.
<!-- body:end -->
```

Unit **не копирует** хаб. Только `hubs: [auth-context]` и ссылка `[AuthContext](../hubs/auth-context.md)`.

### 12.3. Surface (бот, не HTTP)

```yaml
id: bot-pay-callback
kind: surface
owns:
  - apps/bot-thin/src/handlers/pay.ts
surfaces:
  - {via: bot, at: callback:pay}
uses: [auth, billing]
```

Тот же шаблон для Swift screen: `via: ui`, `at: SettingsView`.
Для очереди: `via: queue`, `at: generation.completed`.

### 12.4. Process

```yaml
id: checkout
kind: process
owns: []                    # процесс не владеет деревом
uses: [api, worker, billing]
processes: []
# GitNexus heuristicLabel: Checkout
```

Тело: нумерованные шаги + `file:line`. Не дублировать FLOWS.md целиком — FLOWS держит 2–5 критических; process-страница — если поток ветвистый.

### 12.5. Одно приложение без packages/

```yaml
id: app
kind: unit
owns:
  - src/**
used_by: []
surfaces:
  - {via: http, at: /}
  - {via: cli, at: bin/serve}
```

Страницы: `docs/ARCHITECTURE.md`, `docs/components/app.md` или сразу компоненты по папкам `src/<area>`.

---

## 13. Как модель обходит stub (промпт-закон)

1. Загрузить этот чертёж + `wiki-methodology` page-type для `type:`.
2. Взять одну страницу из `STALE_JSON` / списка `status: stub`.
3. Прочитать файлы из `owns` (не больше разумного; приоритет entry + public export).
4. GitNexus `context` на `symbols[]`, если индекс есть.
5. Писать только `<!-- body -->`. Цитаты `path:line`. Без маркетинга.
6. `sources:` = реально открытые файлы.
7. Не создавать соседние страницы «заодно». Нет файла — оставить `(planned)`.
8. Не трогать `wiki/`, `docs/plans/`, код.

---

## 14. Кто что читает днём

| Кто | Грузит | Не грузит |
|-----|--------|-----------|
| Холодный старт `resume-project` | CORE memory + CLAUDE + `docs/llm/INDEX.md` | всю wiki |
| Writer lane | CLAUDE + MODULE_MAP строка модуля + 1 component/hub | `docs/plans/` |
| Docs night | `STALE_JSON` + эти файлы | always_load целиком |
| Человек | `docs/INDEX.md` | `web.yaml` не обязан |

QUERY (агент перед работой): `docs/web.yaml` → страница unit/hub → код по `owns`.

---

## 15. Связь с onboard и memory

| Система | Пишет | Ночь |
|---------|-------|------|
| `project-onboard` | INIT: CLAUDE, `docs/llm/*`, опционально первые stubs | нет, один раз |
| `docs` этап | INGEST: web + проза по диффу | 05:00 Luna |
| `memory` этап | факты `.agents/memory/` | свой maintain, не docs |

LESSONS/PROGRESS/session-log **не** источники wiki (канон 1).
Onboard не оставляет тонкие stubs как «готово»: либо fill сразу, либо `status: stub` и ночь добьёт.

---

## 16. SelfyStudio — пилот, не снос

Сейчас: `docs/components/*.md` с редакционной шапкой (пример `auth.md`: `sources:` есть, `owns`/`uses` нет). `wiki/` ≈ дубль. `docs/plans/` огромный архив. Корневого `docs/llm/MANIFEST.yaml` нет.

Порядок пилота:

1. Положить MANIFEST: live = INDEX + ARCHITECTURE + `docs/components/*` + будущие hubs. archive = plans, compliance, seo, wiki.
2. Прогнать `docs-web` на `packages/auth` → шапка на существующем `docs/components/auth.md` (прозу не затирать).
3. Dry-run `docs-stale --since yesterday`.
4. Одна ночь Luna по реальному диффу.
5. `wiki/` не удалять, пока INDEX кормится из `docs/` и человек сказал «сноси».

---

## 17. NEVER

- Вторая графовая БД «потому что паутина».
- Эмбеддинги в ночном горячем пути.
- Luna на весь `docs/` «на всякий случай».
- Модель пишет INDEX, backlinks, `web:` поля.
- Ночь пишет `docs/plans/`, legal, seo-черновики, feature code.
- `sources:` из других md.
- Языковые поля в схеме шапки.
- Тихий снос `wiki/`.
- Считать незакоммиченное «вчерашними файлами».
- LESSONS / `docs/solutions/` / чат в живую wiki (compound — в `.agents/`).
- `llms-full.txt` на весь монорепо (Willison так делает только для маленькой либы).
- Туториалы в LLM-pack. Глоссарий общеизвестных слов без местного инварианта.

---

## 18. Сборка в стеке (порядок работ)

1. Контракт шапки + `docs-lint` на web/body маркеры.
2. `docs-web` v1: единицы из npm/python/swift манифестов + glob owns; GitNexus опционален.
3. Расширить `docs-stale`: owns + web.yaml хабы.
4. `stages.docs` в `pipeline_stages.py` + TUI (дефолт luna/max/fast, enabled false).
5. Переключить `docs-maintain-project`: Luna, fast, `--ignore-user-config`, timeout 1800, `page_cap`.
6. Cron-пример 05:00 + `since=yesterday`.
7. Пилот SelfyStudio: MANIFEST + одна шапка auth + dry-run.
8. Шаблоны §21 в `templates/docs/` + `docs-web` сеет glossary/log stubs.
9. `docs-lint` + редкий lint-проход Luna (сироты, термин без страницы).
10. Потом: хабы из fan-in, process-страницы, удаление wiki по команде.

---

## 19. Карта файлов стека (куда ляжет код)

| Путь | Зачем |
|------|--------|
| `bin/docs-web` | сборка шапок + stubs + `web.yaml` |
| `bin/docs-stale` | уже есть; расширить |
| `bin/docs-maintain-project` | уже есть; Luna + knobs |
| `bin/docs-maintain-all` | уже есть; cron 05:00 |
| `bin/pipeline_stages.py` | `stages.docs` |
| `agents/codex/instructions/docs-maintain.md` | промпт: только stale, не трогать web |
| `plugins/lane-stack/skills/docs-maintain/SKILL.md` | info-блок |
| `templates/docs/unit.md` | stub unit |
| `templates/docs/hub.md` | stub hub |
| `templates/docs/glossary.md` | таблица терминов |
| `templates/docs/patterns.md` | повтор ≥3 |
| `templates/docs/gotchas.md` | symptom/cause/workaround |
| `templates/docs/log.md` | префикс ingest/lint |
| `docs/DOCS-STAGE.md` | этот чертёж |

Методология страниц не копируется сюда: грузить `docs-methodology` + `wiki-methodology` как сейчас.

---

## 20. Smell test перед реализацией

1. Факт нельзя вывести из символа/графа? Тогда это проза, не поле шапки.
2. Поле нельзя заполнить без LLM? Тогда его нет в `web:`.
3. Страница нужна, если senior не узнает нового? Не создавать (living-documentation §curation).
4. Пять файлов за день породили бы 40 stale-страниц? Порог хаба завышен или owns слишком широкий (`**` на корень).

---

## 21. Что класть в систему сразу (пакет INIT)

Не плодить новую таксономию. Имена уже в `TAXONOMY.yaml` / wiki-methodology. Здесь — **обязательный минимум** при `docs-web` INIT и шаблоны, с которых агент не сходит.

Живое только `docs/`. `wiki/` не создавать и не писать.

### 21.1. Всегда (любой репозиторий)

| Файл | Кто сеет | Кто наполняет | Always-load? |
|------|----------|---------------|--------------|
| `docs/INDEX.md` | builder | никто | да (карта) |
| `docs/web.yaml` | builder | никто | нет, QUERY |
| `docs/log.md` | stub | ночь append | нет |
| `llms.txt` | builder из INDEX | никто | да, тонкий |
| `docs/ARCHITECTURE.md` | stub | агент | нет |
| `docs/gotchas.md` | stub | агент | нет |
| `docs/glossary.md` | скрипт: список терминов | агент: колонка Means | нет |
| `CLAUDE.md` / `AGENTS.md` | onboard | человек; абляция | да, ≤200 строк |

CLAUDE содержит **указатель** на INDEX + Never/Verify. Не API, не глоссарий, не паттерны (Черный / Anthropic / agents.md).

### 21.2. Если есть в коде (условные)

| Условие | Файл |
|---------|------|
| store (Prisma, SQL, CoreData, Redis-модуль) | `docs/data-model.md` — каркас таблиц скриптом |
| UI | `docs/DESIGN.md` (уже в pack) |
| деплой / compose / systemd | `docs/RUNBOOK.md` + `deployment.md` |
| auth / секреты | не отдельный роман; хаб + секция в ARCHITECTURE |
| ≥3 unit зовут один символ | `docs/hubs/<id>.md` + строка-кандидат в `patterns.md` |
| есть `.env.example` | таблица ENV **внутри** RUNBOOK, не новый файл |
| ADR-класс решения | `docs/decisions/<slug>.md` — не с INIT пачкой |

### 21.3. Не с INIT

`docs/solutions/`, `active-tasks.md` из TODO, `analyses/*` пачкой, process-страница на каждый GitNexus Process, `security.md` без auth, туториалы, `llms-full.txt` монорепо, дубль LESSONS/PROGRESS.

`patterns.md` — пустой stub. Строки появляются, когда скрипт или агент доказал повтор.

---

## 22. Шаблоны агенту (копировать в `templates/docs/`)

Маркеры `<!-- body -->` / `<!-- fill:* -->` как в §6. `web:` на glossary/gotchas/log — минимальный (`kind` ниже).

### 22.1. `glossary.md`

Скрипт кладёт строки Term из: `hub` id, модели schema, enum, `id` unit. Means пустой → `status: stub`.

```markdown
---
title: Glossary
type: reference
kind: store
status: stub
confidence: low
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: [glossary]
sources: []
id: glossary
owns: []
---

# Glossary

<!-- body:start -->
| Term | Means here | hub / unit | file:line |
|------|------------|------------|-----------|
| AuthContext | | hubs/auth-context | |
<!-- body:end -->
```

Закон: одно локальное значение. Общеизвестное слово без инварианта этого репо — удалить. Синоним: `see: <Term>`. Нет `file:line` после fill — строка не факт.

Ночь: вчера переименовали символ/модель → обновить или вычеркнуть строку.

### 22.2. `patterns.md`

```markdown
---
title: Patterns
type: reference
status: stub
tags: [patterns]
id: patterns
---

# Patterns

<!-- body:start -->
## <Name>

**Repeats in:** [api](apps/api.md), [worker](apps/worker.md)
**Rule:** one sentence the next writer must follow
**Evidence:** `a.ts:10`, `b.ts:20`, `c.ts:30`
**Do not:** the failure mode
<!-- body:end -->
```

Нет трёх цитат из **разных unit** — секцию не писать. Скрипт только добавляет `<!-- candidate: symbol X used_by: … -->`. Агент подтверждает или стирает.

### 22.3. `gotchas.md`

Один тип: troubleshooting. Секции Critical / High / Medium / Low.

```markdown
## <short name>

**Symptom:** what you see
**Cause:** `path:line` — why
**Workaround:** concrete action
**Pattern:** Release It! name if Critical/High
```

Не копировать `.agents/LESSONS.md` оптом. Урок «модель снова забыла bun» — в LESSONS, не сюда. Сюда — ловушка **кода**.

### 22.4. `log.md` (Карпатый)

Пишет только раннер/lint. Модель не переписывает историю.

```markdown
# Docs log

<!-- generated; append-only -->

## [2026-08-28] ingest | yesterday
changed: packages/auth/src/index.ts
pages: docs/packages/auth.md, docs/hubs/auth-context.md
model: gpt-5.6-luna max fast
status: updated

## [2026-08-28] lint | weekly
orphans: 0
terms_without_page: AuthRole
web_status: ok
```

`grep "^## \[" docs/log.md | tail -5` — последние операции.

### 22.5. `llms.txt` (Howard)

Builder из INDEX. Корень репо. Не эссе.

```markdown
# selfystudio

> Monorepo: cabinet, api, worker, bot. Agent: start at docs/INDEX.md, then one unit page.

## Always
- [INDEX](docs/INDEX.md): catalog + TL;DR
- [CLAUDE](CLAUDE.md): never / verify / pointers

## On demand
- [Architecture](docs/ARCHITECTURE.md): boundaries
- [Web](docs/web.yaml): owns / uses / hubs
- [Glossary](docs/glossary.md): project terms
```

Ссылки на markdown, не на HTML. Archive в файл не попадает. Вложенный `apps/<name>/` может иметь свой `llms.txt` (v2: самый специфичный побеждает) — как вложенный CLAUDE.

### 22.6. `data-model.md` каркас

Скрипт: список моделей/таблиц из schema. Агент: владелец unit, инвариант, FK.

```markdown
## <Model>

**Owns:** packages/persistence-prisma
**Keys:** …
**Invariant:** …
**Source:** schema.prisma:NN
```

### 22.7. `analyses/<slug>.md` (QUERY → файл)

Только если ответ синтеза не влезает в существующую страницу и есть ≥3 `file:line`. Иначе оставить в чате.

```yaml
type: explanation
status: active
tags: [analysis]
```

Тело: вопрос, вывод, таблица сравнения, ссылки на unit/hub. Ночь не регенерит, пока `sources:` не пересеклись с диффом.

### 22.8. `decisions/<slug>.md`

Только ADR-класс (границы данных, persistence, деплой, security, интеграция, concurrency). Y-statement + ≥2 опции. Пачкой с INIT не сеять.

---

## 23. Lint как операция (не только ночной ingest)

Отдельно от 05:00. Раз в неделю или `docs-maintain-project . lint`.

Детерминизм (0 LLM):

- битые относительные ссылки
- `owns` glob без файлов
- модель правила `web:`
- `sources:` из `docs/**` / `wiki/**`
- термин в glossary без `file:line` при `status: active`
- страница live не в INDEX
- сирота: нет входящих ссылок и нет ребра в `web.yaml`

Luna (узкий список из отчёта линта): противоречие двух страниц по одному `file:line`; термин упомянут в 3+ страницах без строки glossary; candidate pattern без трёх цитат.

Потолок тот же: `page_cap`. Отчёт + строка в `log.md`. Корпус молча не «чистит» (канон memory: отчёт, не автопочинка прозы).

---

## 24. Always-on и абляция

| Слой | Бюджет | Что |
|------|--------|-----|
| CLAUDE + AGENTS | ≤200 строк | Never, Verify, «грузи INDEX» |
| `llms.txt` / `docs/llm/INDEX.md` | одна карта | ссылки + одна строка |
| glossary / patterns / hubs | on_demand | ночь и QUERY |
| memory CORE | свой бюджет | не дублировать в docs |

Раз в новую модель (Черный): выкинуть из always_load всё, без чего writer не ломается. Вернуть только проваленные проверки. Skills/шаблоны не резать — они не в каждом контексте.

`TEST_INDEX` + команда verify в CLAUDE — главный рычаг качества, не длина wiki.

---

## 25. Откуда закон (чтобы не расползтись)

| Источник | Берём | Не берём |
|----------|-------|----------|
| Karpathy gist | ingest/query/lint, index+log, query→analyses редко | LLM пишет INDEX; raw/ отдельно от git |
| Cherny / Anthropic | тонкий CLAUDE, ошибка→LESSONS, verify, абляция | wiki внутри CLAUDE |
| Howard llms.txt | карта + on-demand ссылки | full dump |
| Procida Diátaxis | один `type:` на файл | tutorial в pack |
| Horthy | узкий промпт ночи, не dumb zone | всё в один контекст |
| Every compound | шаг «запомнить урок» | `docs/solutions/` как живая wiki |
| Willison | версия machine-index | склейка 150k токенов монорепо |
| Yegge Beads | задачи в `.agents/runs` | трекер внутри `docs/` |
| agents.md | вложенные файлы, ближайший побеждает | второй README для людей |

X/Twitter с этой машины не читался (Grok CLI без нативного X-поиска). Законы выше — из gist, спек и полных гайдов, не из выдуманных тредов.

---

## 26. Ревью чертежа — что забыли (2026-08-28)

Дыры, без которых `docs-web` / ночь разъедутся. Не новые «хотелки».

### 26.1. Вписать в реализацию (иначе баг)

1. **`status: stub` всегда в stale**, даже если вчерашний git их не трогал. Иначе `page_cap` откладывает fill навсегда: окно 24ч ушло, stub висит.
2. **Слияние шапки.** `docs-web` переписывает только ключи web. `title/type/status/confidence/created/tags/sources` и `<!-- body -->` не трогать. Нет алгоритма → затрём прозу SelfyStudio.
3. **Игнор владения.** `owns` не включает `dist/**`, `*.generated.*`, `node_modules/**`, `.git/**`, lockfiles, бинарники, `coverage/**`. Иначе паутина из мусора.
4. **Удаление / rename кода.** Файл из `owns` исчез → страница `status: deprecated` + строка в log, не молчаливый 404. Rename unit → тот же `id`, путь страницы можно сменить, в INDEX редирект одной строкой.
5. **Регистр имён.** Канон в live pack: `ARCHITECTURE.md`, `gotchas.md`, `glossary.md`, `docs/packages/<id>.md`. SelfyStudio сейчас `docs/components/auth.md` + иногда `architecture.md`. INIT: не плодить дубль; одна страница, старый путь — stub-redirect или снос после «сноси». App-pack: `GOTCHAS.md` vs корень `gotchas.md` — зафиксировать одно (`gotchas.md` везде).
6. **Язык.** Тела wiki — **English** (`LANGUAGE.md`), как LESSONS. Русский только корневой человеческий `README.md`. Иначе ночь смешает RU SelfyStudio и EN pack.
7. **Секреты.** В docs запрещены значения ключей, токены, raw connection string. Только имена env. Линт: паттерны секретов → fail.
8. **Ночь: сначала индекс кода.** Если GitNexus `commitsBehind > 0` — `analyze` или `web_status: degraded` и без новых рёбер. Иначе шапки врут.
9. **Коммит.** Ночь **не** пушит и не коммитит, пока человек / solo-ритуал не сказал. Отчёт в `session-log` + dirty tree. (Сейчас maintain тоже не коммитит — оставить законом.)
10. **Часовой пояс.** `yesterday` = локальный календарный день хоста cron, не `date -u` в имени отчёта вразнобой. Зафиксировать: cron TZ + одно `since`.
11. **Писатель фичи не обновляет docs.** Lane `owns_paths` на код. Docs — ночь или явный docs-maintain. Иначе гонка с 05:00.
12. **Очередь сверх `page_cap`.** В `STALE_JSON` поле `deferred: [...]`. Следующая ночь: сначала `stub` + deferred, потом новый дифф.

### 26.2. Файлы, которые есть в onboard и выпали из §21

| Файл | Куда |
|------|------|
| `docs/TESTING.md` / `TEST_INDEX.yaml` | условно, если есть тесты (уже TAXONOMY) |
| `docs/llm/DOC_LAYOUT.md` | onboard; не always_load |
| `docs/overview.md` | методология «always»; у нас заменяет тонкий `llms.txt` + INDEX TL;DR — **не сеять третий overview**, если INDEX+ARCHITECTURE есть |
| `apps/<name>/docs/llm/MANIFEST.yaml` | локальный live list этого app, иначе ночь не видит pack |
| `apps/<name>/docs/INDEX.md` | первая строка: «корень: ../../docs/INDEX.md» |

`gaps.md` / `active-areas.md` / `SECURITY.md` с INIT не сеять (уже §21.3).

### 26.3. Дрейф двух карт модулей

`MODULE_MAP.yaml` (onboard) и `web.yaml` (docs-web) описывают одни unit. Закон: **id совпадают**. `docs-web` после сборки сверяет id; лишний/пропавший — строка lint, не авто-перепись MODULE_MAP (onboard владеет responsibility/verify).

### 26.4. Бюджет страницы

Тело `<!-- body -->` целевое 5–15 KB (wiki-methodology). Больше → split или ссылка на код. Иначе Luna max fast снова упрётся, как memory на 371k.

### 26.5. Сознательно не добавлять

Событийный `messaging.md` (хватает `via: queue` в surface). FTS по docs. Автокоммит. `llms-full`. Общий `SECURITY.md` без auth. Третий overview. Писать wiki из LESSONS.

