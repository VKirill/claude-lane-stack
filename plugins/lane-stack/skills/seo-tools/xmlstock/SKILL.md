---
name: xmlstock
description: "[RU: интеграция xmlstock.com — Яндекс Search API, Яндекс Live, Google XML Search, парсинг SERP/картинок/видео/новостей] xmlstock.com REST API — RU reseller дешёвых XML-лимитов для Яндекс Search API (~18 руб/1000 vs официальные 480), Яндекс Live (живая выдача с ads/scroller/related), Google XML Search. Async/hybrid режимы с req_id и кодом 210/202, params query/lr/page/domain/device/tbm/groupby/sortby/filter/maxpassages/related/ads, parsing картинок (tbm=images), видео (tbm=video), новостей (tbm=news, только Google), мобильная выдача (device=mobile), POST-режим с XML-body. Use when: xmlstock, xmlstock.com, яндекс xml, yandex search api, yandex.xml, яндекс лимиты, парсинг выдачи яндекса, парсинг google, google xml search, проверка позиций, проверка индексации, SERP parsing, парсинг сниппетов, req_id, delayed=1, tbm=images, scroller, related searches, парсинг рекламной карусели, key collector xml, topsite xml, проверка позиций сайта, ошибка 210, ошибка 202, ошибка 32, hybrid режим. SKIP: Mutagen (→mutagen, frequency/Wordstat, not SERP scraping); proxy для собственного скрапинга SERP (→proxy6, dramatically more expensive at scale); Bing/DuckDuckGo (different provider, xmlstock не поддерживает); официальное Yandex Search API напрямую (~100x дороже); Google Custom Search JSON API (different surface, limit 100/day free)."
stacks:
  - xmlstock
  - ru-seo
  - python
  - nodejs
tags:
  - seo
  - ru
  - serp
  - yandex
  - google
  - parsing
  - xml
  - positions
source: vechkasov-global-skills
risk: high-stakes
---

<!-- versions:start -->

## 🎯 Version Requirements (August 2026)

**Primary pins:**
- xmlstock API: `docs-only (stable JSON/XML REST, no version path; https://xmlstock.com/{yandex|yandexlive|google}/{xml|json|html}/)`
- Python: `3.14.x`
- Node.js: `24.x (Active LTS)`

> Source of truth: [STACK_VERSIONS.md](../../STACK_VERSIONS.md) — verified 2026-08-24

<!-- versions:end -->

## Usage

Loaded automatically when its description matches the active task. Read only the section you need, then follow the link to the relevant reference file for full detail.

## Use this skill when

- Парсинг позиций сайта в Яндексе или Google по списку ключей с региональностью (`lr=`, `domain=`, `device=`)
- Проверка индексации страниц / количества проиндексированных страниц через `query=site:domain.com`
- Сбор SERP-снапшотов (ТОП-10/50/100) для аналитики, мониторинга конкурентов, кластеризации
- Парсинг живой выдачи Яндекса с дополнительными блоками: реклама Яндекс.Директ (`ads=1`), товарная карусель (`scroller=1`), Related Searches (`related=1`)
- Парсинг Яндекс/Google картинок (`tbm=images`), Google новостей (`tbm=news`), видео (`tbm=video`)
- Обратный поиск по картинкам в Яндексе через `query=image:URL` + `tbm=images`
- Замена прямого скрапинга через прокси/решение капч на стабильный API за ~18 руб/1000 запросов (≈100× дешевле официального Yandex Search API)
- Интеграция Key Collector / Topvisor / Site-Control / Topsite через готовый URL `https://xmlstock.com/{engine}/xml/?user=...&key=...`
- Building a Python / Node.js client с async-polling req_id, dedup, balance pre-check, retry на 210/202 с exponential backoff
- Asynchronous (`delayed=1`) batch SERP parsing для больших объёмов с гибким контролем (нет квот, только пропускная способность их сервера)

## Do not use this skill when

