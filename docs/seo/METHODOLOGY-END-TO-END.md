# DrMax methodology — project OT → DO

Канон по трём книгам + prompt-каналу. Главы — указатель; **первоисточник всегда PDF/Markdown корпуса и originals/**.

Корпус: `~/.agents/skills/seo-prompt-engineering-2026/references/books/`  
Промпты: `…/originals/`  
Оркестрация: `seo-drmax-orchestrator` · harness: `SOLO-SEO-ORCHESTRATION.md`

---

## 0. Три слоя одной системы

| Слой | Книга / источник | Роль в проекте |
|---|---|---|
| **A. Passport & research** | *Промптоведение v1.5* + Collector/Validator | Понять нишу, спрос, аудиторию, SERP, риски **до** стратегии |
| **B. Ranking reality** | *Доказательное SEO* | Любое действие → конкретный сигнал (Q*/P*/T*, NavBoost, clutter, contentEffort…) |
| **C. Page craft** | *GIST v3.3 pocketbook* + Humanization/CVD | Страница как незаменимая единица (не «объём текста») |

Правило handoff (книга промптоведения):  
**факты → гипотезы → решения → gaps → первичные источники**. Вывод LLM ≠ доказательство.

---

## 1. Книга «Промптоведение для SEO-стратегов v1.5»

### 1.1. Архитектура промпта (методология, не «чат»)

Промпт = контракт: роль · вход · этапы · запреты · проверка · формат выхода.  
Full vs lite: lite = скрининг; full = решение со стратегическим риском.

### 1.2. Системы 01–25 (измерения, не конвейер по умолчанию)

| № | Система | Зачем в проекте |
|---:|---|---|
| 01 | Niche Landscape | Карта ниши / игроки / модели |
| 02 | Market Opportunity | Где вообще есть вход |
| 03 | Search Demand Mapper | Карта спроса до page mapping |
| 04 / Trend v4 | Trends | Сдвиги спроса |
| 05–07 | Audience / JTBD | Боли, сегменты, jobs |
| 08/15 | Buyer Journey | Запросы по стадиям |
| 09 | Terminology | Язык ниши |
| 10 | SERP Reality Check | Страховка от галлюцинаций |
| 11–13 | Season / Geo / Commercial | Искажения и money-intent |
| 14 | White Space | Тематические пробелы |
| 16 | Platforms | Не только Google |
| 17–19 | E-E-A-T / Entity / Regulatory | Доверие и риски |
| 20–22 | Linkability / Entry / Monetization | Внешний рост и fit |
| 23–25 | Community / Format / AI Search | Голос, формат, GEO |

### 1.3. Матрица применения (сценарии книги)

| Задача | Минимальная связка |
|---|---|
| Зайти в нишу? | 01→02→03→21→22 (+10,17,19,25) |
| Новый SEO-проект | 01→03→05→08→10 (+06,07,09,21,24) |
| Точка входа нового сайта | 02→03→10→21 (+14,17,20,25) |
| Рост существующего | demand + SERP + white space + trust |
| B2B leads | 05→07→08→17→22→13→14 |

### 1.4. Бонусы

- **Universal Project Data Collector v2** → сырая карточка с URL  
- **Project Data Validator & Normalizer** → безопасный вход в любые промпты  
- **Блок 2 конкуренты** (порядок жёсткий): Landscape → Deconstructor → Weakness → SERP Gap → Strategy Builder  

### 1.5. Intent chain (канал + книга)

03 Demand Mapper → Search Intent Classifier → Query Modifier → **живая SERP**  
(Этапы 3.4–3.7 в постах — без оригиналов; не выдумывать как «промпты DrMax».)

---

## 2. Книга «Доказательное SEO 2026» (по частям)

### Часть 1 — Карта реальности Google

| Гл. | Тема | Практика в системе |
|---:|---|---|
| 1 | Конвейер ≠ один алгоритм; индексация→скоринг→NavBoost→Twiddlers | Аудит «на каком этапе ломается» |
| 2 | Q* (siteAuthority, panda debt) vs P* (chrome, clicks) vs T* ABC | Стратегия: slow quality vs fast NavBoost |

### Часть 2 — Технический фундамент

| Гл. | Тема | Артефакт |
|---:|---|---|
| 3 | robots, sitemap, canonical, clutterScore, forwardingdup | `technical/audit.md` + scan versions |
| 4 | CWV как триггер NavBoost (LCP/INP/CLS, TTFB) | measurement + technical fixes |
| 5 | URL architecture, sandbox новых URL | IA / cocoon topology |

