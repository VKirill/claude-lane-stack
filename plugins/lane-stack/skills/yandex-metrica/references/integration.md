# Integration — production clients (Python + Node.js)

## Python — httpx async client

### Install

```bash
uv pip install httpx redis asyncpg
```

### Base client

```python
# metrika_client.py
import asyncio
import logging
import random
import time
from dataclasses import dataclass
from typing import Any, AsyncIterator

import httpx

logger = logging.getLogger(__name__)


class MetrikaError(Exception):
    def __init__(self, status: int, code: str, message: str, response: dict):
        self.status = status
        self.code = code
        self.message = message
        self.response = response
        super().__init__(f"[{status}/{code}] {message}")


class QuotaExceeded(MetrikaError):
    pass


class RateLimited(MetrikaError):
    def __init__(self, retry_after: float, **kw):
        self.retry_after = retry_after
        super().__init__(**kw)


@dataclass
class TokenBucket:
    rate: float = 30.0
    capacity: float = 30.0
    tokens: float = 30.0
    updated: float = 0.0

    def __post_init__(self):
        self.updated = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self.updated
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
                self.updated = now
                if self.tokens >= 1:
                    self.tokens -= 1
                    return
                wait = (1 - self.tokens) / self.rate
                await asyncio.sleep(wait)


class MetrikaClient:
    BASE_URL = "https://api-metrika.yandex.net"

    def __init__(
        self,
        token: str,
        *,
        max_parallel: int = 3,
        rate_per_sec: float = 30.0,
        logs_rate_per_sec: float = 10.0,
        timeout: float = 60.0,
    ):
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={"Authorization": f"OAuth {token}"},
            timeout=timeout,
            http2=True,
        )
        self._sema = asyncio.Semaphore(max_parallel)
        self._main_bucket = TokenBucket(rate=rate_per_sec, capacity=rate_per_sec)
        self._logs_bucket = TokenBucket(rate=logs_rate_per_sec, capacity=logs_rate_per_sec)

    async def aclose(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.aclose()

    def _bucket_for(self, url: str) -> TokenBucket:
        return self._logs_bucket if "/logrequest" in url else self._main_bucket

    async def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict | None = None,
        json: Any = None,
        stream: bool = False,
        max_attempts: int = 7,
    ) -> httpx.Response:
        bucket = self._bucket_for(url)
        for attempt in range(max_attempts):
            await bucket.acquire()
            async with self._sema:
                try:
                    if stream:
                        # caller will use stream() context manager
                        return await self._client.send(
                            self._client.build_request(method, url, params=params, json=json),
                            stream=True,
                        )
                    r = await self._client.request(method, url, params=params, json=json)
                except httpx.TransportError as e:
                    if attempt == max_attempts - 1:
                        raise
                    wait = min(2 ** attempt, 60) + random.uniform(0, 1)
                    logger.warning("transport error %s; retry in %.1fs", e, wait)
                    await asyncio.sleep(wait)
                    continue

            if r.status_code == 429:
                retry_after = float(r.headers.get("Retry-After", "0"))
                if not retry_after:
                    retry_after = min(2 ** attempt, 60)
                logger.warning("429 on %s; waiting %.1fs", url, retry_after)
                await asyncio.sleep(retry_after + random.uniform(0, 1))
                continue
            if r.status_code in (500, 502, 503, 504):
                wait = min(2 ** attempt, 60) + random.uniform(0, 1)
                logger.warning("%d on %s; retry in %.1fs", r.status_code, url, wait)
                await asyncio.sleep(wait)
                continue
            if not r.is_success:
                body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
                errors = body.get("errors") or [{}]
                code = errors[0].get("error_type", "unknown")
                msg = errors[0].get("message") or body.get("message") or r.text
                if code == "quota_exceeded":
                    raise QuotaExceeded(r.status_code, code, msg, body)
                raise MetrikaError(r.status_code, code, msg, body)
            return r

        raise MetrikaError(0, "max_retries", f"exhausted {max_attempts} retries", {})

    # --- Reporting API ---

    async def stat_data(
        self,
        counter_id: int,
        *,
        dimensions: list[str] | None = None,
        metrics: list[str],
        date1: str = "7daysAgo",
        date2: str = "yesterday",
        filters: str | None = None,
        sort: list[str] | None = None,
        limit: int = 100000,
        offset: int = 1,
        accuracy: str = "full",
        attribution: str = "LASTSIGN",
        extra: dict | None = None,
    ) -> dict:
        params = {
            "ids": counter_id,
            "metrics": ",".join(metrics),
            "date1": date1,
            "date2": date2,
            "limit": limit,
            "offset": offset,
            "accuracy": accuracy,
            "attribution": attribution,
        }
        if dimensions:
            params["dimensions"] = ",".join(dimensions)
        if filters:
            params["filters"] = filters
        if sort:
            params["sort"] = ",".join(sort)
        if extra:
            params.update(extra)
        r = await self._request("GET", "/stat/v1/data", params=params)
        data = r.json()
        if data.get("sampled"):
            logger.warning(
                "Response is SAMPLED: share=%s, size=%s/%s — consider accuracy=full",
                data.get("sample_share"),
                data.get("sample_size"),
                data.get("sample_space"),
            )
        return data

    async def stat_data_paginated(self, counter_id: int, **kwargs) -> AsyncIterator[dict]:
        limit = kwargs.pop("limit", 100000)
        offset = 1
        while True:
            data = await self.stat_data(counter_id, limit=limit, offset=offset, **kwargs)
            rows = data.get("data", [])
            if not rows:
                return
            for row in rows:
                yield row
            if len(rows) < limit:
                return
            offset += limit

    # --- Management API ---

    async def list_counters(self) -> list[dict]:
        r = await self._request("GET", "/management/v1/counters", params={"per_page": 100})
        return r.json().get("counters", [])

    async def list_goals(self, counter_id: int) -> list[dict]:
        r = await self._request("GET", f"/management/v1/counter/{counter_id}/goals")
        return r.json().get("goals", [])

    # --- Logs API ---

    async def logs_evaluate(self, counter_id, *, date1, date2, fields, source="visits"):
        params = {"date1": date1, "date2": date2, "fields": ",".join(fields), "source": source}
        r = await self._request("GET", f"/management/v1/counter/{counter_id}/logrequests/evaluate", params=params)
        return r.json()["log_request_evaluation"]

    async def logs_create(self, counter_id, *, date1, date2, fields, source="visits", attribution="LASTSIGN"):
        params = {"date1": date1, "date2": date2, "fields": ",".join(fields), "source": source}
        if source == "visits":
            params["attribution"] = attribution
        r = await self._request("POST", f"/management/v1/counter/{counter_id}/logrequests", params=params)
        return r.json()["log_request"]

    async def logs_status(self, counter_id, request_id):
        r = await self._request("GET", f"/management/v1/counter/{counter_id}/logrequest/{request_id}")
        return r.json()["log_request"]

    async def logs_clean(self, counter_id, request_id):
        await self._request("POST", f"/management/v1/counter/{counter_id}/logrequest/{request_id}/clean")

    async def logs_list(self, counter_id):
        r = await self._request("GET", f"/management/v1/counter/{counter_id}/logrequests")
        return r.json().get("requests", [])

    async def logs_download_part(self, counter_id, request_id, part_number, dest_path):
        url = f"/management/v1/counter/{counter_id}/logrequest/{request_id}/part/{part_number}/download"
        await self._main_bucket.acquire()
        total = 0
        async with self._sema:
            async with self._client.stream("GET", url) as r:
                r.raise_for_status()
                with open(dest_path, "wb") as f:
                    async for chunk in r.aiter_bytes(chunk_size=1024 * 1024):
                        f.write(chunk); total += len(chunk)
        return total
```

