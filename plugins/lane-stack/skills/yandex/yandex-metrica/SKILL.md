---
name: yandex-metrica
description: "[RU: яндекс метрика, метрика api, logs api, цели метрики] Yandex.Metrika API via api-metrika.yandex.net with OAuth 2.0. Reporting API v1 (/stat/v1/data, /bytime, /drilldown, /comparison) with ym:s:/ym:pv:/ym:u: namespaces, filter DSL, attribution models; Logs API raw hits/visits lifecycle created→processed→cleaned, 10 GB/counter; Management API for counters/goals/filters CRUD. Quotas: 5000 req/day per user_login, 30 req/s per IP (10 for Logs), 3 parallel, 200 req/5min. Use when: яндекс метрика, metrika api, /stat/v1/data, logs api, raw hits export, ym:s:visits, counter_id, attribution, цели метрики. SKIP: Webmaster (→yandex-webmaster); Direct ads (→yandex-direct); GA4 (→google-analytics); AppMetrica (→appmetrica); CRM (→amocrm/bitrix24)."
stacks:
  - yandex-metrica
  - ru-analytics
  - python
  - nodejs
tags:
  - analytics
  - ru
  - yandex
  - metrika
  - attribution
  - logs-api
  - oauth
source: vechkasov-global-skills
risk: high-stakes
---

<!-- versions:start -->

## Version Requirements (May 2026)

**Primary pins:**
- Yandex Metrika API: `Reporting v1 (/stat/v1/data), Management v1 (/management/v1), Logs (/management/v1/counter/{id}/logrequests*) — stable, no deprecation notice`
- Base URL: `https://api-metrika.yandex.net`
- Python: `3.14.x`
- Node.js: `24.x (Active LTS)`

> Source of truth: [STACK_VERSIONS.md](../../STACK_VERSIONS.md) — verified 2026-08-24

<!-- versions:end -->

## Usage

Loaded automatically when its description matches the active task. Read only the section you need, then follow the link to the relevant reference file for full detail.

## Use this skill when

- Pulling traffic/source/goal/conversion reports via Reporting API (`/stat/v1/data`)
- Time-series via `/stat/v1/data/bytime` (charts grouped by day/week/month)
- Hierarchical drill-down (e.g. city → page → device) via `/stat/v1/data/drilldown`
- A/B segment or period comparisons via `/stat/v1/data/comparison`
- Raw hit/visit export via Logs API for ClickHouse / BigQuery / DuckDB
- Multi-touch attribution — first/last/last-significant/Yandex Direct/cross-device via `attribution=`
- CRUD on counters, goals, filters, representatives, operations via Management API
- Importing expenses, CRM data, offline conversions, user params via Data Import API
- Storing OAuth tokens with the right minimum scope (`metrika:read` / `metrika:write` / `metrika:offline_data`)
- Building a Python (`httpx`) or Node.js client with Logs API polling, 429/503 retry, `request_id` deduplication
- Detecting sampling (`sampled=true`, `sample_share`) and re-running with `accuracy=full` when needed

## Do not use this skill when

- Search Console-style queries / index / sitemap — that is **not** Metrika. Use `yandex-webmaster` (cascade marker)
- Yandex.Direct ad campaign stats (impressions, clicks, CPC, CTR) — separate API. Use `yandex-direct` (cascade marker)
- Google Analytics 4 — different platform and API. Use `google-analytics` (cascade marker)
- AppMetrica (mobile app analytics on appmetrica.yandex.com) — separate API. Use `appmetrica` (cascade marker)
- Placing the JS tag on a page or configuring goals via JS — that is tag-manager / frontend work, not API
- Downstream processing of collected data (ETL, ClickHouse, dashboards) — that belongs to `clickhouse` / `polars` / `pandas` / `postgresql`
- Session-recording (Webvisor) data — Webvisor API exists separately and is not covered here

## Purpose

Yandex.Metrika is the largest Russian web-analytics platform (the GA4 equivalent for the RU market). The API exposes three surfaces: **Reporting API** (`/stat/v1/data*`) — aggregated reports with `dimensions`, `metrics`, filter-segments and attribution models; **Logs API** (`/management/v1/counter/{id}/logrequests*`) — raw hit/visit export in TSV with `created`→`processed`→`cleaned` lifecycle; **Management API** (`/management/v1`) — CRUD on counters, goals, filters, operations. All endpoints are OAuth-authenticated against `api-metrika.yandex.net`.