- Сбор частотностей / уровня конкуренции / Wordstat — это **не** делает xmlstock. Использовать `mutagen` (cascade marker) для wordstat_qso и `strong`
- Собственный скрапер SERP через прокси / разгадывание капч — на масштабах >5к запросов это дороже и менее стабильно. Если запросов очень мало (<100/мес) — пользователь не обязан подключать сторонний сервис; для прокси — `proxy6` (cascade marker)
- Других поисковиков: Bing, DuckDuckGo, Baidu — xmlstock поддерживает только Яндекс и Google
- Прямой Yandex Search API (api.search.yandex.ru) — другой endpoint, другие цены, другая аутентификация. Этот скилл — про reseller xmlstock, а не про официальный API
- Google Custom Search JSON API (CSE) — другой surface, JSON-only, 100 бесплатных/день; разные параметры
- Использование собранных данных downstream (HTTP-плeerинг, БД, аналитика) — это работа runtime-скиллов (`httpx`, `nodejs`, `postgresql`)
- Парсинг SERP-фич сложнее базовых блоков (People Also Ask с раскрытием, Knowledge Graph, Featured Snippets с разметкой) — xmlstock возвращает только то, что описано; для подобного — SerpApi/DataForSEO (другие сервисы, дороже)

## Purpose

xmlstock.com — крупнейший российский reseller XML-лимитов для Яндекс Search API (платный новый API, заменивший бесплатный Яндекс.XML с 1 ноября 2023) и аналогичный сервис для Google. Цены: ~18 руб/1000 запросов к Яндекс XML (vs 480 руб официальные днём и 360 ночью — ≈100× дешевле благодаря договорённости с командой Яндекса), сопоставимые на Google. Поддерживает все официальные параметры выдачи плюс Live-парсинг с экстра-блоками (Яндекс.Директ ads, товарная карусель, related searches), мобильную выдачу, картинки/видео/новости, async-режим с req_id.

This skill is **high-stakes** because:

1. **Платно за каждый ответ**. За ошибки 1, 15, 18, 19, 37, 210, 10001, 10002 деньги списываются (запрос обработан, формально корректен). За остальные ошибки — нет.
2. **Async double-spend trap**: повторная отправка `delayed=1` для того же запроса создаёт **новую** задачу с новым req_id и списанием. Нужно persist req_id и поллить только по нему.
3. **Hybrid режим (по умолчанию для Яндекс XML)** возвращает либо результат, либо `error code=210` (запрос поставлен в очередь). Повторный запрос за 210-результатом **не** тарифицируется, но требует терпения 20-30 секунд между retry, иначе ловишь 201 (повторный запрос из кеша не чаще раза в 30 с — для async).
4. **Region (`lr=`) драматически меняет SERP**. Промах с регионом = собранные позиции бесполезны = деньги выброшены. Перед батчем — проверить настройки по умолчанию в ЛК и явно передавать `lr` в URL.
5. **Limit 250 результатов** в Яндекс XML — попытка запросить 3-ю страницу при `groupby=100` вернёт error 18.
6. **Rate limits**: Яндекс XML — 50 потоков / 100 req/s рекомендованно; Яндекс Live — 10 потоков / 10 req/s; Google XML — 15 потоков / 15 req/s. Превышение → 55, 503. Большие пакеты с интервалом *хуже* равномерного потока — часть отсекается.
7. **Hybrid vs Synchronous vs Async**. Синхронный режим отключен с 1 марта 2025. По умолчанию — гибридный. Async (`delayed=1`) — отдельная семантика с req_id.
8. **Кириллические домены** в Punycode или нет — `punycode=1/0`. Несоответствие downstream-обработке → битые ссылки и ложные «не найдено».
9. **Билинговый порядок**: списание происходит при первой отправке запроса в API. На стороне xmlstock запрос помнится и обрабатывается по мере готовности ответа Яндекса. Re-fetch по тому же req_id или поллинг 210 — бесплатные.

Скилл owns provider-domain knowledge: эндпоинты, параметры, async lifecycle, rate-limit recipes, error semantics, биллинговая модель. HTTP-плeerинг — это `httpx` / `nodejs`.

## Using via mcp-xmlstock

When working inside the **mcp-xmlstock** MCP server, SERP queries are wrapped into
dedicated tool calls — no manual URL construction, no auth params in code, no 210/202
retry loops, and no XML parsing required. Use `xmlstock_yandex_serp({query, lr, ...})`
for Yandex SERP and `xmlstock_google_serp({query, hl, page, ...})` for Google;
responses are cached for 24 hours by default (pass `force_refresh: true` to bypass).
Errors (codes -34, 200, 42, 32, etc.) surface as MCP isError responses with `billed`
hints. Use `xmlstock_usage_stats()` for the local call counter and a link to your
XMLStock dashboard for the actual credit balance.

