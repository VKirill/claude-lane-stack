# Cookbook — yandex_webmaster_api recipes

Last verified: 2026-05-17

Base URL: `https://api.webmaster.yandex.net`  
Auth header: `Authorization: OAuth <token>` (literal `OAuth`, NOT `Bearer`)  
All `{user_id}` and `{host_id}` values must come from the API — never hardcode. See bootstrap recipe first.

---

## 1. Bootstrap — get user_id

### Get current user_id

```
yandex_webmaster_api({
  endpoint: "/v4/user"
})
```

Returns `{ "user_id": 1234567 }`. Persist — required in every path below.

---

## 2. Hosts

### List all sites for the account

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts"
})
```

Response: `hosts[]` with `host_id`, `ascii_host_url`, `verified`, `host_data_status` (OK / NOT_INDEXED / NOT_LOADED).  
Persist `host_id` — it looks like `https:example.com:443`, not a plain domain.

### Get a single host record

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts/https:example.com:443"
})
```

### Add a new site

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts",
  method: "POST",
  body: { "host_url": "https://example.com" }
})
```

Returns 201. 409 `HOST_ALREADY_ADDED` → treat as success. 403 `HOSTS_LIMIT_EXCEEDED` → stop.

### Delete a site

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts/https:example.com:443",
  method: "DELETE"
})
```

Irreversible — all analytics for this host are wiped.

### Get site summary (SQI, indexed pages, problem counts)

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts/https:example.com:443/summary"
})
```

Returns aggregated stats: SQI index, indexed page count, problem counts by severity. Use for dashboards.

---

## 3. Verification

### Check verification state

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts/https:example.com:443/verification"
})
```

Response: `{ "verification_uin": "...", "verification_state": "VERIFIED", "verification_type": "META_TAG", "applicable_verifiers": [...] }`.  
States: `NONE`, `IN_PROGRESS`, `VERIFIED`, `VERIFICATION_FAILED`, `INTERNAL_ERROR`.

### Start verification via META_TAG

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts/https:example.com:443/verification?verification_type=META_TAG",
  method: "POST"
})
```

Returns `verification_uin` — add `<meta name="yandex-verification" content="<uin>" />` to homepage `<head>`, then call GET to poll until `VERIFIED`.  
Other types: `DNS` (TXT record), `HTML_FILE` (file at site root), `TXT_FILE` (legacy).  
409 `VERIFICATION_ALREADY_IN_PROGRESS` → idempotent success.

### List co-owners (other verified users for this host)

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts/https:example.com:443/owners"
})
```

---

## 4. Search queries (replaces deleted `webmaster_top_queries`)

### Top queries by shows — last week

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts/https:example.com:443/search-queries/popular/",
  params: {
    order_by: "TOTAL_SHOWS",
    query_indicator: ["TOTAL_SHOWS", "TOTAL_CLICKS", "AVG_SHOW_POSITION", "AVG_CLICK_POSITION"],
    limit: 500
  }
})
```

Returns TOP-3000 queries (paginate 6 × 500 for the full set). Persist `query_id` from each row.

### Top queries by clicks — custom date range

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts/https:example.com:443/search-queries/popular/",
  params: {
    order_by: "TOTAL_CLICKS",
    query_indicator: ["TOTAL_SHOWS", "TOTAL_CLICKS", "AVG_CLICK_POSITION"],
    date_from: "2026-04-01",
    date_to: "2026-04-30",
    limit: 500,
    offset: 0
  }
})
```

### Top queries — mobile only

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts/https:example.com:443/search-queries/popular/",
  params: {
    order_by: "TOTAL_SHOWS",
    query_indicator: ["TOTAL_SHOWS", "TOTAL_CLICKS", "AVG_SHOW_POSITION"],
    device_type_indicator: "MOBILE",
    limit: 500
  }
})
```

Device values: `ALL` (default), `DESKTOP`, `MOBILE`, `TABLET`, `MOBILE_AND_TABLET`.

### Paginate top queries — page 2 (offset 500)

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts/https:example.com:443/search-queries/popular/",
  params: {
    order_by: "TOTAL_SHOWS",
    query_indicator: ["TOTAL_SHOWS", "TOTAL_CLICKS"],
    limit: 500,
    offset: 500
  }
})
```

### Aggregated all-queries history (trend chart)

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts/https:example.com:443/search-queries/all/history",
  params: {
    query_indicator: ["TOTAL_SHOWS", "TOTAL_CLICKS"],
    date_from: "2026-03-01",
    date_to: "2026-05-17"
  }
})
```

Returns time-series `{ "indicators": { "TOTAL_SHOWS": [{date, value}, ...] } }` — no per-query breakdown.

### History for one specific query

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts/https:example.com:443/search-queries/abc123def456/history",
  params: {
    query_indicator: ["TOTAL_SHOWS", "AVG_SHOW_POSITION"],
    date_from: "2026-04-01",
    date_to: "2026-05-17"
  }
})
```

Replace `abc123def456` with the `query_id` from `popular/`. 404 `QUERY_ID_NOT_FOUND` → query fell out of TOP-3000 or expired.

