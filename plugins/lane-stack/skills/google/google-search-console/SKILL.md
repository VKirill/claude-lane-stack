---
name: google-search-console
description: "[RU: Google Search Console API, гугл серч консоль, вебмастер гугл, gsc] GSC (Webmasters) API v1 — OAuth 2.0 + service account, searchanalytics.query (dimensions, filter operators, 25k row cap + startRow pagination), urlInspection.index.inspect (2000/day cap), Sites + Sitemaps CRUD, Indexing API for JobPosting/BroadcastEvent only, ~2-3 day data lag. Use when: GSC, search console, webmasters api, urlInspection, URL-prefix vs Domain property. SKIP: Yandex Webmaster (→yandex-webmaster); GA4 (→google-analytics); Bing Webmaster (→bing-webmaster); generic Google auth (→google-cloud-auth); SERP scraping (→xmlstock)."
stacks:
  - google-search-console
  - seo
  - python
  - nodejs
tags:
  - seo
  - google
  - gsc
  - search-console
  - indexing
  - oauth
  - sitemaps
source: vechkasov-global-skills
risk: high-stakes
---

<!-- versions:start -->

## Version Requirements (May 2026)

**Primary pins:**
- Search Console API: `v1` (Webmasters v3 endpoints stable; URL Inspection on `searchconsole.googleapis.com/v1`)
- Indexing API: `v3` (JobPosting + BroadcastEvent only)
- Python: `3.14.x`
- Node.js: `24.x (Active LTS)`

> Source of truth: [STACK_VERSIONS.md](../../STACK_VERSIONS.md) — verified 2026-08-24

<!-- versions:end -->

## Usage

Loaded automatically when the description matches the active task. Read only the section you need, then follow the link to the relevant reference file for full detail.

## Use this skill when

- Pull search analytics data (queries, pages, countries, devices, searchAppearance) for content planning, position audits, or client reports.
- Programmatically check URL index status via `urlInspection.index.inspect` (verdict, coverageState, lastCrawlTime, googleCanonical vs userCanonical, mobileUsability, AMP, richResults).
- Submit / delete / list `sitemap.xml` for an added property (`/webmasters/v3/sites/{siteUrl}/sitemaps`).
- Manage sites list (URL-prefix property vs Domain property `sc-domain:example.com`) and check permission level.
- Notify Google about a new or deleted page via Indexing API — **only for JobPosting or BroadcastEvent**. Regular pages will not work and abuse risks revoke.
- Build a Python (`google-api-python-client` + `google-auth`) or Node.js (`googleapis`) client with service account and automatic 25k-cap pagination.
- Schedule a daily ETL of search analytics into PostgreSQL — `(query, page, country, device, date) → clicks/impressions/ctr/position`.
- Audit indexation on large sites via URL Inspection while respecting the 2000/day/property quota.

## Do not use this skill when

- You need Yandex Webmaster — different provider, different property/sitemap model; → cascade `yandex-webmaster`.
- You need GA4 web analytics (sessions, users, events) — GSC only returns Google search data; → cascade `google-analytics`.
- You need Bing Webmaster Tools — separate Microsoft API.
- You need generic Google OAuth2 / service account patterns; → cascade `google-cloud-auth`.
- You need true SERP positions with real locale/device — GSC returns **averaged** impressions/position for queries already discovered; real SERP snapshot → cascade `xmlstock`.
- You expect a "list all my indexed URLs" endpoint — Google does not provide one; sample via Sitemaps + URL Inspection.
- You want to force-index regular pages with Indexing API — abuse-banned, alternative is sitemap + internal links + UI "Request Indexing".

## Purpose

Google Search Console API (Webmasters v3 + URL Inspection v1) is the only official channel for Google organic data: queries, clicks, impressions, CTR, position, index status. This skill covers OAuth 2.0 (user + service account), Search Analytics query with filters and 25k pagination, URL Inspection with daily quota, Sites + Sitemaps CRUD, and — separately — Indexing API (with a strict JobPosting/BroadcastEvent warning).

This skill is **high-stakes** because:

