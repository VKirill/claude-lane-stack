# Indexing API — STRICT WARNING

## What this is NOT

**Google's Indexing API is NOT a general indexation accelerator.** This is the most common misconception.

From Google's official docs:

> "The Indexing API can only be used to crawl pages with either JobPosting or BroadcastEvent embedded in a VideoObject."

> "Any attempts to abuse the Indexing API, including the use of multiple accounts or other means to exceed usage quotas, may result in access being revoked."

For **regular pages** (articles, products, categories, landing pages) the Indexing API is forbidden by policy and has no effect (even when the call returns 200, Google ignores it). Systematic abuse → access revoked, in extreme cases a manual action on the site.

## When you MAY use it

Only when the page contains one of:

1. **JobPosting** schema.org markup — job vacancies (required: `title`, `datePosted`, `hiringOrganization`, `jobLocation`, etc.).
2. **BroadcastEvent** embedded inside a **VideoObject** — live streams (start/end time, `isLiveBroadcast`).

Both content types are short-lived — Google built a fast lane for them because standard indexation cannot keep up.

## Endpoint

`POST https://indexing.googleapis.com/v3/urlNotifications:publish`

OAuth scope: `https://www.googleapis.com/auth/indexing` (separate scope, **not** webmasters).

The service account must be an **Owner** in the Search Console property — Full user is **not** enough for the Indexing API (separate requirement).

## Request

```jsonc
{
  "url": "https://example.com/jobs/senior-dev",
  "type": "URL_UPDATED"        // URL_UPDATED — new/updated page; URL_DELETED — removed
}
```

## Response

```jsonc
{
  "urlNotificationMetadata": {
    "url": "https://example.com/jobs/senior-dev",
    "latestUpdate": {
      "url": "https://example.com/jobs/senior-dev",
      "type": "URL_UPDATED",
      "notifyTime": "2026-05-13T10:22:30.123Z"
    }
  }
}
```

## Batch (up to 100)

`POST https://indexing.googleapis.com/batch` (multipart) — separate endpoint, up to 100 sub-requests per multipart payload. Each sub-request is one `urlNotifications:publish`.

## Status check

`GET https://indexing.googleapis.com/v3/urlNotifications/metadata?url=<URL-encoded>`

Returns the latest `notifyTime` and type. Not "indexed/not" — only that Google was notified.

## Quotas

- 200 calls/day default per project — raise via Google Cloud Console quota request.
- 600 calls/minute.
- On abuse, quota is revoked without warning.

## Sample — Python

```python
from google.oauth2 import service_account
from googleapiclient.discovery import build

creds = service_account.Credentials.from_service_account_file(
    "sa.json",
    scopes=["https://www.googleapis.com/auth/indexing"],
)
svc = build("indexing", "v3", credentials=creds, cache_discovery=False)

# JobPosting / BroadcastEvent ONLY
resp = svc.urlNotifications().publish(body={
    "url": "https://example.com/jobs/senior-dev",
    "type": "URL_UPDATED",
}).execute()
print(resp["urlNotificationMetadata"]["latestUpdate"]["notifyTime"])
```

## What to use instead for regular pages

| Goal | Action |
|---|---|
| Speed up indexation of a new page | Submit sitemap + internal links + social signals |
| Notify about a removed page | 410 Gone or 404 + wait for recrawl |
| Forced re-index on change | Update `lastmod` in the sitemap; "Request Indexing" in the UI (quota 10/day) |
| Mass indexation (migration) | Sitemap-index split into 50k-URL chunks + links + patience |

## Red flag

If the user says "let's set up the Indexing API so my articles get indexed faster" — **STOP**. Explain the restrictions. Recommend sitemap + GSC UI "Request Indexing".
