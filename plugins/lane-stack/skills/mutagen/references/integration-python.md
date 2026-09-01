# Python integration — httpx + tenacity + pydantic

Reference implementation patterns. Defaults from [recommended-defaults.md](recommended-defaults.md).

## Dependencies

```toml
# pyproject.toml
[project.dependencies]
httpx = "*"          # async HTTP
tenacity = "*"       # retry decorators
pydantic = "*"       # response shape validation
```

## Env var

```python
import os

API_KEY = os.environ["MUTAGEN_API_KEY"]
BASE_URL = "http://api.mutagen.ru/json"
```

NEVER hardcode `API_KEY`. Load from env at startup; raise loudly if missing.

## Client skeleton

```python
import asyncio
import httpx
from tenacity import (
    retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type,
)
from pydantic import BaseModel, Field

class MutagenTransientError(Exception): ...
class MutagenTerminalError(Exception): ...

class MutagenClient:
    def __init__(self, api_key: str, *, timeout: float = 30.0):
        self._api_key = api_key
        self._client = httpx.AsyncClient(
            base_url=f"{BASE_URL}/{api_key}",
            timeout=httpx.Timeout(timeout, connect=10.0),
            headers={"Content-Type": "application/json; charset=utf-8"},
        )

    async def close(self) -> None:
        await self._client.aclose()

    @retry(
        retry=retry_if_exception_type(MutagenTransientError),
        wait=wait_random_exponential(multiplier=0.5, max=30),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    async def _call(self, method: str, params: dict | None = None,
                    *, use_post: bool = False) -> dict:
        url = f"/{method}/"
        try:
            if use_post:
                resp = await self._client.post(url, json=params or {})
            else:
                resp = await self._client.get(url, params=params or {})
        except (httpx.ConnectError, httpx.ReadTimeout) as e:
            raise MutagenTransientError(str(e)) from e
        if 500 <= resp.status_code < 600:
            raise MutagenTransientError(f"HTTP {resp.status_code}")
        if resp.status_code >= 400:
            raise MutagenTerminalError(f"HTTP {resp.status_code} {resp.text[:200]}")
        return resp.json()
```

## Free methods

```python
    async def balance(self) -> float:
        data = await self._call("mutagen.balance")
        return float(data["balance"])

    async def progects(self) -> list[dict]:
        return await self._call("mutagen.progects")

    async def progect_keywords(self, progect_id: int) -> list[dict]:
        return await self._call(
            "mutagen.progect.keywords",
            {"progect_id": progect_id},
        )
```

## `check_key` async helper

```python
class CheckKeyResult(BaseModel):
    key: str
    strong: int
    wordstat: int
    tails: int
    direct_spec: float = Field(alias="spec")
    direct_first: float = Field(alias="first")
    direct_garant: float = Field(alias="garant")
    vital: str | bool
    vital_site: str

class TaskStore:
    """Persist task_id per keyword for idempotency."""
    async def get(self, key: str) -> int | None: ...
    async def put(self, key: str, task_id: int) -> None: ...

    async def check_key_new(self, key: str) -> dict:
        return await self._call("mutagen.check_key.new", {"key": key})

    async def check_key_get(self, task_id: int) -> dict:
        return await self._call(
            "mutagen.check_key.get",
            {"task_id": task_id},
        )

    async def check_key_with_polling(
        self, key: str, store: TaskStore,
        *,
        initial_delay: float = 2.0,
        cap: float = 30.0,
        max_attempts: int = 60,
    ) -> dict:
        # 1. Idempotency lookup
        task_id = await store.get(key)
        if task_id is None:
            resp = await self.check_key_new(key)
            task_id = int(resp["task_id"])
            await store.put(key, task_id)

        # 2. Poll
        delay = initial_delay
        for _ in range(max_attempts):
            resp = await self.check_key_get(task_id)
            status = resp.get("status")
            if status == "completed":
                return resp
            if status in ("rejected", "error"):
                raise MutagenTerminalError(
                    f"check_key terminal state {status} for task_id={task_id}"
                )
            await asyncio.sleep(min(delay, cap))
            delay = min(delay * 1.5, cap)
        raise MutagenTerminalError(f"check_key timeout for task_id={task_id}")
```

## `parser.mass` batch helper

```python
    async def parser_mass_new(
        self,
        keys_list: list[str],
        name: str,
        parser: str,
        region_id: str = "0",
    ) -> int:
        # Always dedupe + normalize before submit
        keys_list = _normalize_keys(keys_list)
        data = await self._call(
            "mutagen.parser.mass.new",
            {
                "keys_list": keys_list,
                "name": name,
                "parser": parser,
                "region_id": region_id,
            },
            use_post=True,  # always POST — likely > 100 KB
        )
        return int(data["id"])

    async def parser_mass_id(self, mass_id: int) -> dict:
        return await self._call(
            "mutagen.parser.mass.id",
            {"mass_id": mass_id},
        )

    async def parser_mass_with_polling(
        self, mass_id: int,
        *,
        initial_delay: float = 5.0,
        cap: float = 60.0,
        max_attempts: int = 120,
    ) -> dict:
        delay = initial_delay
        for _ in range(max_attempts):
            resp = await self.parser_mass_id(mass_id)
            status = resp.get("status")
            if status == "finish":
                return resp["data"]
            if status == "error":
                raise MutagenTerminalError(
                    f"parser.mass terminal state for mass_id={mass_id}"
                )
            await asyncio.sleep(min(delay, cap))
            delay = min(delay * 1.5, cap)
        raise MutagenTerminalError(f"parser.mass timeout for mass_id={mass_id}")


def _normalize_keys(raw: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for k in raw:
        k = " ".join(k.strip().split()).casefold()
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(k)
    return out
```