This skill is **high-stakes** because:

1. **Sampling kicks in silently.** Default `accuracy=medium` returns `sampled: true`, `sample_share: 0.05` (5% of data) for heavy queries. Decisions made on an unrepresentative sample are decisions made on noise. Mitigation: `accuracy=full` for finance-critical reports; always inspect `sampled` and `sample_share` in the response.
2. **5000 requests/day per `user_login`** — resets at 00:00 GMT (03:00 MSK). A dashboard polling every minute exhausts the budget before lunch. Cache responses, aggregate queries.
3. **200 requests / 5 minutes on `/stat/v1/data/`** — a separate counter from the daily cap. Tripping it blocks the endpoint for 5 minutes.
4. **3 parallel requests per user_login** — more than that → 429. Do not run N workers without a semaphore.
5. **30 req/s per IP** (10 req/s for Logs API) — exceeding returns 429 with `Retry-After`.
6. **Logs API: 10 GB per counter** total uncleaned prepared logs. Forget to clean → `400 quota_exceeded`. Always `POST .../clean` after a successful download.
7. **Logs API: 1-year max range** in a single request, and `fields` ≤ 3000 characters. Split larger ranges client-side.
8. **Attribution shifts numbers dramatically.** The same conversion under `LAST` vs `FIRST` attributes to different sources. The default is `LASTSIGN` (last significant). If API numbers disagree with the web UI, check the attribution model.
9. **`counter_id` (`ids=`) is mandatory and easy to mix up.** One token may have access to dozens of counters; passing the wrong one returns 403.
10. **OAuth scope: read vs write.** `metrika:read` covers Reporting and Logs API but **not** goal/filter creation or imports. Use `metrika:write` only when CRUD is required.
11. **Same-day data is unstable.** Metrika finalizes ~99% of sessions within 3 days. Requests for `today` are meaningless for final figures.

This skill owns the provider-domain knowledge: endpoints, dimension/metric namespaces, filter DSL, Logs API lifecycle, quotas, attribution models, OAuth scopes. HTTP transport belongs to `httpx` / `nodejs`.

## Capabilities

### OAuth 2.0 and scopes

All requests require `Authorization: OAuth <token>` (the official scheme; `Bearer <token>` also works). Tokens are issued via oauth.yandex.ru — application type "For API access / debugging", `client_id`, Implicit-flow callback. Scopes: `metrika:read` (reports, Logs API, settings read), `metrika:write` (counters/goals/filters/operations CRUD), `metrika:expenses` / `metrika:user_params` / `metrika:offline_data` (imports; covered by `metrika:write`). For organization accounts add `passport:business`. Tokens have no default TTL but can be revoked by the user.

> Full reference: [references/setup.md](references/setup.md)

### End-to-end API workflow

Bootstrap → list counters → standard reports → time-series / drilldown / comparison → Logs API submit→poll→download→clean → goals/filters CRUD → quotas & defensive backoff → daily ETL into Postgres.

> Full reference: [references/workflow.md](references/workflow.md)

### Reporting API — request structure

`GET https://api-metrika.yandex.net/stat/v1/data?ids=<counter_id>&dimensions=<ym:...>&metrics=<ym:...>&date1=YYYY-MM-DD&date2=YYYY-MM-DD&filters=<expr>&sort=<field>&limit=<n>&offset=<n>&accuracy=full&attribution=LASTSIGN&group=day&direct_client_logins=...`. Limits: up to 10 dimensions per request; default `limit=100`, max `100000` (paginate via `offset`); `date1`/`date2` accept `today`, `yesterday`, `NdaysAgo`. Endpoints: `/stat/v1/data` (table), `/stat/v1/data/bytime` (series), `/stat/v1/data/drilldown` (hierarchy), `/stat/v1/data/comparison` (segment comparison).

> Full reference: [references/reporting-api.md](references/reporting-api.md)

### Dimensions and metrics — namespaces

