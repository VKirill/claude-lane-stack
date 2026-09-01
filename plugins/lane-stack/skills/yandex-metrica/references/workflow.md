# End-to-end API workflow

Concrete, copy-pasteable workflows that cover the whole lifecycle from token to daily ETL. For deeper detail on any step, see the matching reference file.

Base URL: `https://api-metrika.yandex.net`. All requests carry `Authorization: OAuth <token>` (the official scheme; `Bearer <token>` is also accepted).

## 1. Bootstrap — OAuth scopes and counter discovery

Choose the **minimum** scope. Read-only analytics needs only `metrika:read`.

| Scope | Allows |
|---|---|
| `metrika:read` | Reporting API, Logs API, read counter settings, list counters |
| `metrika:write` | CRUD on counters / goals / filters / operations / representatives |
| `metrika:expenses` | Expense imports (covered by `metrika:write`) |
| `metrika:user_params` | User-params imports (covered by `metrika:write`) |
| `metrika:offline_data` | Offline-conversions / CRM / calls imports (covered by `metrika:write`) |
| `passport:business` | Add for Yandex ID Business (org) accounts |

Discover counters this token can see:

```bash
# HTTP: GET /management/v1/counters
curl -sS -H "Authorization: OAuth $METRIKA_TOKEN" \
  "https://api-metrika.yandex.net/management/v1/counters?per_page=100" | jq
```

Response excerpt:

```json
{
  "counters": [
    {
      "id": 12345678,
      "name": "My site",
      "site": "example.ru",
      "status": "Active",
      "owner_login": "vasya",
      "permission": "view",
      "pro": false,
      "time_zone_name": "Europe/Moscow"
    }
  ],
  "rows": 1
}
```

- `id` → use as `ids=` (Reporting) or in `/counter/{id}/...` (Management/Logs)
- `permission`: `own` / `view` / `edit`
- `pro: true` = Metrika Pro (larger Logs API storage quota)

Errors: 401 = bad token, 403 = no access, empty `counters` = token owner has no counters. See `references/integration.md` for a typed Python wrapper.

## 2. Standard reporting via /stat/v1/data

`GET /stat/v1/data` returns a tabular report.

```
GET /stat/v1/data?
  ids=<counter_id>
  &dimensions=<csv ym:...>
  &metrics=<csv ym:...>
  &date1=YYYY-MM-DD  (or today/yesterday/NdaysAgo)
  &date2=YYYY-MM-DD
  &filters=<DSL expression, URL-encoded>
  &sort=<csv, prefix "-" for DESC>
  &limit=100000  &offset=1
  &accuracy=full
  &attribution=LASTSIGN
Header: Authorization: OAuth <token>
```

curl — visits by traffic source, finance-grade accuracy:

```bash
curl -sS -H "Authorization: OAuth $METRIKA_TOKEN" -G \
  "https://api-metrika.yandex.net/stat/v1/data" \
  --data-urlencode "ids=$COUNTER_ID" \
  --data-urlencode "dimensions=ym:s:date,ym:s:lastTrafficSource" \
  --data-urlencode "metrics=ym:s:visits,ym:s:users,ym:s:bounceRate" \
  --data-urlencode "date1=2026-04-01" \
  --data-urlencode "date2=2026-04-30" \
  --data-urlencode "sort=-ym:s:visits" \
  --data-urlencode "limit=100000" \
  --data-urlencode "accuracy=full" \
  --data-urlencode "attribution=LASTSIGN"
```

Response shape (excerpt):

```json
{
  "data": [
    {
      "dimensions": [{"name": "2026-04-15"}, {"name": "organic", "id": "organic"}],
      "metrics": [12453, 9871, 23.45]
    }
  ],
  "total_rows": 1453,
  "sampled": false,
  "sample_share": 1.0,
  "data_lag": 119,
  "totals": [389172, 215430, 28.12]
}
```

Always inspect `sampled` and `sample_share`. If `sampled: true` and the report is finance-grade, re-run with `accuracy=full`.

### Pagination

