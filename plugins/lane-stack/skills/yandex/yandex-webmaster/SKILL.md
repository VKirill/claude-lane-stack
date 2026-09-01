---
name: yandex-webmaster
description: "[RU: Яндекс.Вебмастер API — поисковые запросы, индексация, переобход URL, sitemap] Yandex.Webmaster REST API v4 — OAuth 2.0, popular/history search queries, recrawl with daily quota, sitemap CRUD, diagnostics, host verification. Use when: yandex webmaster, яндекс вебмастер, webmaster api, api.webmaster.yandex.net, /v4/user, host_id, recrawl, переобход url, popular search queries, TOTAL_SHOWS, AVG_SHOW_POSITION, sitemap api, OAuth Яндекс, верификация прав, диагностика, индексация. SKIP: Wordstat frequency (→mutagen); SERP positions (→xmlstock); Google Search Console (→google-search-console); traffic (→yandex-metrica); ads (→yandex-direct)."
stacks:
  - yandex-webmaster
  - ru-seo
  - python
  - nodejs
tags:
  - seo
  - ru
  - yandex
  - search-console
  - indexing
  - sitemap
  - oauth
source: vechkasov-global-skills
risk: high-stakes
---

<!-- versions:start -->
<!-- versions:end -->

## Usage

Loaded automatically when the description matches the active task. Read only the section you need, then follow the link to the relevant reference file.

## Use this skill when

- Pulling search query stats (shows, clicks, avg position, CTR) — `search-queries/popular` or `search-queries/all/history`
- Monitoring indexing dynamics — `indexing/history`, `indexing/samples`, `indexing/insearch/history`
- Submitting URLs to recrawl with daily-quota awareness — `POST recrawl/queue` + `GET recrawl/quota`
- Managing sitemaps: list, add user sitemaps, track processing errors — `sitemaps`, `user-added-sitemaps`
- Site diagnostics with severity (FATAL/CRITICAL/POSSIBLE_PROBLEM/RECOMMENDATION) — `diagnostics`
- External/internal link audit — `links/external/samples`, `links/internal/samples`
- Host ownership verification (DNS, HTML_FILE, META_TAG, TXT_FILE) — `verification`
- SQI history, search events (pages added/removed) — `sqi-history`, `search-events`
- Building a Python (`httpx`) / Node.js (`undici`) OAuth client with refresh-token, `task_id` persistence, recrawl daily quota
- Registering an OAuth app on `oauth.yandex.com` and obtaining a long-lived token

## Do not use this skill when

- Wordstat / general phrase frequency — Webmaster reports shows that already happened on your site, not query volume. Use `mutagen` (cascade)
- Generic SERP position tracking for arbitrary keywords — Webmaster only covers verified hosts. Use `xmlstock` (cascade)
- Google Search Console / Bing Webmaster — different provider. Use `google-search-console` (cascade)
- Yandex.Metrica (behavior, traffic sources, conversions) — separate product. Use `yandex-metrica` (cascade)
- Yandex.Direct (ad campaigns, bids, budgets) — separate API. Use `yandex-direct` (cascade)
- Custom SERP scraping bypassing the API — `xmlstock` or your own scraper via `proxy6`
- Downstream runtime (HTTP client, DB, cache) — use `httpx`, `nodejs`, `postgresql`, `redis`

## Purpose

Yandex.Webmaster API v4 (`https://api.webmaster.yandex.net/v4/`) — official REST interface for managing sites in Yandex.Webmaster: search analytics (what users searched and clicked), indexing, page recrawl, problem diagnostics, sitemaps, links, ownership verification. Auth is OAuth 2.0 with `Authorization: OAuth <token>` header.

This skill is **high-stakes** because:

1. **Recrawl daily quota silently exhausts.** Each `POST /recrawl/queue` spends 1 unit; a batch of 5000 URLs without a pre-check hits 429 `QUOTA_EXCEEDED` after ~N successful posts. Duplicate URL returns 409 `URL_ALREADY_ADDED` (no quota spent, but trips batch logic). Quota varies with SQI / site type; **always** call `GET /recrawl/quota` first.
2. **OAuth token is short-lived by default.** Without explicitly requesting long-lived tokens in the app settings, the token expires ~1 year from last use; tokens with explicit `expires_in` expire quickly. Refresh logic is mandatory.
3. **`host_id` is not a domain.** It is an internal id like `https:example.com:443` (colon-separated) — never guess; fetch from `GET /v4/user/{user-id}/hosts` and persist.
4. **Date-range retention is not documented but bounded.** Detailed search-query data is retained ~90 days. Older ranges return truncated payloads silently. For long history — accumulate locally.
5. **Unverified site (`HOST_NOT_VERIFIED`)** returns 404 on most endpoints. Filter `verified=true` before analytics calls.
6. **Rate limit on 429** is not publicly documented as a number. Strategy: exponential backoff + Retry-After-aware + concurrency ≤ 5-10 per host.
7. **`HOSTS_LIMIT_EXCEEDED`** per user (historically ~1703) — verify before bulk adds.
8. **Sitemap add is idempotent by URL**: re-POST same URL → 409 `SITEMAP_ALREADY_ADDED` — catch and treat as success.