Namespaces: `ym:s:` (sessions/visits — the workhorse), `ym:pv:` (page views), `ym:u:` (users), `ym:up:` (user params), `ym:ad:` (Yandex.Direct), `ym:sp:` (search phrases), `ym:el:` (external links), `ym:dl:` (downloads), `ym:ev:` (events). Dimensions and metrics in one request must share a namespace or be joined via `EXISTS()` in the filter. Key fields: `ym:s:visits`, `ym:s:users`, `ym:s:pageviews`, `ym:s:bounceRate`, `ym:s:avgVisitDurationSeconds`, `ym:s:goal{ID}reaches`, `ym:s:goal{ID}conversionRate`.

> Full reference: [references/dimensions-and-metrics.md](references/dimensions-and-metrics.md)

### Filter DSL and segments

Operators: `==`, `!=`, `=@` (substring), `!@` (no substring), `=~` (regex), `=*` (glob with `*`), `=n` (null), `=N` (not null), `>`, `<`, `>=`, `<=`, `IN(...)`, `NOT IN(...)`. Logic: `AND`, `OR`, `NOT`. Cross-namespace: `EXISTS(ym:pv:URL=='https://...')`. Limits: up to 10 unique dimensions/metrics in a filter, 20 conditions, 10 000 chars, 100 values per `IN()`. `filters` is a one-shot segment; persistent segments are created via Management API.

> Full reference: [references/segments-and-filters.md](references/segments-and-filters.md)

### Logs API — raw-hit lifecycle

Workflow: **(1)** `GET /management/v1/counter/{id}/logrequests/evaluate?date1=&date2=&fields=&source=` — verify feasibility (free); **(2)** `POST /management/v1/counter/{id}/logrequests?date1=&date2=&fields=&source=visits|hits` — create the job, get `request_id`, status `created`; **(3)** poll `GET /management/v1/counter/{id}/logrequest/{request_id}` until status becomes `processed` (or `processing_failed` / `awaiting_retry`); **(4)** download chunks: `GET /management/v1/counter/{id}/logrequest/{request_id}/part/{n}/download` (count from `parts[]`); **(5)** `POST /management/v1/counter/{id}/logrequest/{request_id}/clean` — release storage. Sources: `visits` or `hits`. Limits: `fields` ≤ 3000 chars, range ≤ 1 year, total ≤ 10 GB per counter. Polling cadence: 30–60 s is reasonable.

> Full reference: [references/logs-api.md](references/logs-api.md)

### Management API — CRUD

`GET /management/v1/counters` — accessible counters (fields `id`, `name`, `site`, `permission`, `pro`); `GET /management/v1/counter/{id}` — details; `POST /management/v1/counters` — create; `PUT /management/v1/counter/{id}` — update. Goals: `GET/POST /management/v1/counter/{id}/goals`, types `url`, `number`, `step`, `composite`, `action`. Filters: `/counter/{id}/filters` (bot/IP/domain exclusion). Operations: `/counter/{id}/operations` (URL cleanup — strip query params). Representatives: `/counter/{id}/representatives`.

> Full reference: [references/management-api.md](references/management-api.md)

### Errors, quota exhaustion, retry

HTTP 401 = invalid/expired token (reissue); 403 = no access to counter_id (check token owner); 429 = rate limit (honor `Retry-After`); 400 + `quota_exceeded` = 10 GB Logs cap; 400 + `LimitedExceededException` = daily request budget exhausted. Retry policy: exponential backoff 1→2→4→8 with jitter, cap 60 s; never retry 401/403/400.

> Full reference: [references/errors.md](references/errors.md)

### Rate limits and concurrency strategy

Global: **30 req/s per IP** (Reporting + Management), **10 req/s per IP** for Logs API, **3 parallel** per `user_login`, **5000 req/day** per `user_login` (reset 00:00 GMT = 03:00 MSK), **200 req / 5 min** on `/stat/v1/data/`. Logs API: **10 GB** of prepared logs per counter. Recipe: asyncio.Semaphore(3), token-bucket at 30 req/s, response cache for 5–15 min on dashboards, daily counter in Redis.

> Full reference: [references/rate-limits.md](references/rate-limits.md)

### Production clients (Python + Node.js)