### Logs API worker (submit → poll → download → clean)

```python
# logs_worker.py
import asyncio, logging
from pathlib import Path
import asyncpg

logger = logging.getLogger(__name__)


async def process_log_job(client, pg, *, counter_id, date1, date2, fields, source, dest_dir):
    """Atomic Logs API job: preflight → create → poll → download → clean."""

    ev = await client.logs_evaluate(counter_id, date1=date1, date2=date2, fields=fields, source=source)
    if not ev["possible"]:
        return {"status": "unfeasible", "evaluation": ev}

    # persist intent BEFORE creating, so a restart cannot produce duplicates
    task_id = await pg.fetchval(
        "INSERT INTO metrika_log_tasks (counter_id,date1,date2,source,fields,status) "
        "VALUES ($1,$2,$3,$4,$5,'creating') RETURNING id",
        counter_id, date1, date2, source, fields,
    )

    try:
        req = await client.logs_create(counter_id, date1=date1, date2=date2, fields=fields, source=source)
        request_id = req["request_id"]
        await pg.execute(
            "UPDATE metrika_log_tasks SET request_id=$1, status='polling' WHERE id=$2",
            request_id, task_id,
        )

        delay = 15.0
        while True:
            await asyncio.sleep(delay)
            st = await client.logs_status(counter_id, request_id)
            if st["status"] == "processed":
                parts = st["parts"]; break
            if st["status"] in ("processing_failed", "canceled"):
                await pg.execute("UPDATE metrika_log_tasks SET status='failed' WHERE id=$1", task_id)
                return {"status": "failed", "log_request": st}
            delay = min(delay * 1.5, 300.0)

        dest_dir = Path(dest_dir); dest_dir.mkdir(parents=True, exist_ok=True)
        for part in parts:
            n = part["part_number"]
            path = dest_dir / f"counter_{counter_id}_req_{request_id}_part_{n}.tsv"
            size = await client.logs_download_part(counter_id, request_id, n, str(path))
            await pg.execute(
                "INSERT INTO metrika_log_parts (task_id,part_number,size_bytes,file_path) "
                "VALUES ($1,$2,$3,$4)",
                task_id, n, size, str(path),
            )

        await client.logs_clean(counter_id, request_id)
        await pg.execute(
            "UPDATE metrika_log_tasks SET status='done', cleaned_at=now() WHERE id=$1", task_id,
        )
        return {"status": "done", "task_id": task_id, "parts": len(parts)}

    except Exception:
        await pg.execute("UPDATE metrika_log_tasks SET status='error' WHERE id=$1", task_id)
        raise
```