```python
async def paginate(client, params: dict):
    """Yield rows page-by-page; stop when fewer than `limit` come back."""
    offset, limit = 1, 100000
    while True:
        r = await client.get("/stat/v1/data", params={**params, "limit": limit, "offset": offset})
        r.raise_for_status()
        rows = r.json()["data"]
        if not rows:
            return
        for row in rows:
            yield row
        if len(rows) < limit:
            return
        offset += limit
```

### Errors to expect

| Status / code | Meaning | Fix |
|---|---|---|
| 400 `invalid_parameter` | typo in dimension/metric | check `/stat/openapi/dimensions` |
| 400 `dimension_metric_namespace_mismatch` | mixing namespaces | one namespace per query, or wrap with `EXISTS()` |
| 400 `too_many_dimensions` | > 10 dimensions | reduce |
| 403 | wrong owner / scope | `GET /management/v1/counters` |
| 429 | rate limit | honor `Retry-After`, back off |

## 3. Sub-endpoints — when to use which

| Endpoint | Use case |
|---|---|
| `/stat/v1/data` | Tabular report — the default |
| `/stat/v1/data/bytime` | Time series for charts; needs `group=day/week/month` and `top_keys=N` |
| `/stat/v1/data/drilldown` | Hierarchical exploration; pass `parent_id=[...]` to expand a node |
| `/stat/v1/data/comparison` | A/B compare segments or periods; duplicate params with `_a`/`_b` suffixes |
| `/stat/v1/data/comparison/drilldown` | Comparison + drill-down |

Example — series over 30 days, top-7 browsers:

```
GET /stat/v1/data/bytime?ids=12345678
   &metrics=ym:s:visits
   &date1=30daysAgo&date2=yesterday
   &group=day&top_keys=7
   &dimensions=ym:s:browser
```

Example — A/B compare months:

```
GET /stat/v1/data/comparison?ids=12345678
   &metrics=ym:s:users
   &dimensions=ym:s:trafficSource
   &date1_a=2026-04-01&date2_a=2026-04-30
   &date1_b=2026-03-01&date2_b=2026-03-31
```

When the URL exceeds ~8 KB (long `filters` or many `direct_client_logins`), switch to POST with `application/x-www-form-urlencoded` or `application/json` — same endpoint, same params.

## 4. Logs API — raw hits export (5 steps)

Asynchronous: minimum total latency from submit to download is minutes, often hours.

### 4.1 Evaluate (pre-flight, free)

```
GET /management/v1/counter/{counter_id}/logrequests/evaluate
   ?date1=YYYY-MM-DD
   &date2=YYYY-MM-DD
   &source=visits         (or hits)
   &fields=ym:s:visitID,ym:s:date,ym:s:dateTime,ym:s:lastTrafficSource
```

Response:

```json
{
  "log_request_evaluation": {
    "possible": true,
    "max_possible_day_quantity": 365,
    "expected_size": 154872931,
    "log_request_sum_size": 2147483648,
    "log_request_sum_max_size": 10737418240
  }
}
```

- `possible: false` → cannot run (e.g. quota or range too wide)
- `max_possible_day_quantity` → trim the date range to this
- `log_request_sum_size` / `log_request_sum_max_size` → quota usage / cap (10 GB)

Always call this before `POST /logrequests` on wide ranges.

### 4.2 Create the job

```
POST /management/v1/counter/{counter_id}/logrequests
   ?date1=YYYY-MM-DD
   &date2=YYYY-MM-DD
   &source=visits
   &fields=ym:s:visitID,ym:s:date,ym:s:dateTime,ym:s:lastTrafficSource
   &attribution=LASTSIGN    (only for source=visits)
```

Response:

```json
{
  "log_request": {
    "request_id": 9876543,
    "counter_id": 12345678,
    "source": "visits",
    "status": "created",
    "parts": [],
    "size": 0,
    "attribution": "LASTSIGN"
  }
}
```

**Persist `request_id` to the DB BEFORE returning to the caller.** A crash now means a duplicate job on retry and double quota consumption.

Sources: `visits` (one row per session) or `hits` (one row per page view). Fields: ≤ 3000 chars, valid for the chosen `source`.

### 4.3 Poll status