Ready-made templates: `httpx.AsyncClient` with OAuth, token-bucket for 30 req/s, asyncio.Semaphore(3), retry on 429/503 honoring `Retry-After`, daily counter in Redis, `request_id` persistence in Postgres, Logs API worker (submit → poll → download chunks → clean), TSV parsing for multi-touch attribution (first/last/linear), Node.js mirror on `undici`. PostgreSQL schema for daily aggregates + raw hits.

> Full reference: [references/integration.md](references/integration.md)

## Quick reference

| API | Base path | Auth | Rate |
|---|---|---|---|
| Reporting | `https://api-metrika.yandex.net/stat/v1/data{,bytime,drilldown,comparison}` | OAuth | 200 req/5 min, 5000/day |
| Logs | `https://api-metrika.yandex.net/management/v1/counter/{id}/logrequest*` | OAuth `metrika:read` | 10 req/s, 10 GB/counter |
| Management | `https://api-metrika.yandex.net/management/v1/{counters,counter/{id}/{goals,filters,operations,representatives}}` | OAuth (read or write per op) | 30 req/s |
| Data Import | `https://api-metrika.yandex.net/management/v1/counter/{id}/{expenses,offline_conversions,calls,user_params}/upload` | OAuth `metrika:write`+scope | 30 req/s |

| `/stat/v1/data` param | Type | Notes |
|---|---|---|
| `ids` | int / CSV | counter_id (required); multiple comma-separated |
| `dimensions` | CSV | up to 10; e.g. `ym:s:date,ym:s:lastTrafficSource` |
| `metrics` | CSV | e.g. `ym:s:visits,ym:s:users,ym:s:bounceRate` |
| `date1`, `date2` | str | `YYYY-MM-DD`, `today`, `yesterday`, `NdaysAgo` |
| `filters` | str | DSL: `ym:s:lastTrafficSource=='organic'` |
| `sort` | CSV | `-ym:s:visits` (minus = DESC) |
| `limit` | int | default 100, max 100000 |
| `offset` | int | 1-based |
| `accuracy` | str | `low` / `medium` / `high` / `full` or number 0.01–1 |
| `proposed_accuracy` | bool | true → server suggests accuracy for speed |
| `attribution` | str | `FIRST` / `LAST` / `LASTSIGN` (default) / `LAST_YANDEX_DIRECT_CLICK` / `CROSS_DEVICE_*` / `AUTOMATIC` |
| `group` | str | `all` / `day` / `week` / `month` (for `/bytime`) |
| `direct_client_logins` | CSV | for Yandex.Direct reports |
| `include_undefined` | bool | include rows with null dimensions |
| `lang` | str | `ru` / `en` (label language) |

| Namespace | Holds | Sample dimension | Sample metric |
|---|---|---|---|
| `ym:s:` | Visits / sessions | `ym:s:date`, `ym:s:lastTrafficSource`, `ym:s:browser`, `ym:s:regionCity`, `ym:s:deviceCategory`, `ym:s:UTMSource` | `ym:s:visits`, `ym:s:users`, `ym:s:bounceRate`, `ym:s:pageDepth`, `ym:s:avgVisitDurationSeconds`, `ym:s:percentNewVisitors`, `ym:s:goal{ID}reaches`, `ym:s:goal{ID}conversionRate` |
| `ym:pv:` | Page views | `ym:pv:URL`, `ym:pv:title`, `ym:pv:referer` | `ym:pv:pageviews`, `ym:pv:users` |
| `ym:u:` | Users (cohorts) | `ym:u:userID`, `ym:u:firstVisitDate`, `ym:u:gender`, `ym:u:ageInterval` | `ym:u:users`, `ym:u:visitsPerUser` |
| `ym:up:` | User parameters | `ym:up:paramsLevel1..5` | `ym:up:params` |
| `ym:ad:` | Yandex.Direct | `ym:ad:directCampaignName`, `ym:ad:directOrder` | `ym:ad:clicks`, `ym:ad:RUBAdCost` |

| Logs lifecycle status | Meaning |
|---|---|
| `created` | Queued, waiting to be processed |
| `processed` | Ready — download via `/part/{n}/download` |
| `awaiting_retry` | Transient error, will be retried |
| `processing_failed` | Terminal failure — recreate |
| `cleaned_by_user` | Removed via `POST /clean` |
| `cleaned_automatically_as_too_old` | Auto-removed after 7 days |
| `canceled` | Cancelled |

