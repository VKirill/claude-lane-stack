# Rate limit and retry

The provider enforces **3 requests per second per api_key**. Exceed it and the next request returns HTTP 429. This file covers the client budget, the limiter pattern, and the retry policy.

All numeric defaults below are SSOT in [recommended-defaults.md](recommended-defaults.md). Reference numbers here, do not redefine.

## Client budget

| Knob | Default | Why |
|---|---|---|
| Steady-state target | **2 req/s** | 33% headroom under the 3 req/s hard limit |
| Allowed peak burst | up to **3 req/s** for ≤ 1 s | Provider tolerates one second at the limit |
| Inter-call sleep (sync code) | **≥ 340 ms** | One call every 333 ms ≈ 3 req/s; round up for safety |
| Concurrent in-flight | **2** | Two parallel calls × ~400 ms each ≈ within budget |

Use the SAME limiter across all callers that share the api_key. Two processes each thinking they own the budget = 429 storm.

## Limiter pattern — token bucket

Token bucket of size 3, refilling at 2 tokens/s (steady) or 3 tokens/s (max). Every API call acquires one token before issuing.

### Python — asyncio.Semaphore + sleep

```python
import asyncio, time
from collections import deque

class TokenBucket:
    def __init__(self, rate: float = 2.0, capacity: int = 3):
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.updated_at = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.updated_at
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.updated_at = now
            if self.tokens < 1:
                wait = (1 - self.tokens) / self.rate
                await asyncio.sleep(wait)
                self.tokens = 0
            else:
                self.tokens -= 1
```

Wire it as a dependency: `await bucket.acquire(); resp = await client.get(url)`. Share one `TokenBucket` instance across the whole process.

### Node — bottleneck

```ts
import Bottleneck from "bottleneck";

export const proxy6Limiter = new Bottleneck({
  reservoir: 3,
  reservoirRefreshAmount: 3,
  reservoirRefreshInterval: 1000, // 1 s
  maxConcurrent: 2,
  minTime: 340, // ms between scheduled calls
});

const res = await proxy6Limiter.schedule(() => fetch(url));
```

Use one Bottleneck instance per api_key. Cluster mode if running across multiple processes (Bottleneck supports Redis-backed coordination).

### Cross-process coordination (Redis)

If multiple Node workers or Python processes share the key, use Redis to count tokens.

```python
# Pseudocode — Lua-evaluated atomic token take
LUA = """
local now = tonumber(ARGV[1]); local rate = tonumber(ARGV[2])
local capacity = tonumber(ARGV[3])
local tokens = tonumber(redis.call('HGET', KEYS[1], 'tokens') or capacity)
local ts = tonumber(redis.call('HGET', KEYS[1], 'ts') or now)
tokens = math.min(capacity, tokens + (now - ts) * rate)
local allowed = 0
if tokens >= 1 then tokens = tokens - 1; allowed = 1 end
redis.call('HSET', KEYS[1], 'tokens', tokens, 'ts', now)
redis.call('EXPIRE', KEYS[1], 60)
return allowed
"""
```

## Retry policy

| Trigger | Retry? | Why |
|---|---|---|
| HTTP 429 | YES | rate limited — wait and try again |
| HTTP 5xx | YES | transient server issue |
| Connection reset / DNS / timeout | YES | network |
| `error_id 30` (Error unknown) | YES (once) | undocumented server hiccup |
| `error_id 100` (key) | NO | code/config bug |
| `error_id 105` (IP) | NO | code/config bug |
| `error_id 110/200/210/220/230/240/250/260/270/280` | NO | bad request — fix the call |
| `error_id 300` (stock) | NO | fix count or country, not retry |
| `error_id 400` (no money) | NO | top up balance, not retry |
| `error_id 404` (not found) | NO | bad ids |
| `error_id 410` (price ≤ 0) | NO | bad combination |

**Exponential backoff defaults** (SSOT in [recommended-defaults.md](recommended-defaults.md)):
- base: 500 ms
- multiplier: 2
- cap: 30 s
- max attempts: 5
- jitter: full (random between 0 and computed delay)

So delays roughly: 500 ms → 1 s → 2 s → 4 s → 8 s. With jitter, slightly less on average.

### Python — tenacity

```python
from tenacity import (
    retry, retry_if_exception_type, stop_after_attempt,
    wait_random_exponential,
)
import httpx

class Proxy6RetryableError(Exception): ...
class Proxy6FatalError(Exception): ...

@retry(
    retry=retry_if_exception_type(Proxy6RetryableError),
    wait=wait_random_exponential(multiplier=0.5, max=30),
    stop=stop_after_attempt(5),
    reraise=True,
)
async def call(client: httpx.AsyncClient, url: str) -> dict:
    await bucket.acquire()
    resp = await client.get(url, timeout=10.0)
    if resp.status_code == 429:
        raise Proxy6RetryableError("rate limit")
    if resp.status_code >= 500:
        raise Proxy6RetryableError(f"server {resp.status_code}")
    data = resp.json()
    if data.get("status") == "no":
        eid = data.get("error_id")
        if eid == 30:
            raise Proxy6RetryableError("unknown server error")
        raise Proxy6FatalError(f"error_id {eid}: {data.get('error')}")
    return data
```

### Node — p-retry

```ts
import pRetry, { AbortError } from "p-retry";

async function call(url: string): Promise<unknown> {
  return pRetry(
    async () => {
      const res = await proxy6Limiter.schedule(() =>
        fetch(url, { signal: AbortSignal.timeout(10_000) })
      );
      if (res.status === 429) throw new Error("rate limit");
      if (res.status >= 500) throw new Error(`server ${res.status}`);
      const data = (await res.json()) as { status: string; error_id?: number; error?: string };
      if (data.status === "no") {
        if (data.error_id === 30) throw new Error("unknown server error");
        throw new AbortError(`error_id ${data.error_id}: ${data.error}`); // fatal — do not retry
      }
      return data;
    },
    { retries: 5, factor: 2, minTimeout: 500, maxTimeout: 30_000, randomize: true }
  );
}
```

`AbortError` from `p-retry` short-circuits the retry loop for fatal envelope errors.

## Timeout

Per-request HTTP timeout: **10 s**. proxy6.net usually responds in <500 ms; if it doesn't, the network path is degraded and retry will help. Do not raise to 30 s or 60 s — that just stretches the failure window without recovering.

Pair with abort signals so retries don't pile up requests against an unresponsive server.

## What to log

On every API call log: method, params (with `api_key` masked), response `status`, `error_id` if any, HTTP status, latency, attempt number. Do NOT log the response `list` payload (proxy credentials).