---

## 5. Diagnostics (replaces deleted `webmaster_indexing_issues`)

### Get all site problems

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts/https:example.com:443/diagnostics"
})
```

Response: `{ "problems": { "DISALLOWED_IN_ROBOTS": { "severity": "FATAL", "state": "PRESENT", "last_state_update": "..." }, ... } }`.

Severity tiers:
- `FATAL` — site broken (`DISALLOWED_IN_ROBOTS`, `DNS_ERROR`, `MAIN_PAGE_ERROR`, `THREATS`): alert immediately.
- `CRITICAL` — major risk (`SSL_CERTIFICATE_ERROR`, `SLOW_AVG_RESPONSE_TIME`): alert within 1 h.
- `POSSIBLE_PROBLEM` — SEO-affecting (`NO_SITEMAPS`, `NO_ROBOTS_TXT`, `TOO_MANY_PAGE_DUPLICATES`): planned fix.
- `RECOMMENDATION` — nice-to-have (`NOT_MOBILE_FRIENDLY`, `FAVICON_PROBLEM`, `NO_METRIKA_COUNTER`): weekly digest.

State values: `PRESENT` (active), `ABSENT` (clear), `UNDEFINED` (not enough data — treat as suspicious).

---

## 6. Indexing statistics

### Indexing history by HTTP status class (30-day trend)

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts/https:example.com:443/indexing/history",
  params: {
    date_from: "2026-04-17",
    date_to: "2026-05-17",
    indexing_indicators: ["HTTP_2XX", "HTTP_4XX", "HTTP_5XX"]
  }
})
```

HTTP classes: `HTTP_2XX`, `HTTP_3XX`, `HTTP_4XX`, `HTTP_5XX`, `OTHER` (timeouts, DNS).

### Sample pages that failed to load (FAILED_TO_DOWNLOAD)

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts/https:example.com:443/indexing/samples",
  params: {
    indexing_indicators: "FAILED_TO_DOWNLOAD",
    offset: 0,
    limit: 50
  }
})
```

Indicators: `DOWNLOADED`, `EXCLUDED`, `FAILED_TO_DOWNLOAD`, `SEARCHABLE`. These are samples, not a complete list.

### In-search pages history (how many pages are currently in SERP)

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts/https:example.com:443/indexing/insearch/history",
  params: {
    date_from: "2026-04-01",
    date_to: "2026-05-17"
  }
})
```

### Sample searchable pages

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts/https:example.com:443/indexing/insearch/samples",
  params: { offset: 0, limit: 50 }
})
```

### Search events history (pages added/removed from search)

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts/https:example.com:443/search-events/history",
  params: {
    date_from: "2026-04-01",
    date_to: "2026-05-17"
  }
})
```

---

## 7. Recrawl queue

### Check daily recrawl quota (ALWAYS do this before a batch)

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts/https:example.com:443/recrawl/quota"
})
```

Returns `{ "daily_quota": 100, "quota_remainder": 87 }`. `daily_quota == 0` means the site is likely unverified. Clamp batch to `quota_remainder - safety_margin` (at least 10).

### Submit one URL for recrawl

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts/https:example.com:443/recrawl/queue",
  method: "POST",
  body: { "url": "https://example.com/updated-page" }
})
```

Returns 202 `{ "task_id": "abc123", "quota_remainder": 86 }`. Each POST costs 1 quota unit. 409 `URL_ALREADY_ADDED` → already queued, not an error, quota NOT spent.

### List recent recrawl tasks

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts/https:example.com:443/recrawl/queue",
  params: {
    offset: 0,
    limit: 50,
    date_from: "2026-05-10",
    date_to: "2026-05-17"
  }
})
```

### Check status of a specific recrawl task

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts/https:example.com:443/recrawl/queue/abc123def456"
})
```

`state`: `IN_PROGRESS`, `DONE` (bot loaded — not yet "in search"), `FAILED` (5xx/timeout/robots block).

---

## 8. SQI history

### SQI (site quality index) time series

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts/https:example.com:443/sqi-history",
  params: {
    date_from: "2026-01-01",
    date_to: "2026-05-17"
  }
})
```

Use to chart long-term site quality trend. SQI drives recrawl `daily_quota` — a low SQI means fewer quota units.

---

## 9. Sitemaps

### List all sitemaps (bot-discovered)

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts/https:example.com:443/sitemaps",
  params: { limit: 100 }
})
```

Shows `sources` (`ROBOTS_TXT`, `WEBMASTER`, `INDEX_SITEMAP`), `errors_count`, `urls_count`.

### Get one sitemap by id

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts/https:example.com:443/sitemaps/c7-fe:80-c0"
})
```

### List user-added sitemaps

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts/https:example.com:443/user-added-sitemaps"
})
```

### Submit a sitemap

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts/https:example.com:443/user-added-sitemaps",
  method: "POST",
  body: { "url": "https://example.com/sitemap.xml" }
})
```

Returns 201 `{ "sitemap_id": "..." }`. 409 `SITEMAP_ALREADY_ADDED` → already submitted, not an error — fetch `sitemap_id` via GET.

### Delete a user-added sitemap

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts/https:example.com:443/user-added-sitemaps/c7-fe:80-c0",
  method: "DELETE"
})
```

