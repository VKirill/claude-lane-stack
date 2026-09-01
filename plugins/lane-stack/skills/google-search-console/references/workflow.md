# End-to-end API workflows

A linear walk through the GSC API surface — each step lists HTTP method, URL, request/response shape, minimal Python + Node samples, and common error codes.

## 1. Bootstrap — auth and property

### 1.1 Pick a scope

| Scope | Use |
|---|---|
| `https://www.googleapis.com/auth/webmasters.readonly` | read-only |
| `https://www.googleapis.com/auth/webmasters` | full (sitemap submit, sites add) |
| `https://www.googleapis.com/auth/indexing` | Indexing API (JobPosting / BroadcastEvent only) |

### 1.2 Pick an auth path

- **User OAuth 2.0**: standard Authorization Code + `refresh_token` (offline access, `prompt=consent`).
- **Service account JSON**: JWT signed with the private key → exchange for access token at `https://oauth2.googleapis.com/token`.

### 1.3 Service account grant — CANNOT self-grant

A human owner must add the service account email in the GSC UI:

`Search Console → property → Settings → Users and permissions → Add user → role: Restricted | Full`

Without this step every call returns:

```
403 forbidden: User does not have sufficient permission for site 'sc-domain:example.com'
```

### 1.4 Pick the property type

| Property type | `siteUrl` format | Verification | Aggregation |
|---|---|---|---|
| URL-prefix | `https://www.example.com/` (trailing slash required) | HTML / DNS / GA / GTM | exact subdomain + protocol only |
| Domain | `sc-domain:example.com` | DNS TXT only | all protocols + all subdomains |

Data from the two **does not** match — a Domain property sees more impressions than any single URL-prefix.

### 1.5 Bootstrap sanity check

```bash
curl -H "Authorization: Bearer $TOKEN" https://www.googleapis.com/webmasters/v3/sites
```

Expect a `siteEntry[]` with `permissionLevel` in {siteOwner, siteFullUser, siteRestrictedUser}. `siteUnverifiedUser` means added without a role — API will return no data.

## 2. Search Analytics — query lifecycle

### 2.1 Endpoint

`POST https://www.googleapis.com/webmasters/v3/sites/{siteUrl}/searchAnalytics/query`

`siteUrl` is fully URL-encoded in the path.

### 2.2 Request shape

```jsonc
{
  "startDate": "2026-04-15",
  "endDate":   "2026-05-12",
  "dimensions": ["query", "page", "country", "device"],
  "type": "web",                       // web|discover|googleNews|news|image|video
  "aggregationType": "auto",           // auto|byPage|byProperty|byNewsShowcasePanel
  "dimensionFilterGroups": [{
    "groupType": "and",                // only "and"
    "filters": [
      { "dimension": "country", "operator": "equals", "expression": "rus" },
      { "dimension": "device",  "operator": "equals", "expression": "MOBILE" }
    ]
  }],
  "rowLimit": 25000,                   // 1..25000
  "startRow": 0,
  "dataState": "final"                 // final | all | hourly_all
}
```

Filter operators: `equals` (default) · `notEquals` · `contains` · `notContains` · `includingRegex` · `excludingRegex` (RE2 syntax).

### 2.3 Response shape

```jsonc
{
  "rows": [
    { "keys": ["query A", "https://example.com/p"], "clicks": 12, "impressions": 320, "ctr": 0.0375, "position": 4.2 }
  ],
  "responseAggregationType": "byPage",
  "metadata": { "first_incomplete_date": "2026-05-10" }
}
```

### 2.4 25k pagination

Hard cap = 25,000 rows. No next-page-token; loop with `startRow += 25000`. Stop when `len(rows) < rowLimit` (including 0).

Python:

```python
def paginate(svc, site_url, body, page=25_000):
    out, start = [], 0
    while True:
        body = {**body, "rowLimit": page, "startRow": start}
        rows = svc.searchanalytics().query(siteUrl=site_url, body=body).execute().get("rows", [])
        out.extend(rows)
        if len(rows) < page:
            return out
        start += page
```

Node:

```ts
async function paginate(sc, siteUrl, body, page = 25_000) {
  const out: any[] = [];
  for (let startRow = 0; ; startRow += page) {
    const { data } = await sc.searchanalytics.query({
      siteUrl, requestBody: { ...body, rowLimit: page, startRow },
    });
    const rows = data.rows ?? [];
    out.push(...rows);
    if (rows.length < page) return out;
  }
}
```

### 2.5 Common error codes

