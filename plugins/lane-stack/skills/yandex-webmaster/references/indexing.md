# Yandex.Webmaster — Indexing & Recrawl

## Indexing statistics

### History — dynamics by HTTP class

```
GET /v4/user/{user-id}/hosts/{host-id}/indexing/history
    ?date_from=YYYY-MM-DD
    &date_to=YYYY-MM-DD
    [&indexing_indicators=...]
```

Defaults to the current day if dates are omitted.

**Response**:

```json
{
  "indicators": {
    "HTTP_2XX": [{"date": "2024-01-15T00:00:00.000+03:00", "value": 1500}],
    "HTTP_3XX": [...],
    "HTTP_4XX": [...],
    "HTTP_5XX": [...],
    "OTHER": [...]
  }
}
```

Status categories (`IndexingStatusEnum`):

| Status | Meaning |
|---|---|
| `HTTP_2XX` | loaded successfully |
| `HTTP_3XX` | redirect (counted separately) |
| `HTTP_4XX` | client errors (404, 403…) |
| `HTTP_5XX` | server errors |
| `OTHER` | timeouts, DNS errors, unreachable |

### Samples — example loaded pages

```
GET /v4/user/{user-id}/hosts/{host-id}/indexing/samples
    ?indexing_indicators={DOWNLOADED|EXCLUDED|FAILED_TO_DOWNLOAD|SEARCHABLE}
    &offset=0&limit=10
```

Returns example URLs for the category. Quick diagnostics: which URLs in particular failed.

### In-search history

```
GET /v4/user/{user-id}/hosts/{host-id}/indexing/insearch/history?date_from=&date_to=
```

Dynamics of pages **in search** (`SEARCHABLE`) — not everything downloaded reaches search.

### In-search samples

```
GET /v4/user/{user-id}/hosts/{host-id}/indexing/insearch/samples?offset=&limit=
```

Example searchable pages.

### Search events (added/removed from search)

```
GET /v4/user/{user-id}/hosts/{host-id}/search-events/history?date_from=&date_to=
GET /v4/user/{user-id}/hosts/{host-id}/search-events/samples?offset=&limit=
```

Event history: pages entered or left search.

## Indexing indicators

| Indicator | Meaning |
|---|---|
| `SEARCHABLE` | in search |
| `DOWNLOADED` | loaded by bot |
| `EXCLUDED` | excluded from search (various reasons) |
| `FAILED_TO_DOWNLOAD` | load failed |

## Recrawl URL queue

### Check quota

```
GET /v4/user/{user-id}/hosts/{host-id}/recrawl/quota
```

```json
{
  "daily_quota": 100,
  "quota_remainder": 87
}
```

- `daily_quota` — daily allowance of recrawl requests for this site. Depends on SQI / site type (more for larger sites). **No official formula** — treat as variable.
- `quota_remainder` — left until end of day (UTC+3 / Moscow).

**Always** call before a batch.

> Verify against current docs: exact `daily_quota` rule — the docs call it "the daily quota" without a formula.

### Submit URL for recrawl

```
POST /v4/user/{user-id}/hosts/{host-id}/recrawl/queue
Content-Type: application/json

{ "url": "https://example.com/page.html" }
```

**Response 202**:

```json
{
  "task_id": "abc123def456",
  "quota_remainder": 86
}
```

`quota_remainder` is returned with every 202 — usable for real-time monitoring without a separate GET `/quota`.

### POST errors

| HTTP | Code | Meaning | Quota |
|---|---|---|---|
| 400 | `INVALID_URL` | invalid URL or not belonging to this host | not spent |
| 403 | `INVALID_USER_ID` | token belongs to another user | — |
| 404 | `HOST_NOT_VERIFIED` | site not verified | — |
| 409 | `URL_ALREADY_ADDED` | URL already in queue (DONE/IN_PROGRESS task exists) | **not spent** |
| 429 | `QUOTA_EXCEEDED` | daily quota drained | — |

### Task list

```
GET /v4/user/{user-id}/hosts/{host-id}/recrawl/queue
    ?offset=0&limit=50
    [&date_from=][&date_to=]
    [&state=IN_PROGRESS|DONE|FAILED]
```

- `limit`: min 1, default 50
- `offset`: default 0

**Response**:

```json
{
  "tasks": [
    {
      "task_id": "abc123",
      "url": "https://example.com/page.html",
      "added_time": "2024-01-15T10:30:00.000+03:00",
      "state": "DONE"
    }
  ],
  "count": 234
}
```

### One task

```
GET /v4/user/{user-id}/hosts/{host-id}/recrawl/queue/{task-id}
```

**Response**:

```json
{
  "task_id": "abc123",
  "url": "https://example.com/page.html",
  "added_time": "2024-01-15T10:30:00.000+03:00",
  "state": "DONE"
}
```

State (`RecrawlStatusEnum`):

| State | Meaning |
|---|---|
| `IN_PROGRESS` | queued / processing |
| `DONE` | bot fetched successfully (does **not** mean indexed in search, only loaded) |
| `FAILED` | could not load (5xx, timeout, blocked in robots.txt) |

Error 404 `TASK_NOT_FOUND` — task_id stale / belonged to another host.

## Batch recrawl pattern

```python
async def batch_recrawl(client, host_id, urls: list[str]) -> dict:
    # 1. Pre-check
    quota = await client.recrawl_quota(host_id)
    if quota["daily_quota"] == 0:
        raise RuntimeError("daily_quota == 0 — site likely not verified")

    # 2. Clamp batch to remainder with safety margin
    safety = 10
    max_send = max(0, quota["quota_remainder"] - safety)
    batch = urls[:max_send]
    skipped = urls[max_send:]

    # 3. Send sequentially (avoid race on quota_remainder, catch 409/429)
    results = []
    for url in batch:
        try:
            r = await client.recrawl_post(host_id, url)
            results.append({"url": url, "task_id": r["task_id"], "state": "QUEUED"})
        except HTTPError as e:
            if e.status == 409:  # URL_ALREADY_ADDED → ok
                results.append({"url": url, "state": "ALREADY_QUEUED"})
            elif e.status == 429:  # QUOTA_EXCEEDED → stop
                results.append({"url": url, "state": "QUOTA_EXCEEDED"})
                break
            else:
                raise
    return {"sent": results, "skipped_for_tomorrow": skipped}
```

## Important URLs (key-page monitoring)

```
GET  /v4/user/{user-id}/hosts/{host-id}/important-urls
POST /v4/user/{user-id}/hosts/{host-id}/important-urls

GET  /v4/user/{user-id}/hosts/{host-id}/important-urls/history
```

URLs that Yandex monitors separately and warns about status changes. **Not recrawl** — just a watch list.

## Quota reset timing

`daily_quota` resets at 00:00 Moscow time (UTC+3). 429 `QUOTA_EXCEEDED` is not permanent — it clears at midnight MSK.

## Common mistakes

- **POST without pre-check `/quota`** — batch of 500 against a site with `daily_quota=100` → 100 OK, 1 hits 429, the rest is `QUOTA_EXCEEDED`.
- **Parallel POSTs (10+)** on the same host — race conditions, duplicate 409, lost `quota_remainder` accuracy. Send sequentially or carefully track `quota_remainder` from each response.
- **Treating `DONE` as "in search"** — it only means "loaded". For search membership use `/indexing/insearch/samples`.
- **Not persisting `task_id`** — without it you cannot check the task status later.
- **Using `indexing/samples` for a full page list** — these are **samples** (limit 1-100), not the full set.
