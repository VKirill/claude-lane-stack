# Rate limits and quotas

Source: [developers.google.com/webmaster-tools/limits](https://developers.google.com/webmaster-tools/limits).

## Search Analytics — `searchanalytics.query`

| Scope | Limit |
|---|---|
| Per-site | 1,200 QPM |
| Per-user | 1,200 QPM |
| Per-project (short) | 40,000 QPM |
| Per-project (daily) | 30,000,000 QPD |

"Load" is measured in two windows: short-term (10 minutes) and long-term (1 day).

## URL Inspection — `urlInspection.index.inspect`

| Scope | Limit |
|---|---|
| Per-site | 600 QPM |
| Per-site (daily) | **2,000 QPD** |
| Per-project | 15,000 QPM |
| Per-project (daily) | 10,000,000 QPD |

**Critical**: 2000/day per site is the bottleneck for large sites. Sharding by property (when a single domain is split across URL-prefix properties) is the only workaround.

## All other resources (Sites, Sitemaps)

| Scope | Limit |
|---|---|
| Per-user | 20 QPS, 200 QPM |
| Per-project | 100,000,000 QPD |

## Indexing API

| Scope | Limit |
|---|---|
| Per-project default | 200 calls/day |
| Per-project | 600 calls/minute |

Raise on request in Google Cloud Console (quota increase form).

## Reset cadence

- Daily limits reset at **midnight Pacific Time** (PST/PDT).
- Short-window (QPM, 100s) — rolling window.
- Not "honest 60s" — it is a token bucket with burst capacity, so a steady stream beats spikes.

## Concurrency strategy

### Search Analytics

- 1200 QPM = 20 RPS sustainable on one site.
- In practice a big report is N small paginated/filtered requests. 10-20 concurrent threads per property is fine.
- Before launching a batch, estimate: `N_property × N_dates × N_filter_combos × pages_per_request_25k`.

### URL Inspection

- Per-site 600 QPM = 10 RPS, but daily 2000 → ~0.023 RPS sustainable. The daily cap is the bottleneck.
- The worker must throttle on **daily cap**, not QPM. Sleep between requests = `86400 / 2000 ≈ 43 s` for even distribution; or "burst at start of day, then stop".
- Persistent cache for 24-72 h is mandatory — never re-inspect the same URL more than once per day.

### Sites / Sitemaps

- 200 QPM per-user = 3.3 RPS. More than enough for CRUD.

## Token bucket sample — Python

```python
import time, asyncio
from collections import deque

class TokenBucket:
    def __init__(self, rps: float, capacity: int | None = None):
        self.rps = rps
        self.cap = capacity or max(1, int(rps * 2))
        self.tokens = self.cap
        self.last = time.monotonic()
        self._lock = asyncio.Lock()

    async def take(self, n: int = 1):
        async with self._lock:
            while True:
                now = time.monotonic()
                self.tokens = min(self.cap, self.tokens + (now - self.last) * self.rps)
                self.last = now
                if self.tokens >= n:
                    self.tokens -= n
                    return
                wait = (n - self.tokens) / self.rps
                await asyncio.sleep(wait)

# Search Analytics
sa_bucket = TokenBucket(rps=20.0, capacity=40)
# URL Inspection — per property
ui_bucket = TokenBucket(rps=10.0, capacity=10)
```

Daily counter — Redis:

```python
async def daily_ok(prop: str) -> bool:
    key = f"gsc:inspect:{prop}:{today_pt():%Y%m%d}"
    n = await redis.incr(key)
    if n == 1:
        # TTL until PT midnight
        await redis.expireat(key, midnight_pt_ts())
    return n <= 2000
```

## Backoff on 429

```python
def backoff(attempt: int) -> float:
    base = min(60, 2 ** attempt)
    jitter = random.uniform(0, 0.3 * base)
    return base + jitter
```

- `429 + reason=dailyLimitExceeded` → **no backoff**, wait for midnight PT.
- `429 + reason in {rateLimitExceeded, userRateLimitExceeded, quotaExceeded}` → exp backoff.

## Batching

- Search Analytics — no batch API on Google's side; parallelize with a semaphore.
- URL Inspection — no batch; parallelism only.
- Indexing API — `https://indexing.googleapis.com/batch` (multipart, 100 sub-requests) — reduces HTTP overhead but not quota.

## When to ask Google for a quota increase

- Search Analytics — usually unnecessary (40k QPM/project is plenty).
- URL Inspection — if 2000/day is too low, **cannot be raised per-site** (hard cap). Only sharding by property helps.
- Indexing API — 200 → 10k/day and higher are granted via the form, but only for confirmed JobPosting / BroadcastEvent use.