| HTTP | reason | Cause |
|---|---|---|
| 400 | `badRequest` | invalid date / dimension / regex |
| 403 | `forbidden` | SA not added to property |
| 404 | `notFound` | siteUrl unknown to user |
| 429 | `quotaExceeded` / `userRateLimitExceeded` | 1200 QPM per-site or per-user |
| 500 / 503 | `backendError` | transient — retry with jitter |

## 3. URL Inspection — index.inspect

### 3.1 Endpoint

`POST https://searchconsole.googleapis.com/v1/urlInspection/index:inspect`

Different base host from Webmasters v3.

### 3.2 Request shape

```jsonc
{
  "inspectionUrl": "https://example.com/blog/post-1",
  "siteUrl": "sc-domain:example.com",  // must match the property exactly
  "languageCode": "en-US"              // BCP-47, optional
}
```

### 3.3 Response shape

```jsonc
{
  "inspectionResult": {
    "indexStatusResult": {
      "verdict": "PASS",                    // PASS|PARTIAL|FAIL|NEUTRAL|VERDICT_UNSPECIFIED
      "coverageState": "Submitted and indexed",
      "robotsTxtState": "ALLOWED",
      "indexingState": "INDEXING_ALLOWED",
      "lastCrawlTime": "2026-05-10T08:32:00Z",
      "pageFetchState": "SUCCESSFUL",
      "googleCanonical": "https://example.com/blog/post-1",
      "userCanonical":   "https://example.com/blog/post-1",
      "sitemap": ["https://example.com/sitemap.xml"],
      "referringUrls": ["https://example.com/blog/"],
      "crawledAs": "MOBILE"
    },
    "ampResult": { "verdict": "...", "issues": [...] },
    "mobileUsabilityResult": { "verdict": "...", "issues": [...] },
    "richResultsResult": { "verdict": "...", "detectedItems": [...] }
  }
}
```

### 3.4 Hard quota — 2000/day/property

The per-site daily cap is non-negotiable. Strategies:

- Persist `INCR gsc:inspect:{property}:{YYYYMMDD}` in Redis with TTL until PT midnight; stop the worker at ~1900/2000.
- Prioritize new / changed URLs (from sitemap diff) over re-checks.
- Cache results for 24-72 h in `gsc_url_inspection`.
- Sleep `86400 / 2000 ≈ 43s` for even distribution.

### 3.5 Common error codes

| HTTP | reason | Cause |
|---|---|---|
| 400 | `inspectionUrl is not under siteUrl` | wrong property |
| 403 | `forbidden` | SA not added |
| 429 | `dailyLimitExceeded` | 2000/day exhausted — wait for PT midnight |
| 429 | `rateLimitExceeded` | 600 QPM exceeded |

Python:

```python
resp = svc.urlInspection().index().inspect(body={
    "inspectionUrl": "https://example.com/blog/post-1",
    "siteUrl": "sc-domain:example.com",
    "languageCode": "en-US",
}).execute()
idx = resp["inspectionResult"]["indexStatusResult"]
```

Node:

```ts
const { data } = await sc.urlInspection.index.inspect({
  requestBody: { inspectionUrl, siteUrl, languageCode: "en-US" },
});
```

## 4. Sites + Sitemaps CRUD

### 4.1 Sites

| Operation | Method | Path |
|---|---|---|
| List | GET | `/webmasters/v3/sites` |
| Get | GET | `/webmasters/v3/sites/{siteUrl}` |
| Add | PUT | `/webmasters/v3/sites/{siteUrl}` (body empty; does **not** verify) |
| Delete | DELETE | `/webmasters/v3/sites/{siteUrl}` |

`permissionLevel`: `siteOwner` · `siteFullUser` · `siteRestrictedUser` · `siteUnverifiedUser` (last = no data).

### 4.2 Sitemaps

| Operation | Method | Path |
|---|---|---|
| List | GET | `/webmasters/v3/sites/{siteUrl}/sitemaps` |
| Get | GET | `/webmasters/v3/sites/{siteUrl}/sitemaps/{feedpath}` |
| Submit | PUT | `/webmasters/v3/sites/{siteUrl}/sitemaps/{feedpath}` |
| Delete | DELETE | `/webmasters/v3/sites/{siteUrl}/sitemaps/{feedpath}` |

`feedpath` must be URL-encoded: `encodeURIComponent("https://example.com/sitemap.xml")`. Submit/delete require the full `webmasters` scope.

Processing state in the response:

