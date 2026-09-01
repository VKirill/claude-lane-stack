# Yandex.Webmaster — End-to-end API Workflow

Step-by-step interaction model from zero to a running daily ETL. Every step lists HTTP method + URL template, headers, request body, response shape, common error paths, and a curl + Python snippet.

Base URL: `https://api.webmaster.yandex.net/v4`
Auth header: `Authorization: OAuth <access_token>` (literal word `OAuth`, not `Bearer`)

---

## 1. Bootstrap: OAuth app → token → user_id → hosts

### 1.1. Register an OAuth app

On [oauth.yandex.com](https://oauth.yandex.com) → "Create new app" → platform "Web services" → set `Redirect URI` → request scopes `webmaster:hostinfo` (read) and `webmaster:verify` (manage verification, recrawl, sitemap). Save → store `client_id` + `client_secret` in a secret manager.

### 1.2. Authorization code flow

Redirect: `https://oauth.yandex.com/authorize?response_type=code&client_id=<CLIENT_ID>&redirect_uri=<URL_ENCODED_REDIRECT>&state=<CSRF_TOKEN>`. After consent Yandex redirects to `redirect_uri?code=<CODE>&state=<CSRF>`. Always verify `state`.

### 1.3. Exchange code for token

```
POST https://oauth.yandex.com/token
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code&code=<CODE>&client_id=<CLIENT_ID>&client_secret=<CLIENT_SECRET>
```
Response 200: `{access_token, expires_in, refresh_token, token_type:"bearer"}`. Persist all four. Full OAuth detail (refresh, rotation, multi-tenant) is in [setup.md](setup.md).

### 1.4. GET /v4/user — fetch `user_id`

```
GET /v4/user
Authorization: OAuth <token>
```
```json
{ "user_id": 1234567 }
```
Persist `user_id`. Reused in every subsequent path.

curl:
```bash
curl -H "Authorization: OAuth $TOKEN" https://api.webmaster.yandex.net/v4/user
```

Python:
```python
import httpx
H = {"Authorization": f"OAuth {token}", "Accept": "application/json"}
r = httpx.get("https://api.webmaster.yandex.net/v4/user", headers=H)
user_id = r.json()["user_id"]
```

### 1.5. List hosts

```
GET /v4/user/{user-id}/hosts
```
```json
{
  "hosts": [
    {
      "host_id": "https:example.com:443",
      "ascii_host_url": "https://example.com:443/",
      "unicode_host_url": "https://example.com:443/",
      "verified": true,
      "main_mirror": {"host_id": "...", "ascii_host_url": "..."},
      "host_data_status": "OK"
    }
  ]
}
```
Persist `host_id` keyed by `(user_id, ascii_host_url)`. Errors: 403 `INVALID_OAUTH_TOKEN`, 403 `INVALID_USER_ID`.

---

## 2. Host verification

### 2.1. Add the host

```
POST /v4/user/{user-id}/hosts
Content-Type: application/json

{ "host_url": "https://example.com" }
```
Success 201. Errors: 409 `HOST_ALREADY_ADDED` (treat as success, GET hosts to pick up `host_id`), 403 `HOSTS_LIMIT_EXCEEDED`.

### 2.2. Get verifier status

```
GET /v4/user/{user-id}/hosts/{host-id}/verification
```
```json
{
  "verification_uin": "abc123def456",
  "verification_state": "NONE",
  "applicable_verifiers": ["DNS", "HTML_FILE", "META_TAG", "TXT_FILE"]
}
```

### 2.3. Place the verification token on the site

Pick one verifier and put the corresponding artifact on the site:

| Verifier | What to place |
|---|---|
| `DNS` | TXT record in the zone: `yandex-verification: <uin>` |
| `HTML_FILE` | File `yandex_<uin>.html` at site root with body `<html><body>Verification: <uin></body></html>` |
| `META_TAG` | `<meta name="yandex-verification" content="<uin>" />` inside `<head>` of homepage |
| `TXT_FILE` | File with unique name (legacy) |

### 2.4. Trigger verification

```
POST /v4/user/{user-id}/hosts/{host-id}/verification?verification_type={DNS|HTML_FILE|META_TAG|TXT_FILE}
```
Response: same shape as the GET, now with `verification_state=IN_PROGRESS`. 409 `VERIFICATION_ALREADY_IN_PROGRESS` is idempotent success.

### 2.5. Poll status

Re-GET `/verification` every 30–60 s until `verification_state ∈ {VERIFIED, VERIFICATION_FAILED, INTERNAL_ERROR}`. Typical wait: 1–10 minutes for `META_TAG` / `HTML_FILE`, up to 24 h for `DNS`. Stop after a sensible cap (e.g. 1 h).

Python:
```python
async def wait_verified(client, host_id, timeout_sec=3600):
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        st = await client.get_verification(host_id)
        if st["verification_state"] in ("VERIFIED", "VERIFICATION_FAILED", "INTERNAL_ERROR"):
            return st
        await asyncio.sleep(45)
    raise TimeoutError("verification polling timed out")
```

---

## 3. Sitemap management

### 3.1. Submit a user-added sitemap

```
POST /v4/user/{user-id}/hosts/{host-id}/user-added-sitemaps
Content-Type: application/json

{ "url": "https://example.com/sitemap.xml" }
```
Response 201:
```json
{ "sitemap_id": "c7-fe:80-c0" }
```
409 `SITEMAP_ALREADY_ADDED` → idempotent. Resolve `sitemap_id` via GET (below).

### 3.2. List user-added sitemaps

```
GET /v4/user/{user-id}/hosts/{host-id}/user-added-sitemaps
```
Use this after a 409 to look up the existing `sitemap_id` by `sitemap_url`.

### 3.3. List ALL sitemaps the bot knows

```
GET /v4/user/{user-id}/hosts/{host-id}/sitemaps?limit=100&from=<cursor>
```
Returns the union of user-added + ones discovered via `robots.txt` + index sitemap children.

### 3.4. Poll processing & errors

```
GET /v4/user/{user-id}/hosts/{host-id}/sitemaps/{sitemap-id}
```
Watch `errors_count`, `urls_count`, `last_access_date`. Yandex re-checks sitemaps on its own schedule (often hours, sometimes days). Do not aggressively poll < 1 h.

### 3.5. Delete user-added sitemap

```
DELETE /v4/user/{user-id}/hosts/{host-id}/user-added-sitemaps/{sitemap-id}
```
Removes user-added entry only; the bot may still know the sitemap via `robots.txt`.

---

## 4. Search analytics

### 4.1. Pull popular queries (TOP-3000)

```
GET /v4/user/{user-id}/hosts/{host-id}/search-queries/popular
    ?order_by=TOTAL_SHOWS
    &query_indicator=TOTAL_SHOWS
    &query_indicator=TOTAL_CLICKS
    &query_indicator=AVG_SHOW_POSITION
    &query_indicator=AVG_CLICK_POSITION
    &device_type_indicator=ALL
    &date_from=2024-01-08&date_to=2024-01-14
    &offset=0&limit=500
```
Response:
```json
{
  "queries": [
    {
      "query_id": "abc123",
      "query_text": "buy bicycle moscow",
      "indicators": {
        "TOTAL_SHOWS": 1234,
        "TOTAL_CLICKS": 56,
        "AVG_SHOW_POSITION": 4.2,
        "AVG_CLICK_POSITION": 3.8
      }
    }
  ],
  "count": 3000,
  "date_from": "2024-01-08",
  "date_to": "2024-01-14"
}
```
Paginate offset = 0, 500, 1000, 1500, 2000, 2500. Stop when fewer than `limit` queries returned.

### 4.2. History for a single query

```
GET /v4/user/{user-id}/hosts/{host-id}/search-queries/{query-id}/history
    ?query_indicator=AVG_SHOW_POSITION&query_indicator=TOTAL_SHOWS
    &date_from=2024-01-01&date_to=2024-03-31
```
404 `QUERY_ID_NOT_FOUND` means the query fell out of TOP-3000. Useful for tracking priority queries; persist `query_id` you care about.

### 4.3. All-queries aggregated history

```
GET /v4/user/{user-id}/hosts/{host-id}/search-queries/all/history
    ?query_indicator=TOTAL_SHOWS&query_indicator=TOTAL_CLICKS
    &date_from=2024-01-01&date_to=2024-03-31
```

### 4.4. 90-day retention caveat

Yandex retains detailed search-query data ~90 days. Requesting older ranges returns empty value arrays without an error. For long-term analytics — snapshot daily into Postgres (see `references/integration.md`).

curl:
```bash
curl -G "https://api.webmaster.yandex.net/v4/user/$UID/hosts/$HID/search-queries/popular" \
  -H "Authorization: OAuth $TOKEN" \
  --data-urlencode "order_by=TOTAL_SHOWS" \
  --data-urlencode "query_indicator=TOTAL_SHOWS" \
  --data-urlencode "query_indicator=TOTAL_CLICKS" \
  --data-urlencode "limit=500"
```

---

## 5. Indexing & recrawl

### 5.1. Indexing history by HTTP class

```
GET /v4/user/{user-id}/hosts/{host-id}/indexing/history?date_from=&date_to=
```
Response (excerpt):
```json
{
  "indicators": {
    "HTTP_2XX": [{"date": "2024-01-15T00:00:00.000+03:00", "value": 1500}],
    "HTTP_4XX": [...]
  }
}
```

### 5.2. Check recrawl quota

```
GET /v4/user/{user-id}/hosts/{host-id}/recrawl/quota
```
```json
{ "daily_quota": 100, "quota_remainder": 87 }
```
**Always** call before a batch. `daily_quota=0` means the host is not verified.

### 5.3. Submit URL for recrawl

```
POST /v4/user/{user-id}/hosts/{host-id}/recrawl/queue
Content-Type: application/json

{ "url": "https://example.com/page.html" }
```
Response 202:
```json
{ "task_id": "abc123def456", "quota_remainder": 86 }
```
Errors:
| HTTP | Code | Quota |
|---|---|---|
| 400 | `INVALID_URL` | not spent |
| 409 | `URL_ALREADY_ADDED` | not spent (idempotent — already queued) |
| 429 | `QUOTA_EXCEEDED` | drained |

### 5.4. Poll task status

```
GET /v4/user/{user-id}/hosts/{host-id}/recrawl/queue/{task-id}
```
```json
{
  "task_id": "abc123",
  "url": "https://example.com/page.html",
  "added_time": "2024-01-15T10:30:00.000+03:00",
  "state": "DONE"
}
```
State: `IN_PROGRESS` → `DONE` / `FAILED`. `DONE` means the bot fetched the page — not that it is in search. Use `indexing/insearch/samples` for the second question. Typical SLA: minutes to hours.

### 5.5. Sequential batch pattern

```python
async def batch_recrawl(client, host_id, urls, safety=5):
    quota = await client.recrawl_quota(host_id)
    if quota["daily_quota"] == 0:
        raise RuntimeError("daily_quota==0 — host not verified")
    max_send = max(0, quota["quota_remainder"] - safety)
    to_send, skipped = urls[:max_send], urls[max_send:]
    sent = []
    for url in to_send:
        try:
            r = await client.recrawl_post(host_id, url)  # already_queued absorbs 409
            sent.append({"url": url, "task_id": r.get("task_id")})
            if (r.get("quota_remainder") or 0) <= safety:
                break
        except WebmasterError as e:
            if e.status == 429:
                break  # QUOTA_EXCEEDED
            raise
    return {"sent": sent, "skipped_for_tomorrow": skipped}
```

Quota resets at 00:00 Moscow time (UTC+3).

---

## 6. Diagnostics

```
GET /v4/user/{user-id}/hosts/{host-id}/diagnostics
```
```json
{
  "problems": {
    "DISALLOWED_IN_ROBOTS": {"severity": "FATAL", "state": "ABSENT", "last_state_update": "2024-01-15T10:30:00.000+03:00"},
    "NO_SITEMAPS": {"severity": "POSSIBLE_PROBLEM", "state": "PRESENT", "last_state_update": "2024-01-10T08:00:00.000+03:00"}
  }
}
```

Wire to monitoring:

```python
async def classify(client, host_id):
    diag = await client.diagnostics(host_id)
    fatal = []
    critical = []
    for ptype, info in diag.get("problems", {}).items():
        if info["state"] != "PRESENT":
            continue
        if info["severity"] == "FATAL":
            fatal.append(ptype)
        elif info["severity"] == "CRITICAL":
            critical.append(ptype)
    if fatal:
        await alert(level="page", problems=fatal)
    if critical:
        await alert(level="warn", problems=critical)
```

`last_state_update` typically lags 24-48 h behind the actual site change. Do not panic if a just-fixed `robots.txt` still shows `PRESENT` for an hour.

---

## 7. Links analysis

### 7.1. External (inbound) sample

```
GET /v4/user/{user-id}/hosts/{host-id}/links/external/samples?offset=0&limit=100
```
```json
{
  "count": 12345,
  "links": [
    {
      "source_url": "https://referrer.com/post1",
      "destination_url": "https://example.com/landing",
      "discovery_date": "2024-01-10",
      "source_last_access_date": "2024-01-14"
    }
  ]
}
```

### 7.2. Internal (broken) sample

```
GET /v4/user/{user-id}/hosts/{host-id}/links/internal/samples?offset=0&limit=100&indicator=BROKEN
```

### 7.3. Pagination

```python
async def fetch_all_external(client, host_id, page=100):
    offset = 0
    out = []
    while True:
        r = await client.links_external_samples(host_id, offset=offset, limit=page)
        if not r["links"]:
            break
        out.extend(r["links"])
        offset += page
        if offset >= r["count"]:
            break
    return out
```

The endpoint is named `samples` deliberately — it returns a sample, not the full backlink universe. For a complete profile use external SEO tools.

---

## 8. Daily ETL pattern

A production scheduler that pulls all per-host data daily, persists into Postgres, dedupes, and alerts on quota drain.

### 8.1. Schedule

- **Cron** in a small server: `0 1 * * * /usr/bin/python -m wm_etl.daily` (01:00 server time).
- **BullMQ** for Node: a `Repeatable` job with cron `0 1 * * *` and a worker that processes one host at a time.

Why 01:00: recrawl quota resets at 00:00 MSK (UTC+3); pulling at 01:00 ensures yesterday's numbers are final.

### 8.2. Per-host job

```python
async def daily_for_host(client, db, host_id):
    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")

    # 1) Search queries — TOP-3000
    indicators = ["TOTAL_SHOWS", "TOTAL_CLICKS", "AVG_SHOW_POSITION", "AVG_CLICK_POSITION"]
    for offset in range(0, 3000, 500):
        page = await client.search_queries_popular(
            host_id, order_by="TOTAL_SHOWS", indicators=indicators,
            offset=offset, limit=500, date_from=yesterday, date_to=yesterday,
        )
        await db.upsert_query_snapshots(host_id, yesterday, page["queries"])
        if len(page["queries"]) < 500:
            break

    # 2) Indexing history (last 7 days for context)
    week_ago = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
    idx = await client.indexing_history(host_id, date_from=week_ago, date_to=yesterday)
    await db.upsert_indexing_history(host_id, idx)

    # 3) Diagnostics — classify and alert
    diag = await client.diagnostics(host_id)
    await db.upsert_diagnostics(host_id, diag)
    await alert_if_fatal(host_id, diag)

    # 4) Recrawl quota — alert on chronic drain
    quota = await client.recrawl_quota(host_id)
    await db.record_quota(host_id, quota)
    if quota["daily_quota"] > 0 and quota["quota_remainder"] == 0:
        await alert_quota_drain(host_id)
```

### 8.3. Dedupe key

Snapshots are unique by `(host_id, snapshot_date, query_id, device)`. Use `INSERT ... ON CONFLICT ... DO UPDATE` to make re-runs idempotent — re-running the job same day should overwrite, not duplicate.

### 8.4. Alerting on quota exhaustion

- `daily_quota == 0` → host lost verification (e.g. user removed the meta tag).
- `quota_remainder == 0` mid-day → batch job consumed it; either intentional or a runaway worker.
- Two consecutive days of `quota_remainder == 0` with low `daily_quota` → request more quota or stagger work.

### 8.5. Multi-tenant scaling

If you serve many users, each with their own OAuth token:
- Limits are per-token, so parallel users are fine.
- One IP across many tokens can still hit an IP-bound limiter — cap your server to ≤ 10-15 req/s in aggregate.
- Stagger per-tenant cron offsets (`0-50 1 * * *` rather than every tenant at `0 1 * * *`) to spread load.

---

## Cross-references

OAuth → [setup.md](setup.md). Hosts/sitemaps → [hosts-and-sitemaps.md](hosts-and-sitemaps.md). Indicators → [search-queries.md](search-queries.md). Recrawl detail → [indexing.md](indexing.md). Errors → [errors.md](errors.md). Quotas → [rate-limits.md](rate-limits.md). Production clients → [integration.md](integration.md).