## Capabilities

### API client setup и базовая модель запросов

Три независимых эндпоинта: `https://xmlstock.com/yandex/xml/`, `https://xmlstock.com/yandexlive/{xml|json|html}/`, `https://xmlstock.com/google/{xml|json|html}/`. Аутентификация — `user=<ID>&key=<API_KEY>` в query-string (для Live и Google доступны также JSON и HTML форматы; для Яндекс XML — только XML). Ключ можно ротировать в любой момент в ЛК. Параметры в URL имеют приоритет над дефолтами в Настройках ЛК.

> Full reference: [references/setup.md](references/setup.md)

### Яндекс Search API (yandex/xml) — параметры и режимы

Поддерживает: `query`, `lr`, `l10n`, `sortby` (rlv|tm с order), `filter` (moderate|none|strict), `maxpassages` (1-5), `groupby` (плоский 10-100 или flat/deep с attr/groups-on-page/docs-in-group), `page` (0-based, hard cap 250 результатов), `domain` (ru|by|kz|com|com.tr|uz), `device` (desktop|mobile|tablet|iphone|android), `noreask` (1 = без исправления опечаток). Поисковые операторы: `mime:`, `lang:`, `date:`, `site:`. POST-режим с XML-body для сложных параметров. Режимы: hybrid (default, может вернуть 210), async (`delayed=1` + req_id), synchronous (отключен).

> Full reference: [references/yandex-xml.md](references/yandex-xml.md)

### Яндекс Live — живая выдача с экстра-блоками

Эндпоинт `yandexlive/{xml|json|html}/`. Один запрос = 10 результатов (фиксированно). Дополнительные блоки: `ads=1` (топ + нижний рекламный блок Яндекс.Директ с адресом, заголовком, текстом, телефоном, ИНН), `scroller=1` (товарная карусель с ценой/изображением/ссылкой/ИНН), `related=1` (Related Searches внизу страницы). `tbm=images` (30 результатов картинок) с обратным поиском `query=image:URL`, `tbm=video` (18 результатов), `tbm=turbo` (тарифицируется доп., HTML-формат, минимум ошибок). Фильтры по периоду через `within=` (77=сутки, 1=2 недели, 2=месяц) — **только** для XML/JSON. Доп. параметры: `lang`, `rstr`, `punycode`, `hlword`, `noreask`.

> Full reference: [references/yandex-live.md](references/yandex-live.md)

### Google XML Search — параметры и spec

Эндпоинт `google/{xml|json|html}/`. Поддерживает: `query` (с операторами `site:`), `lr` (с авто-сопоставлением кодов регионов Яндекса → Google по запросу в техподдержку), `page`/`start`, `domain` (com|ru|com.ua|by или числовое 143=google.ru), `device`, `tbm` (images|news|video), `tbs` (период: qdr:s/n/n10/h/d/w/m/y или конкретный диапазон `cdr:1,cd_min:1/2/2023,cd_max:3/2/2023`), `hl` (язык UI), `ads=1` (не работает для РФ — санкции Google), `related=1` (объединённо: Related Questions + Related Searches), `filter=1` (показать скрытые «very similar» результаты), `punycode`, `hlword`, `nfpr` (1=без исправления опечаток), `safe` (на/off/empty для размытия). `groupby` больше не работает — Google ограничил выдачу до 10/страница.

> Full reference: [references/google-xml.md](references/google-xml.md)

### Async / Hybrid / Synchronous режимы и req_id lifecycle

Synchronous — отключен. Hybrid (default для Яндекс XML, всегда для Live и Google) — обычный GET, либо результат, либо `<error code="210">` (запрос в очереди). Async — `delayed=1`, ответ — `<req_id>spr3s0ngc4citnd30muk</req_id>`, потом отдельный GET с `req_id=` пока не вернёт результат (или `<error code="202">` ещё не готов). Polling cadence: **20-30 секунд** между попытками. Чаще раза в 30 с по тому же req_id → `error 201` (повторный из кеша). Лимит хранения задачи ограничен — `203` означает что req_id больше нет. Списание: на этапе **получения req_id**, дальнейшие fetch-ы по req_id бесплатные. **Critical**: persist req_id, не отправлять одинаковые `delayed=1` запросы дважды.

