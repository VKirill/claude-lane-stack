---
name: yandex-direct-creatives
description: "Написать объявление для Яндекс.Директа, разбить CSV кластеры на кампании и группы, шаблоны Direct по intent, лимиты заголовка Direct (56 символов ТГО), дополнительный заголовок Direct (30+15 пунктуации), структура группы Direct, креативы по CSV кластерам Key Collector. Do not use: API-отправка→yandex-direct, юр-ниши→legal-ru-marketing, Google Ads/VK Ads."
stacks:
  - yandex-direct
  - ru-ads
  - ru-marketing
tags:
  - ads
  - ppc
  - ru
  - yandex
  - direct
  - creatives
  - csv-workflow
source: vechkasov-global-skills
risk: medium
---

## Use this skill when

- Пишешь объявления для Яндекс.Директа любого формата (ТГО, РСЯ-баннер, СмартБаннер, МастерКампания)
- Получил CSV-выгрузку из Key Collector — нужно разбить на кампании / группы / объявления
- Выбираешь шаблон под intent (informational / transactional / branded / navigational)
- Проверяешь будет ли заголовок / текст в рамках лимитов Direct
- Подбираешь минус-слова из не-целевых intent в том же CSV
- Планируешь структуру naming (`[intent]_[geo]_[product]` для кампаний, `[cluster_id]_[marker]` для групп)
- Готовишь batch ≥ 100 креативов — нужен canary-план
- Получил ссылку на лендинг + CSV кластеров → нужны рекламные объявления Direct

## Do not use this skill when

- Реально вызываешь Direct API (Ads.add, moderate, polling статусов) → `yandex-direct` skill для envelope + services
- Юр-проверка для регулируемых ниш (медицина, фарма, БАД, азартные игры, алкоголь) → `legal-ru-marketing` skill
- Google Ads / VK Ads / TG Ads → их специализированные skills
- SEO-семантика / органический поиск → `seo-specialist` агент или SEO skills
- Контент-план / посты в соцсетях (не реклама) → `copywriter`

## Purpose

Скилл даёт ads-specialist знания и шаблоны для написания качественных объявлений Яндекс.Директа по кластерам Key Collector CSV. Покрывает: per-field лимиты (с учётом правила «пунктуация в отдельном счётчике для доп. заголовка + текст»), стилистические запреты, intent-шаблоны, стратегию маппинга кластеров на структуру Direct, canary-протокол для batch'ей. Финальная валидация ложится на Direct API при загрузке — клиентского валидатора в скилле нет.

## Capabilities

### Landing page research (ОБЯЗАТЕЛЬНО перед креативами)

→ `references/landing-page-research.md`

### Лимиты и модерация

Per-field лимиты символов для всех форматов Direct (ТГО, РСЯ, Видео, СмартБаннер, МастерКампания, ДинамическиеОбъявления): заголовок 1 — 56 симв., заголовок 2 — 30 симв. + 15 пунктуации, текст — 81 симв. Ограничения по возрастным маркерам (18+), лимиты на уровне аккаунт / кампания / группа.

→ `references/limits-and-moderation.md`

### Запрещённые и нежелательные паттерны

Список стилистических запретов, за которые Direct снижает CTR или отклоняет при модерации: CAPS в заголовке, восклицательный спам (!!!), эмодзи в headline, превосходные степени («лучший», «№1», «самый»), цена без оговорки «от», запрещённые спецсимволы.

→ `references/style-and-avoid.md`

### CSV-workflow Key Collector

Пайплайн обработки выгрузки Key Collector: формат файла (UTF-8 BOM, разделитель `;`), 25 стандартных колонок, группировка по полю «Кластер», правило «минимум 2 объявления на кластер», фильтрация нецелевых intent в минус-слова.

→ `references/csv-workflow.md`

### Стратегия маппинга кластеров на Direct

Decision-таблица: когда 1 кластер = 1 группа, когда N кластеров объединяются в одну кампанию. Naming-конвенция для кампаний и групп, stable ID, canary-протокол для загрузки batch ≥ 100 кластеров (5 % пробный запуск → анализ → полная волна).

→ `references/cluster-to-campaign-strategy.md`

### Шаблоны объявлений по intent

4 intent × 2 шаблона каждый: заголовок 1, заголовок 2, текст объявления, 4 быстрые ссылки, 4 уточнения. Анти-шаблоны (что не писать под каждый intent). Покрывает: informational, transactional, branded, navigational.

→ `references/composition-templates.md`

### Форматы и типы кампаний (overview)

Обзор форматов объявлений Direct: размеры баннеров РСЯ, особенности ТГО, СмартБаннер, ДинамическиеОбъявления, МастерКампания. Типы кампаний и критерии выбора между ними.