### Multi-touch attribution from Logs hits

Idea: export raw visits with fields `ym:s:clientID, ym:s:visitID, ym:s:dateTime, ym:s:UTMSource, ym:s:UTMCampaign, ym:s:goal<ID>IsReached`, sort by `(clientID, dateTime)`, group into a per-user touch path, then score:

- **first-touch** = first source in the path
- **last-touch** = last source in the path
- **linear** = equal weight to every source in the path
- **time-decay** = exponential weight `e^(-λ·days_to_conversion)`
- **position-based** = 40% first + 40% last + 20% spread across the middle

Implement via `polars.group_by("ym:s:clientID")` + `pl.col(...).list.*`. See the `polars` skill for the optimal form; the `yandex-metrica` skill is responsible only for a correct export of the raw data.

## PostgreSQL schema

```sql
-- metrika_schema.sql

CREATE TABLE metrika_counters (
    counter_id   BIGINT PRIMARY KEY,
    name         TEXT NOT NULL,
    site         TEXT,
    time_zone    TEXT,
    is_pro       BOOLEAN DEFAULT FALSE,
    metadata     JSONB,
    updated_at   TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE metrika_log_tasks (
    id           BIGSERIAL PRIMARY KEY,
    counter_id   BIGINT NOT NULL REFERENCES metrika_counters,
    request_id   BIGINT UNIQUE,                       -- from Metrika
    date1        DATE NOT NULL,
    date2        DATE NOT NULL,
    source       TEXT NOT NULL CHECK (source IN ('visits','hits')),
    fields       TEXT[] NOT NULL,
    attribution  TEXT,
    status       TEXT NOT NULL,                       -- creating|polling|done|failed|error|unfeasible
    created_at   TIMESTAMPTZ DEFAULT now(),
    cleaned_at   TIMESTAMPTZ
);
CREATE INDEX ON metrika_log_tasks (counter_id, status);
CREATE INDEX ON metrika_log_tasks (status) WHERE status IN ('creating','polling');

CREATE TABLE metrika_log_parts (
    id           BIGSERIAL PRIMARY KEY,
    task_id      BIGINT NOT NULL REFERENCES metrika_log_tasks ON DELETE CASCADE,
    part_number  INT NOT NULL,
    size_bytes   BIGINT NOT NULL,
    file_path    TEXT NOT NULL,
    imported_at  TIMESTAMPTZ,
    UNIQUE (task_id, part_number)
);

-- daily report aggregates (for caching)
CREATE TABLE metrika_daily_stats (
    counter_id     BIGINT NOT NULL,
    date           DATE NOT NULL,
    traffic_source TEXT NOT NULL,
    visits         BIGINT NOT NULL DEFAULT 0,
    users          BIGINT NOT NULL DEFAULT 0,
    bounce_rate    NUMERIC(5,2),
    PRIMARY KEY (counter_id, date, traffic_source)
);
```