```
GET /management/v1/counter/{counter_id}/logrequest/{request_id}
```

```json
{
  "log_request": {
    "request_id": 9876543,
    "status": "processed",
    "size": 154872931,
    "parts": [
      {"part_number": 0, "size": 67108864},
      {"part_number": 1, "size": 67108864},
      {"part_number": 2, "size": 20655203}
    ]
  }
}
```

Lifecycle:

| Status | Meaning | Action |
|---|---|---|
| `created` | Queued | keep polling |
| `processed` | Ready | proceed to download |
| `awaiting_retry` | Transient error | keep polling |
| `processing_failed` | Terminal | log + recreate (or fewer fields) |
| `canceled` | Cancelled | recreate |
| `cleaned_by_user` | Removed via `/clean` | recreate if still needed |
| `cleaned_automatically_as_too_old` | Auto-removed after 7 days | recreate |

Cadence: start at 15–30 s, grow exponentially, cap at ~5 min. Avoid sub-second polling — bookkeeping eats your 5000/day budget.

### 4.4 Download parts

For each `part_number` in `parts[]`:

```
GET /management/v1/counter/{counter_id}/logrequest/{request_id}/part/{part_number}/download
```

Returns **TSV** (tab-separated values, UTF-8, header in the first line). Stream large parts — do not buffer. Code: `references/integration.md` (`logs_download_part`).

You may download parts in parallel, but stay within `3 concurrent per user_login` and `10 req/s for Logs API`.

### 4.5 Clean (free the quota)

```
POST /management/v1/counter/{counter_id}/logrequest/{request_id}/clean
```

Call **once all parts are confirmed on disk**. Skipping this is the #1 reason for `400 quota_exceeded`. After `/clean`, status becomes `cleaned_by_user` and parts are no longer downloadable.

Auxiliary:

```
GET  /management/v1/counter/{id}/logrequests                # list all jobs
POST /management/v1/counter/{id}/logrequest/{rid}/cancel    # cancel an active job
```

## 5. Goals and filters CRUD via Management API

Scope: `metrika:write`.

Create a URL goal (visit a thank-you page):

```bash
curl -sS -X POST \
  -H "Authorization: OAuth $METRIKA_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api-metrika.yandex.net/management/v1/counter/$COUNTER_ID/goals" \
  -d '{
    "goal": {
      "name": "Thank you page",
      "type": "url",
      "is_retargeting": false,
      "conditions": [{"type": "exact", "url": "https://example.com/thank-you"}]
    }
  }'
```

Goal types: `url` / `number` / `step` / `composite` / `action` / `phone` / `email` / `messenger` / `file` / `search` / `payment_system`. `conditions[].type`: `exact` / `contain` / `start` / `regexp`.

Filters (bots / IP / domains):

```json
{
  "filter": {
    "attr": "client_ip",
    "type": "interval",
    "value": "192.168.0.0",
    "value2": "192.168.255.255",
    "action": "exclude",
    "status": "active"
  }
}
```

`attr`: `client_ip` / `referer` / `url` / `title` / `uniq_id`. `action`: `include` / `exclude` / `only_mirrors`.

List, get, update, delete follow the standard pattern: `GET/POST /goals`, `GET/PUT/DELETE /goal/{goal_id}`, same for `/filters/{filter_id}`.

## 6. Quotas and defensive backoff

| Scope | Quota | Reset |
|---|---|---|
| Per IP | 30 req/s | rolling |
| Per IP (Logs API) | 10 req/s | rolling |
| Per user_login | 3 parallel | rolling |
| Per user_login | 5000 req/day | 00:00 GMT (03:00 MSK) |
| Per user_login on `/stat/v1/data/` | 200 req / 5 min | 5-min window |
| Per counter, Logs storage | 10 GB | `/clean` or 7-day auto |
| Single Logs request | 365-day range, 3000-char `fields` | n/a |

Defensive client recipe:

