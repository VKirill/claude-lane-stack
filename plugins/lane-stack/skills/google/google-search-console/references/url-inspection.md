# URL Inspection API — urlInspection.index.inspect

`POST https://searchconsole.googleapis.com/v1/urlInspection/index:inspect`

> **Note**: different base URL from Webmasters v3 (`searchconsole.googleapis.com`, not `googleapis.com/webmasters`). With `google-api-python-client` the service name is `searchconsole`, not `webmasters`.

## Request body

```jsonc
{
  "inspectionUrl": "https://example.com/blog/post-1",
  "siteUrl": "sc-domain:example.com",      // OR "https://example.com/" — must match property
  "languageCode": "en-US"                  // BCP-47, for localized messages
}
```

- `inspectionUrl` — fully-qualified URL, **must be under the property**.
- `siteUrl` — exactly as in Search Console. URL-prefix properties require the **trailing slash**.
- `languageCode` — optional; affects human-readable text (issue descriptions, etc.).

## Response schema

```jsonc
{
  "inspectionResult": {
    "inspectionResultLink": "https://search.google.com/search-console/inspect?...",
    "indexStatusResult": {
      "verdict": "PASS",                     // PASS | PARTIAL | FAIL | NEUTRAL | VERDICT_UNSPECIFIED
      "coverageState": "Submitted and indexed",
      "robotsTxtState": "ALLOWED",            // ALLOWED | DISALLOWED | ROBOTS_TXT_STATE_UNSPECIFIED
      "indexingState": "INDEXING_ALLOWED",    // INDEXING_ALLOWED | BLOCKED_BY_META_TAG | BLOCKED_BY_HTTP_HEADER | BLOCKED_BY_ROBOTS_TXT | INDEXING_STATE_UNSPECIFIED
      "lastCrawlTime": "2026-05-10T08:32:00Z",
      "pageFetchState": "SUCCESSFUL",         // SUCCESSFUL | SOFT_404 | BLOCKED_ROBOTS_TXT | NOT_FOUND | ACCESS_DENIED | SERVER_ERROR | REDIRECT_ERROR | ACCESS_FORBIDDEN | BLOCKED_4XX | INTERNAL_CRAWL_ERROR | INVALID_URL
      "googleCanonical": "https://example.com/blog/post-1",
      "userCanonical":   "https://example.com/blog/post-1",
      "sitemap": ["https://example.com/sitemap.xml"],
      "referringUrls": ["https://example.com/blog/"],
      "crawledAs": "MOBILE"                   // MOBILE | DESKTOP | CRAWLING_USER_AGENT_UNSPECIFIED
    },
    "ampResult": {                            // null if no AMP
      "verdict": "PASS",
      "ampUrl": "https://example.com/blog/post-1/amp",
      "ampIndexStatusVerdict": "PASS",
      "robotsTxtState": "ALLOWED",
      "indexingState": "AMP_INDEXING_ALLOWED",
      "lastCrawlTime": "...",
      "pageFetchState": "SUCCESSFUL",
      "issues": [{ "issue": "...", "severity": "WARNING" | "ERROR" }]
    },
    "mobileUsabilityResult": {
      "verdict": "PASS",
      "issues": [{ "issue": "...", "severity": "WARNING" | "ERROR", "message": "..." }]
    },
    "richResultsResult": {
      "verdict": "PASS",
      "detectedItems": [
        {
          "richResultType": "Product",
          "items": [{ "name": "...", "issues": [...] }]
        }
      ]
    }
  }
}
```

## verdict semantics

| Verdict | Meaning |
|---|---|
| `PASS` | indexed and no issues for this check |
| `PARTIAL` | indexed with warnings |
| `FAIL` | not indexed or critical errors |
| `NEUTRAL` | no data / not applicable |
| `VERDICT_UNSPECIFIED` | server could not determine |

## coverageState — common values

- `Submitted and indexed`
- `Indexed, not submitted in sitemap`
- `Crawled - currently not indexed`
- `Discovered - currently not indexed`
- `Excluded by 'noindex' tag`
- `Blocked by robots.txt`
- `Page with redirect`
- `Duplicate without user-selected canonical`
- `Duplicate, Google chose different canonical than user`
- `Soft 404`
- `Submitted URL not found (404)`

## Quotas

| Limit | Value |
|---|---|
| Per-site QPM | 600 |
| Per-site QPD | **2000** |
| Per-project QPM | 15,000 |
| Per-project QPD | 10,000,000 |

> 2000/day/property is a **hard cap**. For large sites: prioritize (new/changed URLs first), cache results 24-72 h, rotate across properties if you control several.

## Sample — Python

```python
from googleapiclient.discovery import build
from google.oauth2 import service_account

creds = service_account.Credentials.from_service_account_file(
    "sa.json",
    scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
)
svc = build("searchconsole", "v1", credentials=creds, cache_discovery=False)

resp = svc.urlInspection().index().inspect(body={
    "inspectionUrl": "https://example.com/blog/post-1",
    "siteUrl": "sc-domain:example.com",
    "languageCode": "en-US",
}).execute()

idx = resp["inspectionResult"]["indexStatusResult"]
print(idx["verdict"], idx["coverageState"], idx.get("lastCrawlTime"))
```

## Common gotchas

- `inspectionUrl` not under `siteUrl` → 400 `inspectionUrl is not under siteUrl`. Fix: validate prefix / domain.
- URL-prefix property — `siteUrl="https://example.com/"` with the trailing slash. Without it → 400.
- `lastCrawlTime` missing for URLs Google never crawled.
- `googleCanonical != userCanonical` — canonical mismatch impacting indexation; alert on it.
- `richResultsResult` can be empty even when the page has schema.org — Google may not have parsed/processed it.
- The API does not expose "Test Live URL" (the UI button) — it returns the latest crawl state only.