> Full reference: [references/async-and-req-id.md](references/async-and-req-id.md)

### Error codes — биллинговая семантика и retry-стратегия

Полная таблица ошибок с пометками: какие тарифицируются (1, 15, 18, 19, 37, 210, 10001, 10002), какие нет. HTTP 500-502 = перезапрос; 503 = превышен RPS, exponential backoff. Внутри 200-х: 32 = суточный лимит ЛК, 55 = превышен RPS на сервере, 200 = денег на счету нет (надо пополнять), -34 = неверный user/key, 101 = техработы на стороне xmlstock, 18 = либо невалидный XML body, либо запрошена страница > 250 результатов (особый кейс), 210/202 = async/queue retry, 15 = по запросу ничего не нашлось (тарифицируется — запрос корректен).

> Full reference: [references/errors.md](references/errors.md)

### Rate limits и concurrency-стратегия

Рекомендованная concurrency: Яндекс XML — 50 одновременных потоков; Яндекс Live — 10; Google XML — 15. Pacing — отправлять следующий запрос **сразу** по получении результата, не накапливать пакеты. Большой пакет (>500-1000 одновременно) → часть в очередь, часть отсекается, эффективная скорость ниже равномерного потока. При больших объёмах — заранее писать в техподдержку для договорённости. Превышение → код 55 или HTTP 503; правильный backoff: exponential 2→4→8→16 с jitter, max 60 с.

> Full reference: [references/rate-limits.md](references/rate-limits.md)

### Реалистичные клиенты — Python (httpx) и Node.js

Готовые шаблоны: connection pool, балансовый pre-check (`mutagen`-аналогом нет, xmlstock не предоставляет endpoint /balance — мониторить через личный кабинет или через ответ 200 «денег нет»), dedup по `(engine, query, lr, domain, device, page)` хэшу, persistence req_id в Redis/PG, retry на 210/202/55/503 с jitter, parsing XML через `lxml` / `fast-xml-parser`. POST-режим с XML body для сложных групп. Сравнение с прямым скрапингом через `proxy6`: cost, reliability, surface (xmlstock даёт официальные структурированные сниппеты Яндекса, скрапер — только то, что отрендерил браузер).

> Full reference: [references/integration.md](references/integration.md)

## Quick reference

| Engine | Endpoint | Format(s) | Default concurrency | Особенности |
|---|---|---|---|---|
| Яндекс XML | `xmlstock.com/yandex/xml/` | XML | 50 поток. / 100 RPS | hybrid+async, до 100/стр, max 250 рез., POST-body |
| Яндекс Live | `xmlstock.com/yandexlive/{xml,json,html}/` | XML / JSON / HTML(turbo) | 10 поток. / 10 RPS | 10 рез/стр, ads/scroller/related, tbm=images/video |
| Google XML | `xmlstock.com/google/{xml,json,html}/` | XML / JSON / HTML | 15 поток. / 15 RPS | 10 рез/стр (Google cap), tbm=news/images/video, tbs= |

| Параметр | Где работает | Заметка |
|---|---|---|
| `query` | все | до 40 слов / 400 символов; операторы `site:`, `mime:`, `lang:`, `date:`, `image:` (только tbm=images) |
| `lr` | все | id региона; **обязательно проверять под задачу** |
| `domain` | все | ru/by/kz/com/com.tr/uz (Яндекс), com/ru/com.ua/143 (Google) |
| `device` | все | desktop/mobile (+ tablet/iphone/android в Яндексе) |
| `tbm` | yandexlive, google | images / video / news (news — только Google) / turbo (только yandexlive) |
| `page` | все | 0-based; Яндекс XML cap = страница до 250-го результата |
| `groupby` | yandex/xml only | flat/deep + attr=d/mode=deep/groups-on-page/docs-in-group; в Google устарел |
| `delayed=1` | yandex/xml | async режим, ответ — req_id |
| `req_id` | yandex/xml | retrieval по async-задаче, поллить ≥ 20-30 с |
| `ads` | yandexlive, google | 1 = показать рекламные блоки; в Google не работает для РФ |
| `scroller` | yandexlive | 1 = товарная карусель |
| `related` | yandexlive, google | 1 = Related Searches (+ PAA в Google) |
| `tbs` | google | qdr:h/d/w/m/y или cdr:1,cd_min:..,cd_max:.. |
| `within` | yandexlive (XML/JSON) | 77=сутки, 1=2 недели, 2=месяц |
| `noreask` / `nfpr` | yandex / google | 1 = без исправления опечаток |
| `punycode` | yandexlive, google | 1 = кирилл. домены в punycode |
| `hlword` | yandexlive, google | 1 = выделять ключи тегом hlword |
| `safe` | google | on/off/(empty=blur) |