Removes from user-added list. If the sitemap is also in `robots.txt` it remains in the general list.

---

## 10. Links

### Sample inbound (external) links

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts/https:example.com:443/links/external/samples",
  params: { offset: 0, limit: 100 }
})
```

Returns `count` (total) + `links[]` with `source_url`, `destination_url`, `discovery_date`, `source_last_access_date`.

### Inbound links history (trend line for link mass)

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts/https:example.com:443/links/external/history",
  params: {
    date_from: "2026-01-01",
    date_to: "2026-05-17"
  }
})
```

### Sample broken internal links

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts/https:example.com:443/links/internal/samples",
  params: { offset: 0, limit: 100 }
})
```

Returns pages with broken internal links (`destination_url` returning 4xx/5xx from `source_url`).

### Broken internal links history

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts/https:example.com:443/links/internal/history",
  params: {
    date_from: "2026-04-01",
    date_to: "2026-05-17"
  }
})
```

Trending growth here = site navigation regressed. Use as a technical health KPI.

---

## 11. Important URLs (key-page monitoring)

### List monitored important URLs

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts/https:example.com:443/important-urls"
})
```

### Add a URL to the monitored list

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts/https:example.com:443/important-urls",
  method: "POST",
  body: { "url": "https://example.com/key-landing-page" }
})
```

### History for important URLs (indexing changes)

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts/https:example.com:443/important-urls/history",
  params: {
    date_from: "2026-04-01",
    date_to: "2026-05-17"
  }
})
```

---

## 12. Multi-account usage

When the MCP server has multiple Yandex accounts and the host is associated with a specific one, pass `account` explicitly:

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts/https:example.com:443/search-queries/popular/",
  params: {
    order_by: "TOTAL_SHOWS",
    query_indicator: ["TOTAL_SHOWS", "TOTAL_CLICKS"],
    limit: 500
  },
  account: "marketing-team"
})
```

If the `host_id` is unique across all accounts in the inventory, `account` is resolved automatically via smart routing — you can omit it.

---

## 13. Force-refresh cached response

By default GET responses are cached for TTL (default 3600 s). To bypass the cache (e.g. after a fix):

```
yandex_webmaster_api({
  endpoint: "/v4/user/1234567/hosts/https:example.com:443/diagnostics",
  force_refresh: true
})
```

Use after updating robots.txt, resubmitting a sitemap, or fixing a FATAL problem.

---

## Migration from v0.4

These narrow tools were **removed** in v0.5. Use the `yandex_webmaster_api` equivalents below.

| Deleted v0.4 tool | v0.5 replacement |
|---|---|
| `webmaster_site_summary` | `yandex_webmaster_api({ endpoint: "/v4/user/{uid}/hosts/{hid}/summary" })` |
| `webmaster_top_queries` | `yandex_webmaster_api({ endpoint: "/v4/user/{uid}/hosts/{hid}/search-queries/popular/", params: { order_by: "TOTAL_SHOWS", query_indicator: ["TOTAL_SHOWS","TOTAL_CLICKS","AVG_SHOW_POSITION"], limit: 500 } })` |
| `webmaster_indexing_issues` | `yandex_webmaster_api({ endpoint: "/v4/user/{uid}/hosts/{hid}/diagnostics" })` |

Steps to migrate:
1. Call `yandex_webmaster_api({ endpoint: "/v4/user" })` to get `user_id` → replace `{uid}`.
2. Call `yandex_webmaster_api({ endpoint: "/v4/user/{uid}/hosts" })`, find your host by `ascii_host_url` → replace `{hid}` with the returned `host_id`.
3. Substitute into the endpoint above and call.

After upgrading from v0.4, run `invalidate_cache({})` to clear stale cache entries from deleted tool names.

---

## Common mistakes

- **Using `Bearer` instead of `OAuth` in the Authorization header.** The MCP server handles this — but if you call the API directly, always use `Authorization: OAuth <token>`.
- **Guessing `host_id` from the domain.** `host_id` is `https:example.com:443` (colon-separated, no slashes) — fetch from `/v4/user/{uid}/hosts` and persist.
- **Calling analytics endpoints for unverified hosts.** `HOST_NOT_VERIFIED` returns as 404. Filter `verified: true` when iterating hosts.
- **Omitting `query_indicator` in search-queries calls.** Without it the `indicators` object is empty. Always specify the metrics you need.
- **Sending recrawl batches without checking quota.** Always call `/recrawl/quota` first; clamp to `quota_remainder - 10`.
- **Treating 409 responses as errors.** `URL_ALREADY_ADDED`, `HOST_ALREADY_ADDED`, `SITEMAP_ALREADY_ADDED`, `VERIFICATION_ALREADY_IN_PROGRESS` — all are idempotent success states.
- **Expecting search-query data older than ~90 days.** Yandex keeps detailed data for a limited window. Pull daily into your own DB.
