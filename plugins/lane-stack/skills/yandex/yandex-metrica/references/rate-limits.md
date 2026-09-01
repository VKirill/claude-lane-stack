# Rate limits and quotas

## Summary table

| Limit | Quota | Reset |
|---|---|---|
| Requests from a single IP | **30 req/s** API-wide | rolling, recovers under 30 |
| Logs API requests | **10 req/s** per IP | same |
| Parallel requests per user_login | **3** | recovers under 3 |
| Requests per user_login per day | **5000 req/day** | **00:00 GMT** (= 03:00 MSK) |
| Requests to `/stat/v1/data/` per user_login | **200 req / 5 min** | rolling 5-min window |
| Prepared Logs API storage | **10 GB per counter** | `POST /clean` or 7-day auto |
| Max range in Logs API | **365 days** per request | n/a |
| Logs API `fields` | **3000 chars** | n/a |
| Dimensions per Reporting request | **10** | n/a |
| Unique dimensions/metrics inside `filters` | **10** | n/a |
| Conditions inside `filters` (AND/OR) | **20** | n/a |
| `filters` expression length | **10 000 chars** | n/a |
| Values per `IN()` | **100** | n/a |
| Representatives per counter | **3 additions per hour** | every new hour |
| Reports via the web UI | **400 req / 5 min** | rolling 5-min window |

## Quota hierarchy

```
┌──────────────────────────────────────────┐
│ IP-level: 30 req/s (10 req/s for Logs)   │  ← outer gate
├──────────────────────────────────────────┤
│ user_login: 5000 req/day, 3 parallel     │  ← per-token
├──────────────────────────────────────────┤
│ Endpoint: 200 req/5min on /stat/v1/data/ │  ← per-endpoint per-user
├──────────────────────────────────────────┤
│ Storage: 10 GB per counter (Logs)        │  ← per-counter
└──────────────────────────────────────────┘
```

Exceeding **any** quota → 429 with `Retry-After`.

## Daily 5000 budget economics

```
24 hours = 1440 minutes
5000 / 1440 = ~3.47 req/min average
```

A dashboard that polls every minute burns the budget in ~24 minutes once it crosses 3 req/min. Strategies:

1. **5–15 min cache**. Dashboard reads the DB; a background worker refreshes the DB every 5–15 minutes. 5000 lasts the day.
2. **Aggregate queries**. One request with 10 dimensions and 5 metrics is not 10 requests. Make the UI batch-fetch.
3. **Daily counter in Redis**. Track real-time usage; alert when usage > 80% before noon.
4. **Per-team tokens**. Different teams get their own OAuth app and token, each with its own 5000.

```python
import redis.asyncio as redis
from datetime import datetime, timezone

async def check_daily_quota(r: redis.Redis, user_login: str) -> int:
    """Return remaining budget; raise QuotaExceeded once it hits 0."""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    key = f"metrika:quota:{user_login}:{today}"
    used = await r.incr(key)
    if used == 1:
        await r.expire(key, 86400 + 3600)  # 1 day + 1h overlap
    if used > 5000:
        raise QuotaExceeded(f"Daily quota for {user_login} exceeded ({used}/5000)")
    return 5000 - used
```

## 200 req / 5 min on `/stat/v1/data/`

This limit is **separate** from the 5000/day cap — both count in parallel. A typical API server with 2–3 concurrent requests at one-minute intervals does ~30–60 req per 5 min, comfortably inside the cap. ETL bursts hit it quickly.

## 3 parallel per user_login

A semaphore is mandatory:

```python
import asyncio

class MetrikaClient:
    def __init__(self, token):
        self._token = token
        self._sema = asyncio.Semaphore(3)

    async def get(self, url, params):
        async with self._sema:
            return await self._client.get(url, params=params)
```

Without a semaphore, N concurrent tasks will trip 429.

## 30 req/s per IP — token bucket

```python
import asyncio, time

class TokenBucket:
    def __init__(self, rate=30, capacity=30):
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.updated = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.updated
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.updated = now
            while self.tokens < 1:
                wait = (1 - self.tokens) / self.rate
                await asyncio.sleep(wait)
                now = time.monotonic()
                elapsed = now - self.updated
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
                self.updated = now
            self.tokens -= 1
```

For Logs API use `rate=10, capacity=10`.

## Logs API 10 GB

The most painful quota. Every `processed` log occupies storage **until an explicit `POST /clean`** or **until the 7-day auto-cleanup**.

```python
async def cleanup_old_processed(client, counter_id):
    """Clean every processed job we have already downloaded."""
    r = await client.get(f"/management/v1/counter/{counter_id}/logrequests")
    requests = r.json()["requests"]
    for req in requests:
        if req["status"] == "processed":
            # check our DB: did we download all parts?
            if downloaded_all_parts(req["request_id"]):
                await client.post(
                    f"/management/v1/counter/{counter_id}/logrequest/{req['request_id']}/clean"
                )
```

Schedule via cron hourly or right after each successful download.

## Monitoring

Worth collecting:

- `metrika_requests_total{endpoint,counter_id,status}` — Prometheus-style
- `metrika_429_rate` — 429 frequency per endpoint
- `metrika_daily_quota_used` — gauge, updated per request
- `metrika_logs_storage_bytes{counter_id}` — sum of `size` across uncleaned logs
- `metrika_logs_pending_tasks{counter_id}` — jobs in `created`/`awaiting_retry`

Alerts:

- 80% of daily quota used before 50% of the day → predictive warning
- 90% of logs storage used → clean now
- 429 rate > 5% over 5 minutes → reduce concurrency

## Pro tier

Activating **Yandex Metrika Pro** (paid subscription) provides:

- A larger Logs storage quota (exact value via support; typically 3–5x)
- A higher representatives cap
- SLA / priority support

API endpoints are unchanged. Counter responses return `"pro": true`.

## Best-practice summary

1. **Dashboard cache** — mandatory, 5–15 minutes minimum.
2. **Semaphore of 3** — per user_login.
3. **Token bucket 30 req/s / 10 req/s** — client-side, do not rely on server-side throttling.
4. **Daily counter in Redis** — alert at 80%.
5. **Auto-clean Logs** — cron hourly or right after each download.
6. **Backoff on 429** — `Retry-After` first, exponential second.
7. **Quota telemetry** — a dedicated metric so you see traffic spikes coming.