| Код ошибки | Тарифицируется? | Что делать |
|---|---|---|
| 1, 15, 18, 19, 37, 10001, 10002 | **да** | проверить query, не повторять с теми же параметрами |
| 210 | **да** (на yandex/xml) | retry через 20-30 с (есть запоминание задачи) |
| 202 | нет | retry через 20-30 с по req_id |
| 201 | нет | подождать (cache-cooldown 30 с) |
| 203 | нет | задача истекла, заново `delayed=1` |
| 55, HTTP 503 | нет | backoff, снизить concurrency |
| 32 | нет | поднять лимит в ЛК или ждать суточный сброс |
| 200 | нет | пополнить баланс |
| -34, 42, 31 | нет | проверить user/key |
| 101 | нет | техработы, ждать |
| 500-502 | нет | retry |

## Common mistakes

- **Повторная отправка `delayed=1` для того же запроса** — создаёт новую задачу с новым req_id и **новым списанием**. Fix: persist req_id (Redis/PG), retry **только** по нему.
- **Слать большой батч пачкой с интервалом** (например 1000 одновременно, потом пауза, потом ещё 1000). Часть встанет в очередь, часть отсечётся как 55. Fix: ровный поток, одна задача в полёте → следующая. Семафор на 50/10/15 в зависимости от engine.
- **Запрос страницы >250-го результата в Яндекс XML** → `error 18`. Fix: понять hard cap, не паджинировать дальше.
- **Не передавать `lr=`** и полагаться на дефолт в ЛК — собранные позиции окажутся для непредсказуемого региона. Fix: всегда явно `lr` в URL.
- **Перепутать `domain=` и `lr=`** — `domain` — это **зона поиска Яндекса/Google** (ru/by/com), а `lr` — **регион ранжирования**. Это разные вещи; собирать выдачу для Беларуси можно как с `domain=by` так и с `domain=ru&lr=149`. Документацию читать внимательно.
- **Поллить req_id чаще раза в 30 с** → `error 201`. Fix: уважать минимальный 20-30 с интервал.
- **Считать `error 15` (ничего не найдено) бесплатным** — он тарифицируется как корректный ответ. Fix: dedup и не повторять заведомо пустые запросы.
- **Использовать `ads=1` для Google в РФ** — не работает (санкции Google). Fix: для рекламы — Яндекс Live, для Google — только органика.
- **Тащить `device=mobile` в Яндекс XML без проверки** — может вернуть неожиданную выдачу. Лучше явно тестировать на образцах перед батчем.
- **Не различать hybrid и async** — на hybrid (`без delayed=1`) при получении `210` retry **тот же URL** (запрос уже запомнен), а **не** новый. На async retry — по `req_id=`, не отправляя `query=` повторно.
- **POST-body с неэкранированным `&`** → `error 18`. Fix: правильное XML-экранирование (`&amp;`).
- **Не сжимать ответ** — XML-ответы крупные; включать gzip на стороне клиента.

## Red flags — STOP and verify

- О тебя пишут "почему так дорого получилось" — ты, скорее всего, дважды отправил `delayed=1` для тех же ключей. Проверь логи на дубликаты `req_id` и наличие persistence-слоя.
- Позиции "пляшут" между запусками — почти всегда дело в плавающем `lr` (дефолт в ЛК) или промахе device/domain. Зафиксируй явно.
- 503 / 55 валятся пачкой — concurrency задрана. Понизь воркеров до 50/10/15 (Yandex XML / Live / Google).
- `error 200` посреди батча → деньги кончились. Останови воркер, не закидывай оставшиеся ключи в очередь повторно.

## See also

- `mutagen` — частотности и `strong` (не пересекается с xmlstock, дополняет)
- `proxy6` — собственный скрапинг SERP через прокси (альтернатива, дороже на масштабах, менее стабильно)
- `httpx`, `nodejs` — HTTP-плeerинг для собственного клиента
- `postgresql`, `redis` — persistence req_id и dedup ключей