| HTTP / code | Meaning | Retry? |
|---|---|---|
| 401 | invalid/expired token | no — reissue token |
| 403 | no access to counter_id | no — check scope/owner |
| 400 + `quota_exceeded` | 10 GB Logs / daily 5000 | no — clean logs / wait for GMT 00:00 |
| 429 | rate limit | yes — `Retry-After`, exponential backoff |
| 500/502/503 | server error | yes — backoff |

## Common mistakes

- **Skipping `accuracy=full`** on critical reports → silent sampling, `sampled:true, sample_share:0.05` ignored → decisions made on 5% of data. Fix: always inspect `sampled` in the response; use `accuracy=full` for finance-grade reports.
- **Namespace mismatch** — mixing `ym:s:` and `ym:pv:` in the same request → 400. Fix: one namespace per request, cross via `EXISTS()` in `filters`.
- **Asking for `today`** for final numbers — data is unstable for up to 3 days. Fix: use `yesterday` minimum, ideally `7daysAgo` for finalized aggregates.
- **Daily 5000 budget burnt** by a minute-cadence dashboard. Fix: 5–15 min cache, aggregate queries (one request with 10 dimensions ≠ 10 requests).
- **Not persisting Logs `request_id`** — after a worker restart the job is lost, a new one is created, quota is consumed twice. Fix: store `request_id` in Postgres/Redis with `status`, `parts[]`.
- **Skipping `/clean`** after a successful download → 10 GB exhausted in days → `400 quota_exceeded`. Fix: always `POST /clean` once all `parts[]` are downloaded.
- **Using `attribution=LAST`** with Yandex.Direct and being surprised that traffic "disappeared" — `LAST_YANDEX_DIRECT_CLICK` is the dedicated model; without it, much Direct traffic gets attributed to `direct/none`. Fix: use `LAST_YANDEX_DIRECT_CLICK` or `LASTSIGN` for Direct reports.
- **Polling Logs API once per second** → 429. Fix: 30–60 s cadence, exponential growth capped at ~5 min.
- **Storing the token in repo / logs** — a Metrika token is as sensitive as a Yandex ID password for that app. Fix: env only, audit log on use, rotate every N months.
- **Ignoring counter time zone** — Metrika data is in the counter's TZ. `date1=2026-05-15` is not the UTC calendar day. Fix: explicitly reconcile counter TZ before comparing with UTC data from other systems.
- **Requesting > 1 year** in Logs API → 400. Fix: split into yearly chunks, stitch locally.
- **`fields` > 3000 chars** in Logs API → 400. Fix: pick only the columns you need.
- **`limit=100` default** without pagination → silent row loss. Fix: explicit `limit=100000` plus an offset loop until `data.length < limit`.

## Red flags — STOP and verify

- API numbers **disagree with the Metrika web UI** — almost always one of (a) `sampled:true` without `accuracy=full`, (b) different attribution model, (c) different timezone, (d) request for `today`. Check those four before forming hypotheses.
- 429 in bursts → concurrency > 3 or > 30 req/s. Lower the semaphore and token bucket.
- `400 quota_exceeded` on Logs API → cleanup is missing. Run `GET /logrequests` and batch `POST /clean` for every `processed` job that has been downloaded.
- Logs `request_id` lost after worker restart → no persistence layer. Add DB persistence from day one.
- `403` on `/stat/v1/data` — token belongs to a different user, or `counter_id` belongs to someone else. Run `GET /management/v1/counters` to see what is actually visible under this token.
- Sudden spike in daily 5000 usage → someone added a per-minute poll. Add caching and an "only 500 requests left" alert.

## Behavioral Traits

- **Always preflight Logs API** via `/evaluate` before `POST /logrequests`, especially for wide date ranges — it is free and saves the 10 GB quota.
- **Persist before fire-and-forget**: for Logs API always save `request_id` to the DB before the Yandex response reaches the caller.
- **Sampling = always check** `sampled`, `sample_share` in the response; do not trust default accuracy.
- **One namespace per query**; for cross-namespace data use `EXISTS()` in `filters`, never mix `ym:s:` and `ym:pv:` in `dimensions`/`metrics`.
- **Default to `yesterday`**, not `today` — a data-quality vs. latency trade-off.
- **Minimum scope**: issue `metrika:read` for analytics, `metrika:write` only when CRUD is actually needed.