The skill owns provider domain knowledge: v4 endpoints, OAuth lifecycle, recrawl quota semantics, search-query indicators, diagnostics enums, sitemap flow, error table. HTTP transport itself belongs to `httpx` / `nodejs`.

## End-to-end API Workflow

> Full step-by-step API interaction: **[references/workflow.md](references/workflow.md)** — bootstrap, host verification, sitemap submission, search analytics, indexing & recrawl, diagnostics, links, daily ETL pattern. Each step includes HTTP method + URL template, request/response shape, error paths, curl + Python snippets.

Quick map of the workflow file:

| Stage | What |
|---|---|
| 1. Bootstrap | OAuth app → scopes → token → `user_id` → list hosts |
| 2. Host verification | Add host → choose verifier (DNS/HTML_FILE/META_TAG/TXT_FILE) → poll state |
| 3. Sitemap management | Submit user-added sitemap → poll processing → handle errors |
| 4. Search analytics | Pull popular queries → query history → handle 90-day retention |
| 5. Indexing & recrawl | Read indexing history → check quota → submit URL → poll task |
| 6. Diagnostics | Pull problems → classify by severity → wire to monitoring |
| 7. Links | External/internal samples → paginate |
| 8. Daily ETL | Cron / BullMQ → persist to Postgres → dedupe → alert on quota |

## Capabilities

### OAuth & authentication