```jsonc
{
  "path": "https://example.com/sitemap.xml",
  "lastSubmitted": "2026-05-10T12:34:56Z",
  "lastDownloaded": "2026-05-12T03:11:42Z",
  "isPending": false,
  "isSitemapsIndex": true,
  "type": "sitemap",       // sitemap|rssFeed|atomFeed|urlList|patternSitemap|notSitemap
  "errors": 0,
  "warnings": 2,
  "contents": [ { "type": "web", "submitted": 12345 } ]
}
```

`errors > 0` does not mean an HTTP failure — submission returned 200; inspect the field to surface parse problems.

## 5. Indexing API — STRICT WARNING

### 5.1 Endpoint and policy

`POST https://indexing.googleapis.com/v3/urlNotifications:publish` — scope `auth/indexing`.

Google states the Indexing API "can only be used to crawl pages with either JobPosting or BroadcastEvent embedded in a VideoObject". Using it for regular pages is policy abuse — Google can revoke access and, in extreme cases, apply a manual action on the site.

### 5.2 Request

```jsonc
{ "url": "https://example.com/jobs/senior-dev", "type": "URL_UPDATED" }   // or URL_DELETED
```

### 5.3 Response

```jsonc
{
  "urlNotificationMetadata": {
    "url": "https://example.com/jobs/senior-dev",
    "latestUpdate": { "type": "URL_UPDATED", "notifyTime": "2026-05-13T10:22:30Z" }
  }
}
```

### 5.4 Service account role

The SA must be **Owner** on the property (Full user is **not** enough). Quota defaults to 200 calls/day per project; raise via Cloud Console quota form.

### 5.5 Batch

`POST https://indexing.googleapis.com/batch` — multipart, up to 100 sub-requests per call. Reduces HTTP overhead, not quota.

### 5.6 What to do for regular pages instead

Sitemap + internal links + (for forced re-index on changes) `lastmod` bump + GSC UI "Request Indexing" (10/day). Never call this API for non-JobPosting / non-BroadcastEvent pages.

## 6. Quota management

| API | Per-site | Per-user | Per-project |
|---|---|---|---|
| Search Analytics | 1200 QPM | 1200 QPM | 40,000 QPM · 30,000,000 QPD |
| URL Inspection | 600 QPM · **2000 QPD** | — | 15,000 QPM · 10,000,000 QPD |
| Other (Sites/Sitemaps) | — | 20 QPS · 200 QPM | 100,000,000 QPD |
| Indexing API | — | — | 200 QPD default · 600 QPM |

Daily limits reset at PT midnight. Short windows are rolling token buckets.

### 6.1 429 retry policy

```python
def backoff(attempt: int) -> float:
    return min(60, 2 ** attempt) + random.uniform(0, 0.3 * min(60, 2 ** attempt))
```

- `429 + reason=dailyLimitExceeded` → **do not retry**; wait for PT midnight.
- `429 + reason in {rateLimitExceeded, userRateLimitExceeded, quotaExceeded}` → exponential backoff with jitter, max 60 s.
- 500 / 503 → up to 5 retries with jitter.
- 401 → refresh access token once; if still 401 → fatal.

## 7. Daily ETL into PostgreSQL

### 7.1 Schedule

- Cron at 06:00 UTC — well after the 2-3 day data lag.
- Fetch `searchanalytics.query` for `[today-3, today-3]`, `dimensions=[query,page,country,device]`, `dataState=final`, paginated by 25k.

### 7.2 Persist (UPSERT)

```sql
INSERT INTO gsc_search_analytics
  (site_url, date, query, page, country, device, search_appearance,
   clicks, impressions, ctr, position)
VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
ON CONFLICT (site_url, date, query, page, country, device, search_appearance)
DO UPDATE SET clicks=EXCLUDED.clicks, impressions=EXCLUDED.impressions,
              ctr=EXCLUDED.ctr, position=EXCLUDED.position, fetched_at=now();
```

### 7.3 Account for the freshness lag

- `dataState: "final"` (default) — excludes incomplete days (the 2-3 day lag).
- `dataState: "all"` — includes recomputable rows; safe for dashboards, unsafe for historical reports.
- Read `metadata.first_incomplete_date` to know when data may still change.

### 7.4 Downstream

- Diff today's snapshot vs yesterday's → enqueue changed pages into URL Inspection.
- Inspection worker upserts into `gsc_url_inspection` with the per-property daily limiter.
- Sitemap health check: `sitemaps.list` once a day → alert on `errors > 0` or `lastDownloaded` older than 7 days.