## Important Constraints

- **OAuth Bearer/OAuth header** is required on every request; missing → 401.
- **10 dimensions max** per Reporting request; **3000 chars max** in Logs `fields`.
- **1 year max** range in Logs API; **10 GB max** prepared-log storage per counter.
- **5000 req/day, 200 req/5min on /stat/v1/data/, 3 parallel, 30 req/s per IP** — hard quotas.
- **Logs auto-clean after 7 days** — old `processed` jobs flip to `cleaned_automatically_as_too_old`.
- **Same-day data is not final** (sessions finalize over up to 3 days).

## Related Skills

- `yandex-webmaster` — search queries / indexation (cascade marker)
- `yandex-direct` — Yandex.Direct ad-campaign stats (cascade marker)
- `google-analytics` — Google Analytics 4 (cascade marker)
- `appmetrica` — mobile-app analytics (cascade marker)
- `httpx`, `nodejs` — HTTP transport for your own client
- `postgresql`, `redis` — `request_id` persistence, daily counter, response cache
- `polars`, `pandas`, `clickhouse` — downstream processing for raw hits

## API Reference

> **Quick-start recipes**: [references/cookbook.md](references/cookbook.md) — 20+ `yandex_metrika_api` call examples (mcp-yandex-seo v0.5+)

| Endpoint | Method | Purpose |
|---|---|---|
| `/stat/v1/data` | GET | Tabular report (rows × dimensions × metrics) |
| `/stat/v1/data/bytime` | GET | Time series (for charts) |
| `/stat/v1/data/drilldown` | GET | Hierarchical drill-down |
| `/stat/v1/data/comparison` | GET | Comparison of two segments / periods |
| `/stat/v1/data/comparison/drilldown` | GET | Comparison + drill-down |
| `/management/v1/counters` | GET / POST | List / create counters |
| `/management/v1/counter/{id}` | GET / PUT / DELETE | Single-counter CRUD |
| `/management/v1/counter/{id}/goals` | GET / POST | Goals |
| `/management/v1/counter/{id}/goal/{goalId}` | GET / PUT / DELETE | Goal |
| `/management/v1/counter/{id}/filters` | GET / POST | Filters (bots / IP / domains) |
| `/management/v1/counter/{id}/operations` | GET / POST | Operations (URL cleanup) |
| `/management/v1/counter/{id}/representatives` | GET / POST | Representatives (delegated access) |
| `/management/v1/counter/{id}/logrequests/evaluate` | GET | Pre-flight feasibility check |
| `/management/v1/counter/{id}/logrequests` | GET / POST | List / create Logs API jobs |
| `/management/v1/counter/{id}/logrequest/{requestId}` | GET | Job status |
| `/management/v1/counter/{id}/logrequest/{requestId}/part/{n}/download` | GET | Download a log part |
| `/management/v1/counter/{id}/logrequest/{requestId}/clean` | POST | Clean a ready log |
| `/management/v1/counter/{id}/logrequest/{requestId}/cancel` | POST | Cancel a job |
| `/management/v1/counter/{id}/expenses/upload` | POST | Expenses import |
| `/management/v1/counter/{id}/offline_conversions/upload` | POST | Offline-conversion import |
| `/management/v1/counter/{id}/user_params/upload` | POST | User-params import |

## Cookbook (quick-start recipes)

> `references/cookbook.md` — 20+ ready-to-use `yandex_metrika_api` call examples for the mcp-yandex-seo v0.5 generic gateway. Covers counter discovery, reporting, search phrases, traffic sources, time-series, drilldown, comparison, goals, filters, segments, Logs API lifecycle, and migration from v0.4 narrow tools.

## See also

- `yandex-webmaster`, `yandex-direct`, `google-analytics`, `appmetrica` — adjacent RU/EN analytics platforms
- `clickhouse` — recommended sink for Logs API raw hits
- `httpx`, `nodejs` — HTTP client
- `postgresql`, `redis` — persistence