Register an app on [oauth.yandex.com](https://oauth.yandex.com) with scopes `webmaster:hostinfo`, `webmaster:verify`. Authorization Code flow: `https://oauth.yandex.com/authorize?response_type=code&client_id=...` → exchange at `https://oauth.yandex.com/token` (form `grant_type=authorization_code&code=...&client_id=...&client_secret=...`). Response: `access_token`, `refresh_token`, `expires_in`, `token_type=bearer`. Use header `Authorization: OAuth <access_token>` (literal word `OAuth`, **not** `Bearer`). Refresh with `grant_type=refresh_token`.

> Full reference: [references/setup.md](references/setup.md)

### Hosts & verification

`GET /v4/user` → `user_id`. `GET /v4/user/{user-id}/hosts` → array with `host_id`, `ascii_host_url`, `unicode_host_url`, `verified`, `main_mirror`, `host_data_status` (NOT_INDEXED / NOT_LOADED / OK). `POST /v4/user/{user-id}/hosts` body `{"host_url": "..."}` → 201. `DELETE /v4/user/{user-id}/hosts/{host-id}`. Verification: `GET .../verification` (state), `POST .../verification?verification_type={DNS|HTML_FILE|META_TAG|TXT_FILE}` (start). States: `NONE`, `IN_PROGRESS`, `VERIFIED`, `VERIFICATION_FAILED`, `INTERNAL_ERROR`.

> Full reference: [references/hosts-and-sitemaps.md](references/hosts-and-sitemaps.md)

### Search queries analytics

`GET .../search-queries/popular?order_by={TOTAL_SHOWS|TOTAL_CLICKS}&query_indicator=...&device_type_indicator=...&date_from=...&date_to=...&offset=...&limit=...` — TOP-3000 queries for last week by default, page up to 500. Indicators: `TOTAL_SHOWS`, `TOTAL_CLICKS`, `AVG_SHOW_POSITION`, `AVG_CLICK_POSITION`. Device: `ALL` (default), `DESKTOP`, `MOBILE`, `TABLET`, `MOBILE_AND_TABLET`. Single query history: `.../search-queries/{query-id}/history`. All-queries aggregated history: `.../search-queries/all/history`. `query_id` comes from `popular` response.

> Full reference: [references/search-queries.md](references/search-queries.md)

### Indexing statistics

`GET .../indexing/history?date_from=...&date_to=...&indexing_indicators=...` — page-load dynamics split by HTTP code (`HTTP_2XX`, `HTTP_3XX`, `HTTP_4XX`, `HTTP_5XX`, `OTHER`). `.../indexing/samples` — sample loaded pages. `.../indexing/insearch/history` — pages in search; `.../indexing/insearch/samples` — sample searchable pages. `.../search-events/history` + `.../search-events/samples` — added/removed from search. Indicators: `SEARCHABLE`, `DOWNLOADED`, `EXCLUDED`, `FAILED_TO_DOWNLOAD`.

> Full reference: [references/indexing.md](references/indexing.md)

### Recrawl URL queue (daily quota, batch)

`GET .../recrawl/quota` → `{daily_quota, quota_remainder}`. **Always check before batches.** `POST .../recrawl/queue` body `{"url": "..."}` → 202 `{task_id, quota_remainder}`. Each POST = 1 quota unit. Duplicate → 409 `URL_ALREADY_ADDED` (no quota spent). `GET .../recrawl/queue?offset=&limit=&date_from=&date_to=` — task list. `GET .../recrawl/queue/{task-id}` → `{task_id, url, added_time, state}`. State: `IN_PROGRESS`, `DONE`, `FAILED`. For idempotency: persist URL → task_id mapping; do not re-POST.

> Full reference: [references/indexing.md](references/indexing.md)

### Sitemap management

`GET .../sitemaps?limit=&from=` — all sitemaps discovered by the bot, with `sources` (`ROBOTS_TXT`, `WEBMASTER`, `INDEX_SITEMAP`) and `sitemap_type`. Fields: `sitemap_id`, `sitemap_url`, `last_access_date`, `errors_count`, `urls_count`, `children_count`. `GET .../sitemaps/{sitemap-id}` — one. `GET .../user-added-sitemaps` — user-added only. `POST .../user-added-sitemaps` body `{"url": "..."}` → 201 `{sitemap_id}`. `DELETE .../user-added-sitemaps/{sitemap-id}`. Duplicate → 409 `SITEMAP_ALREADY_ADDED` (catch, treat as success).

> Full reference: [references/hosts-and-sitemaps.md](references/hosts-and-sitemaps.md)

### Links analysis (internal/external)

External links: `GET .../links/external/samples?offset=&limit=` (limit 1-100, default 10) → array `{source_url, destination_url, discovery_date, source_last_access_date}` + `count`. History: `.../links/external/history?date_from=&date_to=`. Internal (broken): `.../links/internal/samples` + `.../links/internal/history`. Used for backlink audits and broken-internal-link discovery.

> Full reference: [references/links.md](references/links.md)

### Site diagnostics & problems

`GET .../diagnostics` → `{problems: {[PROBLEM_TYPE]: {severity, state, last_state_update}}}`. Severity: `FATAL` (DISALLOWED_IN_ROBOTS, DNS_ERROR, MAIN_PAGE_ERROR, THREATS), `CRITICAL` (SSL_CERTIFICATE_ERROR, SLOW_AVG_RESPONSE_TIME), `POSSIBLE_PROBLEM` (NO_SITEMAPS, NO_ROBOTS_TXT, TOO_MANY_PAGE_DUPLICATES), `RECOMMENDATION` (NOT_MOBILE_FRIENDLY, FAVICON_PROBLEM, NO_METRIKA_COUNTER). State: `PRESENT`, `ABSENT`, `UNDEFINED`. Use for auto-alerting on FATAL/CRITICAL.

> Full reference: [references/diagnostics.md](references/diagnostics.md)

## Quick reference

| Section | Endpoint | Method | Returns |
|---|---|---|---|
| User | `/v4/user` | GET | `user_id` (needed by all other calls) |
| Hosts | `/v4/user/{user-id}/hosts` | GET / POST | list / add |
| Host | `/v4/user/{user-id}/hosts/{host-id}` | GET / DELETE | info / delete |
| Verification | `.../hosts/{host-id}/verification` | GET / POST | state / start (DNS, HTML_FILE, META_TAG, TXT_FILE) |
| Summary | `.../hosts/{host-id}/summary` | GET | aggregated site stats |
| Search Queries (popular) | `.../search-queries/popular` | GET | TOP-3000 / week, page up to 500 |
| Search Queries (all history) | `.../search-queries/all/history` | GET | aggregated history |
| Search Queries (specific) | `.../search-queries/{query-id}/history` | GET | one query history |
| Indexing History | `.../indexing/history` | GET | HTTP_2XX/3XX/4XX/5XX/OTHER × date |
| Indexing Samples | `.../indexing/samples` | GET | sample loaded pages |
| In-Search History | `.../indexing/insearch/history` | GET | pages in search × date |
| Recrawl Quota | `.../recrawl/quota` | GET | `daily_quota`, `quota_remainder` |
| Recrawl Queue | `.../recrawl/queue` | GET / POST | tasks / submit URL |
| Recrawl Task | `.../recrawl/queue/{task-id}` | GET | `state`: IN_PROGRESS / DONE / FAILED |
| Sitemaps | `.../sitemaps` | GET | all discovered by bot |
| User Sitemaps | `.../user-added-sitemaps` | GET / POST | user-added |
| User Sitemap | `.../user-added-sitemaps/{sitemap-id}` | GET / DELETE | one / delete |
| Links External | `.../links/external/samples` | GET | sample inbound links |
| Links Internal | `.../links/internal/samples` | GET | sample broken internal |
| Diagnostics | `.../diagnostics` | GET | `problems` with severity |
| SQI History | `.../sqi-history` | GET | SQI time series |
| Important URLs | `.../important-urls` | GET / POST | key-page monitoring |

| Indicator | Where | Note |
|---|---|---|
| `TOTAL_SHOWS` | search-queries | times shown in SERP |
| `TOTAL_CLICKS` | search-queries | clicks from SERP |
| `AVG_SHOW_POSITION` | search-queries | avg position on shows |
| `AVG_CLICK_POSITION` | search-queries | avg position on clicks |
| `SEARCHABLE` | indexing | page in search |
| `DOWNLOADED` | indexing | bot loaded |
| `EXCLUDED` | indexing | excluded from search |
| `FAILED_TO_DOWNLOAD` | indexing | load failed |

| HTTP | Code | Quota spent? | Action |
|---|---|---|---|
| 400 | `ENTITY_VALIDATION_ERROR` / `FIELD_VALIDATION_ERROR` / `INVALID_URL` | — | fix body / params |
| 401 | (missing/invalid token) | — | refresh access_token |
| 403 | `INVALID_OAUTH_TOKEN` / `INVALID_USER_ID` / `ACCESS_FORBIDDEN` | — | check scopes / user_id |
| 403 | `HOSTS_LIMIT_EXCEEDED` | — | stop adding sites |
| 404 | `RESOURCE_NOT_FOUND` / `HOST_NOT_FOUND` / `HOST_NOT_VERIFIED` / `HOST_NOT_INDEXED` / `HOST_NOT_LOADED` | — | verify site |
| 404 | `SITEMAP_NOT_FOUND` / `TASK_NOT_FOUND` / `QUERY_ID_NOT_FOUND` | — | id stale / missing |
| 409 | `URL_ALREADY_ADDED` | **no** | already queued — ignore |
| 409 | `HOST_ALREADY_ADDED` / `SITEMAP_ALREADY_ADDED` / `VERIFICATION_ALREADY_IN_PROGRESS` | — | treat as success |
| 422 | (length violation) | — | check url/text length |
| 429 | `QUOTA_EXCEEDED` | **yes** (recrawl) | daily limit drained, wait reset |
| 429 | `TOO_MANY_REQUESTS_ERROR` | — | rate limit, backoff + Retry-After |

## Common mistakes

- **Sending recrawl batches without checking `recrawl/quota`.** After `quota_remainder` successful POSTs the rest gets 429. Fix: `GET recrawl/quota` first, clamp batch to `quota_remainder - safety_margin`.
- **Using `Bearer <token>` instead of `OAuth <token>`.** Yandex accepts only `Authorization: OAuth ya29...`. Bearer returns 401. Fix: hardcode `OAuth ` prefix.
- **Guessing `host_id` from the domain.** `host_id` looks like `https:example.com:443` (colon-separated) — must come from `GET /v4/user/{user-id}/hosts` and be persisted. Fix: cache `domain → host_id`.
- **Calling analytics endpoints for an unverified site** → 404 `HOST_NOT_VERIFIED`. Fix: filter `verified=true` before polling.
- **Treating 409 `SITEMAP_ALREADY_ADDED` as an error and retrying.** Fix: treat as idempotent success, fetch `sitemap_id` via GET.
- **Persisting access_token and never refreshing.** Default tokens expire; after ~1 year integration fails with 401. Fix: on 401, attempt refresh, persist new tokens.
- **Querying search queries for >90 days** and being puzzled by empty data. Webmaster keeps detailed data for a limited window. Fix: daily pull into your DB (see `references/integration.md`).
- **Relying on 429 to learn the current limit** — limits are not returned with rate errors. Fix: measure yourself (sliding window of requests), keep concurrency ≤ 10 per token.

## Red flags — STOP and verify

- **`429 QUOTA_EXCEEDED` on the first recrawl POST of the day** — someone else is using the same OAuth app today. Check other integrations / second worker / cron.
- **`recrawl/quota` returns `daily_quota=0`** — site is **unverified** (or lost verification, e.g. meta tag removed). Verify owns first.
- **`401 INVALID_OAUTH_TOKEN` mid-batch** — token just expired. Refresh, persist, retry the batch from the same offset.
- **Diagnostics returns `FATAL` `DISALLOWED_IN_ROBOTS` or `DNS_ERROR`** on a production site — that is a real incident, alert the owner, do not silence.
- **`task_id` mass-`FAILED` in `recrawl/queue/{task-id}`** — site is temporarily unreachable (5xx / timeout / Yandex bot IP block). Fix the site, do not re-POST.

## Behavioral Traits

- Before mass operations (recrawl batch, bulk sitemap add) — **always** pre-check: `recrawl/quota`, list verified hosts, list existing sitemaps.
- Treat 409 `*_ALREADY_ADDED` as idempotent success. Log INFO, not WARN.
- Persist every server-issued id: `user_id`, `host_id`, `sitemap_id`, `task_id`, `query_id`. Do not recreate per call.
- Snapshot search-queries / indexing stats into your DB daily. Yandex is not long-term storage.
- Separate OAuth tokens: read-only monitoring (`webmaster:hostinfo`) vs write ops (`webmaster:verify`, recrawl, sitemap CRUD).

## Important Constraints

- **NEVER** POST to `recrawl/queue` without first GETting `/recrawl/quota` for server-side batches (an interactive UI button is fine — 1 click = 1 unit).
- **NEVER** store `client_secret` or `access_token` in code / git / public configs. Env or secret store only.
- **NEVER** assume `host_id == ascii_host_url`. They are different fields.
- **NEVER** use the `Bearer` prefix. Only `OAuth `.
- **ALWAYS** handle `verified=false` separately — skip `search-queries`, `indexing`, `recrawl` for those.
- **ALWAYS** honor `Retry-After` on 429; otherwise exponential backoff (2→4→8→16→32 s, max 60 s, jitter).
- **ALWAYS** keep concurrency ≤ 10 simultaneous requests per OAuth token.

## Related Skills

- `mutagen` — Wordstat frequency (cascade); Webmaster shows shows-that-already-happened on your site, mutagen shows phrase volume in Yandex overall
- `xmlstock` — arbitrary SERP position parsing (cascade); Webmaster covers only verified hosts
- `google-search-console` — Google counterpart (cascade); different provider and API
- `yandex-metrica` — behavioral and traffic data (cascade); different Yandex product
- `yandex-direct` — Yandex.Direct for paid search (cascade); different product
- `httpx`, `nodejs` — HTTP transport for your own client
- `postgresql`, `redis` — persistence for `user_id`, `host_id`, `task_id`, daily search-query snapshots

## API Reference

| File | Content |
|---|---|
| [references/cookbook.md](references/cookbook.md) | 20+ ready-to-use `yandex_webmaster_api` recipes: bootstrap, hosts, verification, search queries, diagnostics, indexing, recrawl, sitemaps, links, SQI, important-URLs; migration from v0.4 narrow tools |
| [references/workflow.md](references/workflow.md) | End-to-end API workflow: bootstrap → verify → sitemap → analytics → recrawl → diagnostics → daily ETL |
| [references/setup.md](references/setup.md) | OAuth flow, app registration, scopes, code→token, refresh, headers |
| [references/hosts-and-sitemaps.md](references/hosts-and-sitemaps.md) | `/v4/user`, `/hosts`, verification, sitemap CRUD |
| [references/search-queries.md](references/search-queries.md) | popular, history, query_id, indicators, device filter |
| [references/indexing.md](references/indexing.md) | indexing history/samples, recrawl quota/queue/task |
| [references/links.md](references/links.md) | external/internal links samples + history |
| [references/diagnostics.md](references/diagnostics.md) | problems, severity, problem types, recommendations |
| [references/errors.md](references/errors.md) | full error-code table, retry strategy |
| [references/rate-limits.md](references/rate-limits.md) | 429, concurrency, recrawl daily quota |
| [references/integration.md](references/integration.md) | Production Python (httpx async) + Node.js (undici) clients, Postgres schema |