1. **URL Inspection 2000/day/property quota** — a naive crawl of all URLs in one go ends in `dailyLimitExceeded`. Design with a rate limiter and prioritization (new/changed URLs first).
2. **25,000-row hard cap** on Search Analytics responses. Without `startRow` pagination the long tail is silently lost — the classic "where are my queries?" bug.
3. **Data freshness lag ~2-3 days**. A request for "today" returns empty / incomplete. Use `dataState: "final"` (default) or know what `all` means.
4. **Domain property vs URL-prefix** — `sc-domain:example.com` aggregates all protocols/subdomains; `https://www.example.com/` is only that exact prefix. Mixing them yields wrong numbers.
5. **Service account cannot self-grant.** Its email must be added manually in the GSC UI as a user with Restricted or Full permission. The API offers no bootstrap path.
6. **Indexing API trap**: the "speed up indexation" myth → ban. Supported types are JobPosting and BroadcastEvent (in VideoObject) only.
7. **`searchAppearance` dimension cannot be combined** with other dimensions in one request — separate call required.
8. **Billing**: GSC endpoints are free at reasonable scale, but exceeding QPM/QPD → 429 with reason `quotaExceeded` or `dailyLimitExceeded`. Backoff is mandatory.
9. **OAuth refresh token expiry**: tokens in apps stuck in "Testing" mode expire after 7 days — production requires OAuth verification.

The skill owns provider-domain knowledge: endpoints, dimension/filter semantics, freshness lag, quotas, and the billing-free-but-quota-limited model. Pure HTTP plumbing belongs in `httpx` / `nodejs`. Deeper auth belongs in `google-cloud-auth`.

## Capabilities

### Authentication — OAuth 2.0 (user) + Service Account

Two paths: (a) **User OAuth 2.0 Authorization Code flow** with `refresh_token` — for apps where the GSC owner logs in; scopes `https://www.googleapis.com/auth/webmasters.readonly` (read) or `webmasters` (full, includes sitemap submit). (b) **Service Account JWT** — for server-to-server; the service account email **must be added** as a user in the Search Console UI (Settings → Users and permissions → Add user). Without that, the API returns `403 Forbidden` or `404 User does not have sufficient permission for site`.

> Full reference: [references/setup.md](references/setup.md)

### Property types — URL-prefix vs Domain

`siteUrl` comes in two shapes: **URL-prefix** (`https://www.example.com/` — trailing slash mandatory, exact protocol) and **Domain** (`sc-domain:example.com` — aggregates all protocols/subdomains, DNS-verified). Their data does **not** match: a Domain property sees more impressions. For URL Inspection, `siteUrl` must match the property exactly.

> Full reference: [references/setup.md](references/setup.md)

### Search Analytics — searchanalytics.query

`POST /webmasters/v3/sites/{siteUrl}/searchAnalytics/query`. Body: `startDate`, `endDate` (YYYY-MM-DD, Pacific Time), `dimensions[]` (`date`, `hour`, `query`, `page`, `country`, `device`, `searchAppearance`), `type` (`web`/`discover`/`googleNews`/`news`/`image`/`video`, default `web`), `aggregationType` (`auto`/`byPage`/`byProperty`/`byNewsShowcasePanel`), `dimensionFilterGroups[]` (groupType is always `and`; operators `equals`/`contains`/`notEquals`/`notContains`/`includingRegex`/`excludingRegex`), `rowLimit` (1-25000, default 1000), `startRow` (0+), `dataState` (`final`/`all`/`hourly_all`). Response: `rows[].keys[]` + `clicks`, `impressions`, `ctr` (0..1), `position`. Metadata: `responseAggregationType`, `metadata.first_incomplete_date`.

> Full reference: [references/search-analytics.md](references/search-analytics.md)

### 25,000-row cap + startRow pagination

Hard cap = 25,000 rows per response. Full export: loop with `rowLimit=25000` and increment `startRow += 25000` until a response returns fewer rows than the limit (or zero — empty response means end). There is no next-page-token. **Without pagination the tail is silently lost** beyond the top 25k by clicks.

> Full reference: [references/search-analytics.md](references/search-analytics.md)

### Data freshness lag (~2-3 days)