### Часть 3 — On-page

| Гл. | Тема | Артефакт |
|---:|---|---|
| 6 | Goldmine titles (Blockbert + NavBoost factors) | meta candidates |
| 7 | H1 hierarchy, passages, avgTermWeight | structure briefs |
| 8 | contentEffort, OriginalContentScore, anti-template | content pipeline + CVD |
| 9 | Entities, QBST, siteRadius | entity map |

### Часть 4 — Off-page / brand

Ссылки, brand signals, SERM, reviews → `offpage/` + Entity Footprint / Poisoning skills.

### Часть 5 — Verticals

E-E-A-T, local/GBP, mobile, e-comm, images/video → flags in ANAMNESIS (`ymyl`, `local`, …).

### Часть 6 — Audit & strategy

T-E-E-A audit, long-term plan, Q* vs NavBoost backlog → `strategy/01-strategy.md`.

### Часть 7+ (LLM / кокон)

Multi-stage content PE, semantic cocoon (Matriarch/Mixed/Support), agentic chains → `strategy/cocoons/`, content runs.

---

## 3. Книга «GIST в примерах» (pocketbook)

| Часть | Главы | Когда |
|---|---|---|
| I Старт | 1 chat · 2 Claude · 3 agents | Активация v3.3 в пайплайне |
| II Создание | 4 creation full · 5 audit rewrite · 6 competitive · 7 one-block | `seo-scan` → content work |
| III Meta | 8 Step 8 page · 9 catalog Step 8.11 | meta.md per page |
| IV Batch / fails | batch, типичные сбои | programmatic catalogs |

Режимы: Creation · Audit · Competitive · One-block · Metadata · Batch.  
После GIST: **CVD** (replaceability) → **Humanization** (delivery) → optional **ai-detect**.

---

## 4. Жизненный цикл проекта в нашей системе

```text
┌─────────────────────────────────────────────────────────────┐
│  MODE A: LIVE SITE          MODE B: GREENFIELD              │
│  seo-onboard live           seo-onboard greenfield          │
└──────────────┬──────────────────────────┬───────────────────┘
               ▼                          ▼
        Collector (site+web)        Client brief → Collector shape
               └──────────┬───────────────┘
                          ▼
                 Validator → ANAMNESIS.md (паспорт)
                          ▼
            services wire (seo-services status)
                          ▼
     discovery (selective 01–25 + intent + SERP)
                          ▼
     strategy (Q*/NavBoost + cocoons + backlog)
                          ▼
     technical scan + evidence APIs
                          ▼
     content: GIST → draft → CVD → humanize
                          ▼
     offpage / measure → loop
                          ▼
     seo-scan (full or pages) → versioned artifacts
```

### Состояния STATUS.phase

`passport → discovery → strategy → technical → content → offpage → measure`

### Что нельзя

- Стратегия без ANAMNESIS (или явный skip + gaps)  
- Page decisions без SERP/даты (гипотеза)  
- Путать GIST-маркер / SERP-кластер / URL  
- Выдумывать метрики  
- «Улучшать» originals DrMax  

---

## 5. Артефакты (диск = правда)

| Путь | Содержание |
|---|---|
| `ANAMNESIS.md` | Живой паспорт (validated) |
| `passport/*` | Сырой collector, gaps, sources |
| `scans/site/<ts>/` | Версия обзора сайта |
| `scans/pages/<slug>/<ts>/` | Версия анализа URL |
| `discovery/*` | Research outputs |
| `strategy/*` | Q*/NavBoost, cocoons, backlog |
| `content/pages/<slug>/` | GIST/draft/cvd/meta |
| `prompts-used/log.tsv` | Provenance |
| `runs/*` | Исполняемые пакеты задач |

Команды: `seo-onboard` · `seo-scan` · `seo-resume` · `seo-services`.

---

## 6. Как читать книги агенту

1. Сначала этот файл + `activation-matrix.md`  
2. Нужная глава books/*.md (не весь том)  
3. Оригинальный промпт из originals/  
4. Свежие данные: SERP / GSC / Mutagen / DataForSEO  

---

## 7. Карта «кто что делает»

| Работа | Кто |
|---|---|
| Onboard + passport | `seo-onboard` + agent + Collector/Validator |
| Rescan | `seo-scan` (+ agent deep analysis) |
| Strategy judgment | seo-specialist (Claude) |
| Bulk drafts | grok/qwen via seo-dispatch |
| APIs | seo-services env + skills |
| Code on site | dev-orchestrator |
