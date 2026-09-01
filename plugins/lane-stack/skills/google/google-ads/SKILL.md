---
name: google-ads
description: |
  Спецификации Google Ads для российского рынка 2026 — 8 форматов (RSA / Performance Max / Display / Demand Gen / Video / App / Call / Shopping), полный набор character limits (headline 30, description 90, long-headline 90, business-name 25 и т.д.), creative-frameworks под RSA-логику динамической сборки, Google Ads Policies (запрещённые ниши, ограничения по claims, financial services, healthcare, gambling), pre-launch checklist, бенчмарки CTR/CPC/CR/QS по индустриям, **критичный российский контекст** (Google Ads недоступен для размещения в РФ с 22.09.2022 — клиентам с РФ-таргетом перенаправлять на Яндекс.Директ; российские клиенты могут таргетить только зарубеж через зарубежные юрлица). Включает **Python-валидатор `scripts/validate-ads.py`** для проверки длины headlines/descriptions/paths перед запуском. Use when: «Google Ads», «гугл реклама», «РСЯ vs Google», «лимиты для RSA», «PMax кампания», «headline в Google», «character limit», «pre-launch checklist Google», «бенчмарки CTR Google», «можно ли запустить Google Ads в Россию», «таргет на США через Google». SKIP: Я.Директ (→yandex-direct-creatives), VK Ads, TG Ads (→telegram-ads-spec), SEO / органика (→seo-evidence-based-2026), Google Search Console / аналитика (→google-search-console / google-analytics), Google Ads API программно (→google-ads-api если будет создан).
stacks:
  - google-ads
  - paid-media
tags:
  - google-ads
  - rsa
  - performance-max
  - pmax
  - display-ads
  - demand-gen
  - youtube-ads
  - paid-search
  - character-limits
  - validator
  - russian-market
source: vechkasov-global-skills
risk: high-stakes
---

## Usage

Загружается автоматически когда задача относится к Google Ads. **Перед любым креативом — проверь `russia-context.md`**: возможно, клиенту вообще не Google Ads нужен, а Я.Директ. Перед сдачей креатива клиенту — **обязательно прогон через `scripts/validate-ads.py`**.

## Use this skill when

- Запуск / настройка / аудит кампании Google Ads — Search (RSA), Performance Max, Display, Demand Gen, YouTube Video, App, Call, Shopping
- Написание headlines / descriptions для RSA или PMax с обязательной валидацией по символам
- Перенос рекламной воронки с Я.Директа на Google (для зарубежных рынков) или обратно
- Расчёт бюджета и прогноз метрик: «сколько CPC в нише X», «какой Quality Score целевой», «какой CTR ожидать»
- Compliance check: можно ли рекламировать [продукт] в Google Ads — финансы / медицина / БАД / алкоголь / гэмблинг / крипто / политика / здравоохранение
- Аудит существующих RSA: «почему низкий CTR», «почему ad strength = Poor / Average»
- Подготовка к запуску: pre-launch checklist
- Российский B2B/B2C клиент с международной экспансией — выбор каналов (Google Ads на зарубеж vs Я.Директ на РФ)

## Do not use this skill when

- Задача про Я.Директ / TG Ads — `yandex-direct-creatives`, `telegram-ads-spec` (VK Ads spec снят из каталога)
- Задача про органическое продвижение в Google — это SEO (`seo-evidence-based-2026`)
- Задача про Google Search Console, GA4, GTM — это аналитика (`google-search-console`, `google-analytics`, `google-tag-manager`)
- Программная работа с Google Ads API (создание кампаний через код) — это отдельный skill (если/когда `google-ads-api` будет создан)
- Креатив-визуал баннеров / image assets — делегируй `worker-image-designer` (агент)
- Российский клиент хочет размещение **в РФ** через Google — **Google Ads недоступен**, перенаправляй на `yandex-direct-creatives`

## Purpose

**Google Ads** — крупнейшая глобальная платная-рекламная платформа Google (Search + Display + YouTube + Demand Gen + Shopping + App). Для российского рынка 2026 — это инструмент с ограниченной применимостью из-за блокировки размещения в РФ с 22.09.2022, но **критически важный** для двух категорий клиентов:

1. **Российские бренды с экспортной стратегией** — таргетятся на США / Европу / СНГ через зарубежное юрлицо.
2. **Зарубежные клиенты + русскоязычная аудитория вне РФ** — Казахстан, Беларусь, Армения, Грузия, диаспора в US/EU.