Final data appears with a 2-3 day delay (up to 4 for the long tail). `dataState: "final"` (default) excludes incomplete days. `dataState: "all"` includes fresh, recomputable rows (fine for "yesterday" dashboards, bad for historical reports). `metadata.first_incomplete_date` in the response tells you when data may still change. Hourly data: `dataState: "hourly_all"` + `dimensions: ["hour"]`.

> Full reference: [references/search-analytics.md](references/search-analytics.md)

### URL Inspection API — urlInspection.index.inspect

`POST https://searchconsole.googleapis.com/v1/urlInspection/index:inspect`. Body: `inspectionUrl`, `siteUrl` (must match the added property; URL-prefix needs trailing `/`), `languageCode` (BCP-47). Response is `inspectionResult` containing: `indexStatusResult` (verdict, coverageState, robotsTxtState, indexingState, lastCrawlTime, pageFetchState, googleCanonical, userCanonical, sitemap[], referringUrls[], crawledAs), `ampResult`, `mobileUsabilityResult`, `richResultsResult`. Quota: **2000/day/property** and 600 QPM/property.

> Full reference: [references/url-inspection.md](references/url-inspection.md)

### Sites + Sitemaps CRUD

Sites: `GET /webmasters/v3/sites` (list), `GET /sites/{siteUrl}` (get), `PUT /sites/{siteUrl}` (add — attaches site to current user, not verification), `DELETE /sites/{siteUrl}`. Fields: `siteUrl`, `permissionLevel` (siteFullUser/siteOwner/siteRestrictedUser/siteUnverifiedUser). Sitemaps: `GET /sites/{siteUrl}/sitemaps` (list), `GET /sites/{siteUrl}/sitemaps/{feedpath}` (get; feedpath URL-encoded), `PUT /sites/.../sitemaps/{feedpath}` (submit), `DELETE` (unsubmit). Fields: path, lastSubmitted, lastDownloaded, isPending, isSitemapsIndex, type (`sitemap`/`rssFeed`/`atomFeed`/`urlList`/`patternSitemap`/`notSitemap`), warnings, errors, contents[].

> Full reference: [references/sites-and-sitemaps.md](references/sites-and-sitemaps.md)

### Indexing API — JobPosting and BroadcastEvent ONLY

`POST https://indexing.googleapis.com/v3/urlNotifications:publish`. Body: `{ "url": "...", "type": "URL_UPDATED" | "URL_DELETED" }`. **WARNING**: Google explicitly states it "can only be used to crawl pages with either JobPosting or BroadcastEvent (embedded in VideoObject)". Using it for regular pages is abuse → revoke and possible manual action. Batch up to 100 sub-requests via multipart.

**WARNING:** Service account must have **Owner** role in the GSC property — Full user is insufficient for the Indexing API. Re-share property with SA email as Owner if you get 403.

> Full reference: [references/indexing-api.md](references/indexing-api.md)

### Quotas — short-window and daily

Search Analytics: 1200 QPM per-site, 1200 QPM per-user, 40,000 QPM + 30,000,000 QPD per-project. URL Inspection: **600 QPM per-site, 2000 QPD per-site**, 15,000 QPM + 10,000,000 QPD per-project. Other resources (Sites/Sitemaps): 20 QPS + 200 QPM per-user, 100,000,000 QPD per-project. Exceeding → 429 with reason `quotaExceeded` / `userRateLimitExceeded` / `dailyLimitExceeded`. Exponential backoff is required.

- **Indexing API:** 200 calls/day/project (default, raiseable via quota form); 600 QPM/project.

> Full reference: [references/rate-limits.md](references/rate-limits.md)

### Errors — 400/401/403/404/429/500

400 `badRequest` — invalid dimensions/dates. 401 `authError` — expired token, refresh. 403 `forbidden` — no permission on property or service account not added. 404 — `siteUrl` unknown to user. 429 — quota, backoff. 500/503 — transient, retry with jitter. Reason codes are in `error.errors[].reason`.

> Full reference: [references/errors.md](references/errors.md)

### End-to-end API workflows

Auth bootstrap → Search Analytics query lifecycle → URL Inspection → Sitemaps → Indexing API caveat → Quota management → Daily ETL into PostgreSQL.

