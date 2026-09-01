# Yandex.Webmaster — Rate limits and quotas

## Two-layer model

Webmaster API has **two independent limits**:

1. **Recrawl daily quota** — `daily_quota` for POST `/recrawl/queue`. Per host, resets daily at 00:00 MSK.
2. **Global rate limit** — overall requests-per-second per token / IP. Not documented numerically; surfaces as 429 `TOO_MANY_REQUESTS_ERROR`.

## Recrawl daily quota

### What it counts

Each successful POST `/v4/user/{user-id}/hosts/{host-id}/recrawl/queue` (HTTP 202) = -1 unit.

What does **not** spend quota:
- POST returning 409 `URL_ALREADY_ADDED` (URL already in queue)
- POST returning 400 `INVALID_URL`
- All GETs — `/recrawl/quota`, `/recrawl/queue`, `/recrawl/queue/{task-id}` are free

### Quota size

`daily_quota` has **no published formula**. Empirical observations:

- Small site without SQI: 10-30/day
- Average site with SQI: 100-200/day
- Large site (news, e-commerce): 500-1000+/day

Yandex adjusts the quota dynamically based on SQI and site behavior. **Do not hardcode** — always GET `/recrawl/quota` first.

> Verify against current docs: exact `daily_quota` formula. Yandex only calls it "the daily quota" without disclosing the algorithm.

### Reset timing

00:00 Moscow time (UTC+3). Until then `quota_remainder=0` → `429 QUOTA_EXCEEDED`.

### Strategy for big volumes

If you need to recrawl 10000 URLs and `daily_quota=200`:

1. Split into 50 daily chunks of 200 URLs.
2. Each day at `00:10 MSK` (slack after reset) submit a chunk.
3. Persist progress (`processed_at`, `task_id`) in the DB.
4. After all POSTs — a separate worker polls `GET /recrawl/queue/{task-id}` for statuses.

## Global rate limit

Per-second / per-minute limit is **not documented**. Empirical guidance:

- Concurrency ≤ 10 simultaneous requests per OAuth token.
- Sustainable rate: 5-10 req/s.
- Burst: short bursts of 20-30 req/s are tolerated, then throttle back.

On excess — 429 `TOO_MANY_REQUESTS_ERROR`, possibly with `Retry-After`.

## Backoff on 429 / 5xx

```python
async def call_with_backoff(client, method, url, **kw):
    for attempt in range(5):
        r = await client.request(method, url, **kw)
        if r.status_code == 200:
            return r.json()
        if r.status_code == 429:
            retry_after = r.headers.get("Retry-After")
            if retry_after:
                await asyncio.sleep(int(retry_after))
            else:
                await asyncio.sleep(min(2 ** attempt, 60) + random.uniform(0, 1))
            continue
        if r.status_code >= 500:
            await asyncio.sleep(min(2 ** attempt, 30))
            continue
        r.raise_for_status()
    raise RateLimitError("max retries exceeded")
```

## Multi-tenant sharing

If you serve multiple users — each with their own OAuth token — limits are **independent**. You can poll 5 users in parallel, 10 req/s each.

But if all 5 go through **the same IP** (your server), an IP-based limit may apply. Either proxy across IPs or cap aggregate at ≤ 10-15 req/s per IP.

## Concurrency on batch recrawl

**Do not parallelize POSTs** on the same host:

```python
# BAD — race on quota_remainder
await asyncio.gather(*[client.recrawl_post(host_id, url) for url in urls])

# GOOD — sequential, response-aware
for url in urls:
    r = await client.recrawl_post(host_id, url)
    if r["quota_remainder"] < 5:
        break  # close to exhaustion
```

Across different hosts — parallel is fine:

```python
await asyncio.gather(*[
    process_host(client, host_id, urls)
    for host_id, urls in host_urls_map.items()
])
```

## Pre-flight check pattern

```python
async def is_quota_available(client, host_id, need: int) -> bool:
    quota = await client.recrawl_quota(host_id)
    safety_margin = 5
    return quota["quota_remainder"] >= need + safety_margin
```

Use before a batch; if false, defer to tomorrow.

## Sliding window for client-side accounting

For higher reliability — keep your own sliding-window req/s counter in Redis:

```python
async def rate_limit_check(redis, token_id, max_per_second=10):
    now = int(time.time())
    key = f"webmaster:rl:{token_id}:{now}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 2)
    if count > max_per_second:
        raise RateLimitError(f"{token_id} exceeded {max_per_second}/s")
```

## Common mistakes

- **Ignoring `Retry-After`** — that is an explicit hint from Yandex; honor it.
- **Parallel POST recrawl** — loses precise `quota_remainder` accounting.
- **No "tomorrow queue"** — a 10k-URL batch breaks halfway and some URLs are lost. Design as a multi-day pipeline.
- **Assuming `daily_quota` is fixed** — it may change at any moment (SQI changes).
- **No cooldown** — sending huge bursts in half-hour windows is better than an even stream all day.