Skill покрывает **8 форматов** Google Ads с актуальными лимитами 2026, политики, бенчмарки, и — что критично — содержит **Python-валидатор** для проверки длины headlines/descriptions перед запуском (Google режет креатив на превышении). Используется агентом `ads-specialist` (или напрямую) при любой работе с Google Ads.

Skill — knowledge-base. Само исполнение (запуск, оплата, оптимизация) — на стороне клиента / маркетолога в кабинете Google Ads.

## Capabilities

### Российский контекст (читать первым)

С 22.09.2022 Google приостановил продажу рекламы для размещения в РФ. Российские аккаунты заморожены, российские карты не принимаются. **Если клиент таргетит в РФ — Google Ads не вариант**, направляй в Я.Директ. Полная схема + что доступно / недоступно / альтернативы → [references/russia-context.md](references/russia-context.md).

### 8 рекламных форматов Google Ads

Каждый формат — со своими лимитами и логикой:

- **RSA** (Responsive Search Ads) — поиск, динамическая сборка из 3-15 headlines + 2-4 descriptions
- **Performance Max** (PMax) — кросс-канальный AI-driven с asset groups
- **Display Responsive** — баннеры в Google Display Network
- **Demand Gen** — bыло Discovery Ads, YouTube Shorts + Discover feed + Gmail
- **Video** (YouTube TrueView / Bumper / In-Stream / In-Feed)
- **App Campaigns** (UAC) — продвижение мобильных приложений
- **Call Ads** — поисковые объявления с прямым звонком
- **Shopping Ads** — feed-based catalog ads (Google Merchant Center)

Полное описание каждого формата — [references/ad-formats.md](references/ad-formats.md).

### Character limits — все в одной таблице

Лимиты различаются по формату и часто меняются в Google. Single source of truth — [references/character-limits.md](references/character-limits.md). Резюме самых ходовых:

- **Headline**: 30 символов (RSA, PMax, Display, App, Call)
- **Description**: 90 символов
- **Long headline**: 90 символов (PMax, Display, Demand Gen)
- **Short description (PMax)**: 60 символов
- **Business name**: 25 символов
- **Path**: 15 символов (×2 для RSA)
- **Demand Gen headline**: 40 символов (исключение)
- **Sitelink**: 25 символов + descriptions ≤35 (×2)

### Creative frameworks под RSA-логику

RSA — это **не один баннер**, это **набор assets**, из которого Google динамически собирает разные комбинации для разных пользователей. Правила написания headlines:

- Каждый headline = самостоятельная фраза, **не "продолжение предыдущего"**
- 8-12 headlines (даёт +30% performance vs минимум 3)
- Diversity > Pinning — фиксируй позиции редко, только когда юридически обязан
- Включай keyword в 2-3 headlines (но не во все — Google это видит как spam)
- Headline 1 пинни если он юридически обязателен (brand disclaimer, lic. info)

Полные фреймворки + примеры до/после — [references/creative-frameworks.md](references/creative-frameworks.md).

### Google Ads Policies — что нельзя

Каждая ниша имеет свои ограничения. Критические категории:

- **Restricted** (можно с ограничениями): алкоголь, гэмблинг, healthcare, политика, финуслуги, копирайтные товары
- **Запрещено полностью**: counterfeit, dangerous products, hate speech, scam, child-related sexual content
- **Editorial**: clarity, no clickbait, no excessive punctuation/capitalization, профессиональный язык
- **Misrepresentation**: запрещён ложный urgency, fake guarantees, deceptive landing pages

Полный разбор политик + что делать если креатив disapproved → [references/policies.md](references/policies.md).

### Бенчмарки 2026 по индустриям

CTR / CPC / CR / QS реальные числа по 12+ индустриям (B2B Tech, E-commerce, Healthcare, Финуслуги, Education, Travel, SaaS, Real Estate, Legal, и т.д.). [references/benchmarks.md](references/benchmarks.md).

### Pre-launch checklist

35-пунктовый чек-лист перед запуском (technical setup + creative + measurement + compliance). Не проходишь — не запускаешь. [references/pre-launch-checklist.md](references/pre-launch-checklist.md).

### Validator script (Python)

`scripts/validate-ads.py` — CLI-валидатор креатива по character limits. Принимает YAML или JSON, выдаёт structured report с pass/fail и рекомендациями. Корректно работает с Unicode (русский, эмодзи). [references/validator-usage.md](references/validator-usage.md) — usage examples.