> Full reference: [references/workflow.md](references/workflow.md)

### Production clients — Python + Node.js

Drop-in templates: Python with `google-api-python-client` (service account from JSON), Python with raw `httpx` + JWT assertion for fine control, Node.js with `googleapis`. Pagination helper for 25k cap. URL Inspection batch worker with per-property quota tracker. PostgreSQL schema for daily snapshots.

> Full reference: [references/integration.md](references/integration.md)

## Quick reference

| Resource | Endpoint (base + path) | Method |
|---|---|---|
| Search Analytics query | `webmasters/v3/sites/{siteUrl}/searchAnalytics/query` | POST |
| Sites list | `webmasters/v3/sites` | GET |
| Sites get | `webmasters/v3/sites/{siteUrl}` | GET |
| Sites add | `webmasters/v3/sites/{siteUrl}` | PUT |
| Sites delete | `webmasters/v3/sites/{siteUrl}` | DELETE |
| Sitemaps list | `webmasters/v3/sites/{siteUrl}/sitemaps` | GET |
| Sitemap get | `webmasters/v3/sites/{siteUrl}/sitemaps/{feedpath}` | GET |
| Sitemap submit | `webmasters/v3/sites/{siteUrl}/sitemaps/{feedpath}` | PUT |
| Sitemap delete | `webmasters/v3/sites/{siteUrl}/sitemaps/{feedpath}` | DELETE |
| URL Inspection | `searchconsole/v1/urlInspection/index:inspect` | POST |
| Indexing API | `indexing/v3/urlNotifications:publish` | POST |

| Dimension | Notes |
|---|---|
| `date` | YYYY-MM-DD (PT) |
| `hour` | ISO-8601, only with dataState `hourly_all` |
| `query` | search query |
| `page` | landing URL |
| `country` | ISO 3-letter, lower-case (`usa`, `rus`) |
| `device` | `DESKTOP`/`MOBILE`/`TABLET` |
| `searchAppearance` | features: AMP, RICH_RESULT, VIDEO, ... — **cannot combine with other dimensions in one request** |

| Filter operator | Behavior |
|---|---|
| `equals` (default) | exact match |
| `notEquals` | exact exclusion |
| `contains` | substring |
| `notContains` | without substring |
| `includingRegex` | RE2 include |
| `excludingRegex` | RE2 exclude |

| Status / Reason | Meaning | Action |
|---|---|---|
| 400 `badRequest` | invalid dimensions/dates | check formatting |
| 401 `authError` | token expired | refresh OAuth token |
| 403 `forbidden` | service account not added to property | add via UI |
| 404 | siteUrl unknown to user | verify, add, or use `sc-domain:` |
| 429 `quotaExceeded` | short-window | exp backoff |
| 429 `userRateLimitExceeded` | per-user QPM | backoff + lower concurrency |
| 429 `dailyLimitExceeded` | per-day | wait until PT midnight |
| 500 / 503 | transient | retry with jitter |

## Common mistakes

- **Requesting 100k+ queries without pagination** — you get the top 25k and lose the tail. Fix: loop `startRow += 25000` until response is empty.
- **Mixing Domain property with URL-prefix** in `siteUrl` — data will not match; URL Inspection returns 404. Fix: copy the string from GSC UI verbatim; Domain needs the `sc-domain:` prefix.
- **Service account not added in GSC** → 403/404. Fix: a human user must add `xxx@yyy.iam.gserviceaccount.com` as Restricted or Full user in the UI. The API never self-bootstraps.
- **Using Indexing API for regular pages** — abuse, may lead to revoke / manual action. Fix: use sitemap + link profile; Indexing API only for JobPosting / BroadcastEvent.
- **Expecting "today" or "yesterday" data in Search Analytics** — 2-3 day lag. Fix: either `dataState: "all"` for fresh incomplete data, or accept the delay.
- **Combining `searchAppearance` with other dimensions** — spec requires a dedicated call. Fix: first request — just `searchAppearance` to discover values; second — filter by a specific feature.
- **URL Inspection in a loop over 100k URLs with no quota tracking** → `dailyLimitExceeded` within minutes. Fix: 2000/day/property; prioritize new/changed; persist results for N days.
- **Forgetting to URL-encode feedpath in Sitemaps endpoints** → 400. Fix: `encodeURIComponent("https://example.com/sitemap.xml")`.
- **Passing `country` as `"US"`** — it is lower-case 3-letter ISO: `"usa"`. Fix: validate filter format.
- **Relying on `permissionLevel: siteUnverifiedUser`** — that user gets empty API responses. Fix: ensure siteOwner / siteFullUser / siteRestrictedUser.
- **Querying `discover` or `googleNews` for a brand-new property** — may be empty if Google has not classified the source. Fix: confirm baseline with `type: web` first.
- **Ignoring when `responseAggregationType` differs from requested** — Google may return `byPage` instead of `auto`. Fix: read the response field for analytics correctness.