## `serp.report` with row-count probe

```python
    async def serp_report(
        self,
        *,
        region: str,
        report: str,
        keyword: str | None = None,
        keywords: list[str] | None = None,
        domain: str | None = None,
        domain_with_subdomains: str | None = None,
        page: str | None = None,
        filter: list[dict] | None = None,
        sort: str | None = None,
        limit: int | None = None,
        count: bool = False,
    ) -> list[dict] | dict:
        params: dict = {"region": region, "report": report}
        if keyword is not None:
            params["keyword"] = keyword
        if keywords is not None:
            params["keywords"] = ",".join(keywords[:1000])  # provider max
        if domain is not None:
            params["domain"] = domain
        if domain_with_subdomains is not None:
            params["domain_with_subdomains"] = domain_with_subdomains
        if page is not None:
            params["page"] = page
        if filter is not None:
            params["filter"] = filter
        if sort is not None:
            params["sort"] = sort
        if limit is not None:
            params["limit"] = limit
        if count:
            params["count"] = 1

        # POST when filter chain is large or keywords is long
        use_post = (
            (keywords and len(",".join(keywords)) > 50_000)
            or (filter and len(filter) > 10)
        )
        return await self._call("mutagen.serp.report", params, use_post=use_post)

    async def serp_report_probe_count(
        self, *, region: str, report: str, **element_kwargs,
    ) -> int:
        resp = await self.serp_report(
            region=region, report=report, count=True, **element_kwargs,
        )
        return int(resp["count"])
```

## Balance gating helper

```python
class InsufficientFunds(Exception): ...

async def gate_balance(
    client: MutagenClient, expected_cost: float, *, safety: float = 2.0,
) -> None:
    balance = await client.balance()
    if balance < expected_cost * safety:
        raise InsufficientFunds(
            f"balance={balance} < expected_cost={expected_cost} × safety={safety}"
        )
```

## Usage examples

### Check competition for one keyword

```python
async def main() -> None:
    client = MutagenClient(API_KEY)
    try:
        await gate_balance(client, expected_cost=1.0)  # cushion for ~3 paid calls
        store = MyTaskStore()  # implement against PG / Redis
        result = await client.check_key_with_polling("купить квадроцикл", store)
        print(result)
    finally:
        await client.close()
```

### Mass-parse frequency

```python
async def parse_frequencies(client: MutagenClient, raw_keys: list[str]) -> dict:
    keys = _normalize_keys(raw_keys)
    expected = len(keys) * 0.05  # rate from config
    await gate_balance(client, expected, safety=2.0)

    mass_id = await client.parser_mass_new(
        keys_list=keys,
        name="semantics-2026-05-q1",
        parser="wordstat_qso",
        region_id="213",
    )
    # PERSIST mass_id IMMEDIATELY before the first poll
    await my_db.save_mass_id(mass_id, len(keys))
    data = await client.parser_mass_with_polling(mass_id)
    return data
```

### SERP report with safe probe

```python
async def fetch_organic_keywords(
    client: MutagenClient, domain: str, region: str = "yandex_msk",
) -> list[dict]:
    filter_ = [
        {"column": "region_wsqso", "filter_type": "gr_or_eq", "val": 100},
        {"column": "words",        "filter_type": "less_or_eq", "val": 7},
    ]
    n = await client.serp_report_probe_count(
        region=region, report="report_keywords_organic",
        domain=domain, filter=filter_,
    )
    if n > 5000:
        raise ValueError(f"refuse full pull: {n} rows")
    return await client.serp_report(
        region=region, report="report_keywords_organic",
        domain=domain, filter=filter_, limit=min(n, 5000),
        sort="-region_wsqso",
    )
```

## Testing pattern (pytest + respx)

```python
import pytest
import respx
from httpx import Response

@pytest.mark.asyncio
async def test_check_key_polling_completes() -> None:
    async with respx.mock(base_url=f"{BASE_URL}/{API_KEY}") as mock:
        mock.get("/mutagen.check_key.new/").mock(
            return_value=Response(200, json={"task_id": 1, "status": "created"})
        )
        # First poll: processed; second poll: completed
        get_route = mock.get("/mutagen.check_key.get/")
        get_route.side_effect = [
            Response(200, json={"task_id": 1, "status": "processed"}),
            Response(200, json={
                "status": "completed", "key": "test", "strong": 5,
                "wordstat": 100, "tails": 1000,
                "direct": {"spec": 1.0, "first": 0.5, "garant": 0.5},
                "vital": "", "vital_site": "",
            }),
        ]
        client = MutagenClient(API_KEY)
        store = InMemoryTaskStore()
        result = await client.check_key_with_polling(
            "test", store, initial_delay=0.01, max_attempts=5,
        )
        assert result["strong"] == 5
        await client.close()
```

## Things NOT to do

Refer to [wrong-vs-right.md](wrong-vs-right.md) for the full anti-pattern catalogue. Summary:

- Don't loop `parser.get` — use `parser.mass.new`.
- Don't tight-loop `check_key.get` — use exp backoff.
- Don't call `check_key.new` without persistent task_id lookup — double-charges.
- Don't omit balance pre-check on paid batches.
- Don't hardcode `API_KEY` or print full URL with key.