**Запуск**:
```bash
python ~/.agents/skills/google/google-ads/scripts/validate-ads.py creative.yaml
```

## Behavioral Traits

- **Перед любым креативом проверяет российский контекст** — если клиент таргетит в РФ, перенаправляет на Я.Директ без вариантов.
- **Каждый креатив перед сдачей клиенту прогоняет через `validate-ads.py`** — не на глаз, не "примерно".
- Пишет 8-12 headlines, не минимум 3 — Google рекомендует diversity для performance.
- Не пиннит headlines / descriptions без юридической необходимости — pinning режет Quality Score.
- Каждый headline = самостоятельная фраза; не "продолжение".
- Включает keyword в 2-3 headlines, не во все — иначе Google помечает как spam.
- Для PMax обязательно собирает 5+ images, 1+ video, 5 headlines, 5 descriptions — иначе Asset Group не активируется.
- Для регулируемых ниш (финансы / healthcare / gambling / алкоголь) — сначала policies.md, потом креатив.
- При выборе формата: Search-intent → RSA; Lower-funnel + ROAS → PMax; Brand awareness → Demand Gen / Video.

## Important Constraints

- НИКОГДА не предлагай клиенту запустить Google Ads для размещения в **РФ** — это технически невозможно с 2022.
- НИКОГДА не сдавай креатив клиенту без прогона через validator — character limit overflow = ad disapproved.
- НИКОГДА не пиши headline >30 символов в надежде "Google обрежет красиво" — он просто отклонит ad.
- НИКОГДА не используй ALL CAPS в более чем одном слове на headline — Google режет по editorial.
- НИКОГДА не используй excessive punctuation: `!!`, `???`, `★★★`, `🔥🔥🔥` — automatic disapproval.
- НИКОГДА не обещай результаты которые не можешь обосновать в landing page (LP должна явно подтверждать оффер).
- ВСЕГДА проверяй landing page на: mobile-friendly + загрузка <3 сек + privacy policy + чёткий CTA — иначе QS = низкий.
- ВСЕГДА используй UTM-разметку + conversion tracking + Enhanced Conversions — без этого оптимизация невозможна.

## Related Skills

### Внутри ads-стека
- ✓ `yandex-direct-creatives` — Я.Директ; направление клиентов с РФ-таргетом
- ✓ `telegram-ads-spec` — TG Ads + посевы

### Compliance / creative
- ✓ `ad-creatives-frameworks` — 4U / AIDA / PAS для headline композиции
- ✓ `legal-ru-marketing` — RU compliance (НЕ применим для Google Ads вне РФ)

### Аналитика
- ✓ `google-analytics` — Google Analytics 4 для measurement
- ✓ `google-tag-manager` — Google Tag Manager для conversion tracking
- ✓ `google-search-console` — органика; не Ads

### Визуал
- ✓ `nano-banana` — генерация креативов через worker-image-designer agent

## API Reference

| Topic | File |
|---|---|
| Index, decision map по разделам | [references/REFERENCE.md](references/REFERENCE.md) |
| 8 рекламных форматов в деталях | [references/ad-formats.md](references/ad-formats.md) |
| **Character limits — единая таблица всех лимитов** | [references/character-limits.md](references/character-limits.md) |
| Creative frameworks под RSA-логику (headlines, descriptions, pinning, asset diversity) | [references/creative-frameworks.md](references/creative-frameworks.md) |
| Google Ads Policies — restricted / prohibited / editorial / misrepresentation | [references/policies.md](references/policies.md) |
| **Российский контекст** — блокировка с 2022, что доступно, альтернативы | [references/russia-context.md](references/russia-context.md) |
| Бенчмарки CTR / CPC / CR / QS по 12+ индустриям 2026 | [references/benchmarks.md](references/benchmarks.md) |
| Pre-launch checklist (35 пунктов) | [references/pre-launch-checklist.md](references/pre-launch-checklist.md) |
| Validator usage — как запускать `validate-ads.py`, формат input YAML, как читать output | [references/validator-usage.md](references/validator-usage.md) |

## Scripts

| Script | Purpose |
|---|---|
| `scripts/validate-ads.py` | CLI-валидатор character limits для всех 8 форматов Google Ads. Принимает YAML/JSON, выдаёт report. Корректно считает Unicode. |