## Red flags — STOP and verify

- Service account returns 403 on the first request — **check the UI**: is the SA email added as a property user? Without it the API returns nothing, not even `sites.list`.
- Numbers in the API do not match the GSC UI — almost always different date ranges (UI ~ `dataState all`, API default `final`), different property types (Domain vs URL-prefix), or missing pagination.
- `dailyLimitExceeded` on URL Inspection well before the day ends — no per-property limiter. Stop the worker; recompute around 2000/property.
- Someone asks you to "speed up indexation via Indexing API" for regular pages — red flag, path to a manual action. Refuse and explain.
- An OAuth refresh token suddenly stops working — app likely stuck in Testing mode (7-day expiry) or the user revoked access in their Google account → require re-consent.

## Behavioral traits

- Before any bulk URL Inspection — measure quota: `N URLs × 2000/day/property`.
- For any "pull all data for period" request — always write the pagination loop, never a single 25k-row call.
- For service accounts — first confirm the SA email is added in the GSC UI.
- Distinguish `final` vs `all` `dataState` and explicitly call out the 2-3 day lag.
- Never propose Indexing API for regular pages — JobPosting / BroadcastEvent only.
- For Domain property — always write the `sc-domain:` prefix; never pass `https://example.com/` as Domain.

## Important constraints

- HTTP plumbing — use `httpx` (Python) or `node:fetch` / `googleapis` (Node) — never reimplement.
- OAuth refresh token persistence — Redis/Postgres, never hard-coded.
- `webmasters.readonly` scope for read-only; `webmasters` only when sitemap submit / sites add is genuinely needed.
- Cache URL Inspection results for 24-72 hours in the database; never re-inspect the same URL more than once a day.
- `country` filters — lowercase ISO-3 (`usa`, not `US`).
- `device` filters — uppercase (`MOBILE`, `DESKTOP`, `TABLET`).
- Sitemap `feedpath` — URL-encoded.
- All `lastSubmitted` / `lastDownloaded` timestamps — RFC 3339.

## Related skills

- `yandex-webmaster` — Yandex Webmaster API (separate provider, similar task for RU sites).
- `google-analytics` — Google Analytics 4 Data API (web analytics, not GSC).
- `xmlstock` — true SERP snapshots via parsing (position with geo/device).
- `google-cloud-auth` — generic OAuth / service account patterns for all Google APIs.
- `httpx`, `nodejs` — HTTP transport for custom clients.
- `postgresql`, `redis` — persistence for snapshots, refresh tokens, URL Inspection cache.

## API Reference

| Section | Reference |
|---|---|
| Auth + property setup | [references/setup.md](references/setup.md) |
| Search Analytics deep dive | [references/search-analytics.md](references/search-analytics.md) |
| URL Inspection | [references/url-inspection.md](references/url-inspection.md) |
| Sites + Sitemaps | [references/sites-and-sitemaps.md](references/sites-and-sitemaps.md) |
| Indexing API caveat | [references/indexing-api.md](references/indexing-api.md) |
| Errors | [references/errors.md](references/errors.md) |
| Rate limits | [references/rate-limits.md](references/rate-limits.md) |
| End-to-end workflows | [references/workflow.md](references/workflow.md) |
| Python + Node clients, DB schema | [references/integration.md](references/integration.md) |