## Node.js mirror (undici) — core building blocks

A full TypeScript client is conceptually the same: `undici.request` + `Agent({keepAliveTimeout: 60_000, connections: 6})`, a token bucket at 30 req/s, a semaphore of 3, retry on 429/5xx, header `authorization: 'OAuth ' + token`.

```ts
import { request, Agent } from 'undici';
import { setTimeout as sleep } from 'node:timers/promises';

const BASE = 'https://api-metrika.yandex.net';
const agent = new Agent({ keepAliveTimeout: 60_000, connections: 6 });

async function metrikaFetch<T>(
  token: string,
  path: string,
  { method = 'GET', query }: { method?: string; query?: Record<string, string | number> } = {},
): Promise<T> {
  const url = query
    ? `${BASE}${path}?${new URLSearchParams(
        Object.fromEntries(Object.entries(query).map(([k, v]) => [k, String(v)])),
      )}`
    : BASE + path;
  for (let attempt = 0; attempt < 7; attempt++) {
    const res = await request(url, {
      method,
      headers: { authorization: `OAuth ${token}` },
      dispatcher: agent,
    });
    if (res.statusCode === 429) {
      const wait = Number(res.headers['retry-after'] ?? '0') || Math.min(2 ** attempt, 60);
      await res.body.dump();
      await sleep(wait * 1000);
      continue;
    }
    if (res.statusCode >= 500) {
      await res.body.dump();
      await sleep(Math.min(2 ** attempt, 60) * 1000);
      continue;
    }
    const data = (await res.body.json()) as T & { message?: string };
    if (res.statusCode >= 400) throw new Error(`Metrika ${res.statusCode}: ${data.message ?? 'error'}`);
    return data;
  }
  throw new Error('Metrika: max retries exceeded');
}

// Wrappers:
export const statData = (token: string, q: Record<string, string | number>) =>
  metrikaFetch(token, '/stat/v1/data', { query: q });

export const logsCreate = (token: string, counterId: number, q: Record<string, string | number>) =>
  metrikaFetch(token, `/management/v1/counter/${counterId}/logrequests`, { method: 'POST', query: q });
```

Wrap `metrikaFetch` with a semaphore and token bucket using `p-limit` + a manual refill (the Python example above is 1-to-1 in logic).

## Cost model

Metrika has **no** explicit "points budget" like Search Console or Direct. The budget is measured in **requests** (5000/day per user) and Logs **storage** (10 GB). Empirical request costs:

| Operation | Request cost |
|---|---|
| `GET /stat/v1/data` | 1 |
| Pagination over N pages | N |
| `/stat/v1/data/comparison` | 1 |
| Logs evaluate | 1 |
| Logs create | 1 |
| Logs status poll | 1 per poll |
| Logs download part | 1 per part |
| Logs clean | 1 |
| Management list/get | 1 |

30-day logs of average traffic with 5 fields → 1 create + ~20–60 polls + 5–50 parts + 1 clean ≈ 30–120 requests per job. Out of 5000/day → ~40 such jobs maximum.

There is no soft quota — only the hard 5000. Once exhausted you get `LimitedExceededException` until 00:00 GMT.

## Smoke test

```python
async def smoke_test(token: str, counter_id: int):
    async with MetrikaClient(token) as c:
        counters = await c.list_counters()
        assert any(x["id"] == counter_id for x in counters), "no access to counter"

        data = await c.stat_data(
            counter_id,
            metrics=["ym:s:visits"],
            date1="yesterday", date2="yesterday",
        )
        assert "data" in data, "malformed response"
        print(f"OK: visits yesterday = {data['totals'][0]}")

if __name__ == "__main__":
    import os, asyncio
    asyncio.run(smoke_test(os.environ["METRIKA_TOKEN"], int(os.environ["METRIKA_COUNTER_ID"])))
```