→ `references/ad-formats.md`, `references/campaign-types.md`

### Бенчмарки 2026

Ориентировочные CTR / CPC / CPL по нишам (e-commerce, недвижимость, авто, услуги, B2B SaaS и др.) для оценки реалистичности KPI клиента.

→ `references/benchmarks-2026.md`

### Таргетинг и ключевые слова

Операторы соответствия (точное, фразовое, широкое), минус-слова на уровне кампании и группы, аудиторные таргетинги, геотаргетинг, расписание показов.

→ `references/targeting-and-keywords.md`

## API Reference

| Reference | Когда грузить | Что внутри |
|---|---|---|
| `landing-page-research.md` | перед написанием креативов для нового клиента | как через WebFetch вытащить бренд/услуги/USP/proof/гарантии/CTA с лендинга, как использовать данные в Title/Text/callouts |
| `limits-and-moderation.md` | при написании каждого креатива | per-field char-лимиты ТГО/РСЯ/Видео/Смарт/МК/ДО, 18+, лимиты кампания/группа/аккаунт |
| `style-and-avoid.md` | при ревью креатива | CAPS, !!!, эмодзи в headline, «лучший/№1», спецсимволы, без оговорки «от» в цене |
| `csv-workflow.md` | при работе с Key Collector CSV | формат UTF-8 BOM `;`, 25 колонок, пайплайн «Read → group by Кластер → 2+ ads per cluster» |
| `cluster-to-campaign-strategy.md` | при структурировании кампаний | decision-таблица 1-к-1 vs N-кластеров, naming, stable IDs, canary-протокол ≥ 100 кластеров |
| `composition-templates.md` | при написании конкретного объявления | 4 intent × 2 шаблона × (заголовок + 2-й + текст + 4 ссылки + 4 уточнения), анти-шаблоны |
| `ad-formats.md` | overview форматов | базовый обзор форматов Direct |
| `campaign-types.md` | выбор типа кампании | (унаследовано) |
| `benchmarks-2026.md` | оценка плановых CTR/CPC | (унаследовано) |
| `targeting-and-keywords.md` | подбор таргетинга | (унаследовано) |

## Decision table: задача → reference

| Что ты делаешь | Какой reference грузить первым |
|---|---|
| Пишу первое объявление для нового клиента | `landing-page-research.md` → `composition-templates.md` → проверка лимитов |
| Сел писать объявление под кластер | `composition-templates.md` → проверь `limits-and-moderation.md` → ревью по `style-and-avoid.md` |
| Получил CSV, не знаешь с чего начать | `csv-workflow.md` → `cluster-to-campaign-strategy.md` |
| Готов залить 130+ кластеров одной волной | `cluster-to-campaign-strategy.md` (раздел canary) ОБЯЗАТЕЛЬНО |
| Запрос: «какие лимиты для headline?» | `limits-and-moderation.md` (раздел ТГО) |
| Запрос: «можно ли писать «лучший»?» | `style-and-avoid.md` |

## When to load yandex-direct (API skill)

`yandex-direct-creatives` (этот скилл) — только КОНТЕНТ объявлений + структура кампаний.

`yandex-direct` (отдельный скилл) — для **реальной отправки** через API: envelope JSON-RPC, OAuth, services Campaigns/Ads/Keywords/Reports.

Грузи `yandex-direct` ДОПОЛНИТЕЛЬНО к этому скиллу когда:
- реально вызываешь `Ads.add` / `Ads.moderate`
- паршишь Reports v5 TSV ответ с polling
- управляешь ставками через BidsService / KeywordBidsService

## Behavioral Traits

- Всегда проверяет лимиты символов перед финальной версией объявления — даже если кажется, что текст короткий
- При получении CSV первым делом открывает `csv-workflow.md`, не начинает маппинг вслепую
- Для batch ≥ 100 кластеров всегда предлагает canary-план — никогда не заливает всё сразу
- При выборе шаблона называет intent явно (informational / transactional / branded / navigational), не угадывает

## Important Constraints

- NEVER пропускать проверку лимитов — модерация Direct отклоняет объявление автоматически, без предупреждения
- NEVER вызывать Direct API из этого скилла — для этого есть `yandex-direct`
- NEVER писать объявления для регулируемых ниш без пометки «требуется `legal-ru-marketing`»
- ALWAYS называть intent кластера явно перед выбором шаблона
- ALWAYS включать минус-слова из нецелевых intent при маппинге CSV

## Related Skills

- `yandex-direct` — envelope JSON-RPC, OAuth, services Campaigns/Ads/Keywords/Reports для реальной отправки
- `legal-ru-marketing` — юридические ограничения для регулируемых ниш в российской рекламе