```python
import asyncio, random, time, httpx

class TokenBucket:
    def __init__(self, rate=30.0, capacity=30.0):
        self.rate, self.capacity = rate, capacity
        self.tokens = capacity
        self.updated = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                self.tokens = min(self.capacity, self.tokens + (now - self.updated) * self.rate)
                self.updated = now
                if self.tokens >= 1:
                    self.tokens -= 1
                    return
                await asyncio.sleep((1 - self.tokens) / self.rate)


class MetrikaClient:
    BASE = "https://api-metrika.yandex.net"

    def __init__(self, token: str):
        self._c = httpx.AsyncClient(
            base_url=self.BASE,
            headers={"Authorization": f"OAuth {token}"},
            timeout=60,
        )
        self._sema = asyncio.Semaphore(3)                  # 3 parallel per user_login
        self._main = TokenBucket(rate=30, capacity=30)     # 30 req/s per IP
        self._logs = TokenBucket(rate=10, capacity=10)     # 10 req/s for Logs API

    def _bucket(self, url: str) -> TokenBucket:
        return self._logs if "/logrequest" in url else self._main

    async def request(self, method: str, url: str, **kw) -> httpx.Response:
        for attempt in range(7):
            await self._bucket(url).acquire()
            async with self._sema:
                r = await self._c.request(method, url, **kw)
            if r.status_code == 429:
                # honor Retry-After if present, otherwise exponential backoff
                wait = float(r.headers.get("Retry-After", "0")) or min(2 ** attempt, 60)
                await asyncio.sleep(wait + random.uniform(0, 1))
                continue
            if r.status_code in (500, 502, 503, 504):
                await asyncio.sleep(min(2 ** attempt, 60) + random.uniform(0, 1))
                continue
            return r
        r.raise_for_status()
        return r
```

The daily 5000 budget is best tracked out-of-band in Redis (see `references/rate-limits.md`).

## 7. Daily ETL — schedule and persistence

Pattern: run once per day after the counter's TZ midnight + safety lag. Pull `yesterday`'s aggregates via Reporting, optionally pull a Logs API dump for `yesterday`, persist with idempotent merge keys so re-runs are safe.

Schema, idempotent UPSERT, and a full async worker live in `references/integration.md` (`metrika_daily_stats`, `metrika_log_tasks`, `metrika_log_parts`). The merge key is `(counter_id, date, traffic_source)` — `ON CONFLICT DO UPDATE` keeps re-runs idempotent.

Daily-run flow:

1. One **wide** Reporting query for `yesterday` with `accuracy=full`, `attribution=LASTSIGN`, all dimensions/metrics you need — one daily request beats N narrow ones.
2. UPSERT into `metrika_daily_stats` keyed by `(counter_id, date, traffic_source)`.
3. Submit a Logs API job for the same date via the worker in §4 (Logs API). Land TSV in `/data/metrika/{counter_id}/{date}` for downstream ClickHouse / DuckDB.

Operational hygiene:

- **TZ aware**: `date` is in the counter's timezone — reconcile before joining with UTC data from other systems.
- **Lag-tolerant**: never run for `today`; data finalizes for up to 3 days. Re-run yesterday's pull for D-3..D-1 to catch late sessions.
- **Idempotent**: PK `(counter_id, date, traffic_source)` + UPSERT means re-runs only correct values, never duplicate rows.
- **Quota-aware**: a wide query with 10 dimensions costs the same 1 daily request as a narrow one — aggregate.
- **Persistence-first for Logs**: the worker writes `request_id` before returning so a restart resumes the same job.

## Smoke test

```python
async def smoke(token: str, counter_id: int):
    async with httpx.AsyncClient(
        base_url="https://api-metrika.yandex.net",
        headers={"Authorization": f"OAuth {token}"}, timeout=30,
    ) as c:
        # 1. Token can see this counter
        r = await c.get("/management/v1/counters", params={"per_page": 100})
        r.raise_for_status()
        assert any(x["id"] == counter_id for x in r.json()["counters"]), "no access"

        # 2. Minimal report for yesterday
        r = await c.get("/stat/v1/data", params={
            "ids": counter_id, "metrics": "ym:s:visits",
            "date1": "yesterday", "date2": "yesterday",
        })
        r.raise_for_status()
        print("visits yesterday:", r.json()["totals"][0])
```

If both calls return 200 — token, scope, and `counter_id` are wired correctly.
