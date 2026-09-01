# Python integration — httpx + tenacity + pydantic

Reference implementation for an async Python client.

## Dependencies

```toml
[project]
dependencies = [
  "httpx>=0.27",
  "tenacity>=8.2",
  "pydantic>=2.0",
]
```

For testing: `pytest`, `pytest-asyncio`, `respx`.

## File layout (suggestion)

```
proxy6_client/
├── __init__.py
├── client.py       # Proxy6Client (httpx wrapper + rate limit + retry)
├── models.py       # Pydantic schemas for envelopes and per-method responses
├── exceptions.py   # Typed exceptions per error_id
└── limiter.py      # TokenBucket
```

## Models

```python
# models.py
from typing import Literal, Optional
from pydantic import BaseModel, Field

Version = Literal["3", "4", "5", "6"]

class ErrorEnvelope(BaseModel):
    status: Literal["no"]
    error_id: int
    error: str

class SuccessEnvelope(BaseModel):
    status: Literal["yes"]
    user_id: str
    balance: str
    currency: Literal["RUB", "USD"]

class Proxy(BaseModel):
    id: str
    version: Version
    ip: str
    host: str
    port: str
    user: str
    pass_: str = Field(alias="pass")
    type: Literal["http", "socks", "auto"]
    country: str
    date: str
    date_end: str
    unixtime: int
    unixtime_end: int
    descr: str
    active: str  # "1" or "0"

    class Config:
        populate_by_name = True

class GetPriceResponse(SuccessEnvelope):
    price: Optional[str] = None
    price_single: Optional[str] = None
    period: Optional[int] = None
    count: Optional[int] = None

class GetCountResponse(SuccessEnvelope):
    count: str

class GetCountryResponse(SuccessEnvelope):
    list: list[str]

class GetProxyResponse(SuccessEnvelope):
    list_count: int
    list: dict[str, Proxy]

class BuyResponse(SuccessEnvelope):
    order_id: str
    count: int
    price: str
    price_single: str
    period: int
    country: str
    list: dict[str, Proxy]

class ProlongResponse(SuccessEnvelope):
    order_id: str
    price: str
    price_single: Optional[str] = None  # ABSENT on mixed-version batches
    period: int
    count: int
    list: dict[str, dict]  # {id: {date_end, unixtime_end}}

class SetDescrResponse(SuccessEnvelope):
    count: int

class DeleteResponse(SuccessEnvelope):
    count: int

class CheckResponse(SuccessEnvelope):
    proxy_id: str
    proxy_status: bool
```

## Exceptions

```python
# exceptions.py

class Proxy6Error(Exception):
    """Base."""

class Proxy6RetryableError(Proxy6Error):
    """Network / 5xx / 429 / error_id 30."""

class Proxy6FatalError(Proxy6Error):
    def __init__(self, error_id: int, message: str) -> None:
        super().__init__(f"error_id={error_id}: {message}")
        self.error_id = error_id

class AuthError(Proxy6FatalError):       """100, 105"""
class BadRequest(Proxy6FatalError):      """110, 200, 210, 220, 230, 240, 250, 260, 270, 280"""
class OutOfStock(Proxy6FatalError):      """300"""
class InsufficientFunds(Proxy6FatalError): """400"""
class NotFound(Proxy6FatalError):        """404"""
class InvalidPrice(Proxy6FatalError):    """410"""

_FATAL_MAP = {
    100: AuthError, 105: AuthError,
    110: BadRequest, 200: BadRequest, 210: BadRequest, 220: BadRequest,
    230: BadRequest, 240: BadRequest, 250: BadRequest, 260: BadRequest,
    270: BadRequest, 280: BadRequest,
    300: OutOfStock,
    400: InsufficientFunds,
    404: NotFound,
    410: InvalidPrice,
}

def raise_for_error(error_id: int, message: str) -> None:
    if error_id == 30:
        raise Proxy6RetryableError(f"unknown server error: {message}")
    cls = _FATAL_MAP.get(error_id, Proxy6FatalError)
    raise cls(error_id, message)
```

## Token bucket limiter

See [rate-limit-and-retry.md](rate-limit-and-retry.md) for the full `TokenBucket` class. Instantiate once per `Proxy6Client`.

## Client

```python
# client.py
import os
import httpx
from tenacity import (
    retry, retry_if_exception_type, stop_after_attempt, wait_random_exponential
)
from .models import (
    ErrorEnvelope, GetPriceResponse, GetCountResponse, GetCountryResponse,
    GetProxyResponse, BuyResponse, ProlongResponse, SetDescrResponse,
    DeleteResponse, CheckResponse,
)
from .exceptions import Proxy6RetryableError, raise_for_error
from .limiter import TokenBucket


class Proxy6Client:
    BASE = "https://px6.link/api"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        timeout: float = 10.0,
        rate: float = 2.0,
    ) -> None:
        self.api_key = api_key or os.environ["PROXY6_API_KEY"]
        self.http = httpx.AsyncClient(timeout=timeout)
        self.bucket = TokenBucket(rate=rate, capacity=3)

    async def close(self) -> None:
        await self.http.aclose()

    @retry(
        retry=retry_if_exception_type(Proxy6RetryableError),
        wait=wait_random_exponential(multiplier=0.5, max=30),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    async def _call(self, method: str, **params) -> dict:
        await self.bucket.acquire()
        # api_key in path; params via query string
        url = f"{self.BASE}/{self.api_key}/{method}/"
        resp = await self.http.get(url, params=params)
        if resp.status_code == 429:
            raise Proxy6RetryableError("HTTP 429")
        if resp.status_code >= 500:
            raise Proxy6RetryableError(f"HTTP {resp.status_code}")
        data = resp.json()
        if data.get("status") == "no":
            err = ErrorEnvelope.model_validate(data)
            raise_for_error(err.error_id, err.error)  # may raise Retryable or Fatal
        return data

    # --- methods ---

    async def getprice(self, count: int, period: int, version: str) -> GetPriceResponse:
        data = await self._call("getprice", count=count, period=period, version=version)
        return GetPriceResponse.model_validate(data)

    async def getcount(self, country: str, version: str) -> GetCountResponse:
        data = await self._call("getcount", country=country, version=version)
        return GetCountResponse.model_validate(data)

    async def getcountry(self, version: str) -> GetCountryResponse:
        data = await self._call("getcountry", version=version)
        return GetCountryResponse.model_validate(data)

    async def getproxy(
        self,
        *,
        state: str = "all",
        descr: str | None = None,
        page: int = 1,
        limit: int = 1000,
    ) -> GetProxyResponse:
        params = {"state": state, "page": page, "limit": limit}
        if descr:
            params["descr"] = descr
        data = await self._call("getproxy", **params)
        return GetProxyResponse.model_validate(data)

    async def buy(
        self,
        *,
        count: int,
        period: int,
        country: str,
        version: str,
        descr: str,                  # REQUIRED by our convention (proxy6 allows skip)
        auto_prolong: bool = False,  # default OFF
        type: str | None = None,
    ) -> BuyResponse:
        if not descr:
            raise ValueError("descr is required by convention (ops attribution)")
        params = {
            "count": count, "period": period, "country": country,
            "version": version, "descr": descr,
        }
        if auto_prolong:
            params["auto_prolong"] = ""  # presence-only flag
        if type:
            params["type"] = type
        data = await self._call("buy", **params)
        return BuyResponse.model_validate(data)

    async def prolong(self, *, period: int, ids: list[str]) -> ProlongResponse:
        data = await self._call("prolong", period=period, ids=",".join(ids))
        return ProlongResponse.model_validate(data)

    async def setdescr(
        self,
        *,
        new: str,
        old: str | None = None,
        ids: list[str] | None = None,
    ) -> SetDescrResponse:
        if not (old or ids):
            raise ValueError("setdescr requires either old or ids")
        if len(new) > 50:
            raise ValueError("descr max 50 chars")
        params: dict = {"new": new}
        if old:
            params["old"] = old
        if ids:
            params["ids"] = ",".join(ids)
        data = await self._call("setdescr", **params)
        return SetDescrResponse.model_validate(data)

    async def delete(
        self,
        *,
        ids: list[str] | None = None,
        descr: str | None = None,
        confirm_dry_run: bool = True,
    ) -> DeleteResponse:
        if not (ids or descr):
            raise ValueError("delete requires either ids or descr")
        if descr and not ids and confirm_dry_run:
            # Dry-run pattern: callers must explicitly opt out for descr-only delete
            raise RuntimeError(
                "Refusing to delete by descr without ids. "
                "Call getproxy(descr=...) first, then pass ids=...; "
                "or set confirm_dry_run=False to override."
            )
        params: dict = {}
        if ids:
            params["ids"] = ",".join(ids)
        elif descr:
            params["descr"] = descr
        data = await self._call("delete", **params)
        return DeleteResponse.model_validate(data)

    async def check(self, *, proxy_id: str | None = None, proxy: str | None = None) -> CheckResponse:
        if not (proxy_id or proxy):
            raise ValueError("check requires proxy_id or proxy")
        params = {"ids": proxy_id} if proxy_id else {"proxy": proxy}
        data = await self._call("check", **params)
        return CheckResponse.model_validate(data)

    async def ipauth(self, ip: list[str] | str) -> dict:
        """Pass full union; or the literal string 'delete' to clear all."""
        if isinstance(ip, list):
            ip_str = ",".join(ip)
        else:
            ip_str = ip
        return await self._call("ipauth", ip=ip_str)
```

## Usage

```python
import asyncio
from proxy6_client.client import Proxy6Client

async def main() -> None:
    client = Proxy6Client()  # reads PROXY6_API_KEY
    try:
        # Pre-buy safety: price + stock + balance
        price = await client.getprice(count=10, period=30, version="4")
        stock = await client.getcount(country="ru", version="4")
        if int(stock.count) < 10:
            raise SystemExit("not enough stock")
        if float(client._last_balance or "0") < float(price.price) * 1.1:
            raise SystemExit("balance too low")
        order = await client.buy(
            count=10, period=30, country="ru", version="4",
            descr="prod:scraper-A:reviews",
        )
        print(f"Bought {order.count}, order_id={order.order_id}")
    finally:
        await client.close()

asyncio.run(main())
```

Track `_last_balance` from each response envelope; or call `getprice()` with no args as the cheapest balance probe.

## Testing with respx

```python
# tests/test_client.py
import pytest, respx, httpx
from proxy6_client.client import Proxy6Client
from proxy6_client.exceptions import InsufficientFunds

@pytest.mark.asyncio
@respx.mock
async def test_buy_no_money() -> None:
    respx.get("https://px6.link/api/k/buy/").respond(
        200, json={"status": "no", "error_id": 400, "error": "Error no money"}
    )
    client = Proxy6Client(api_key="k")
    with pytest.raises(InsufficientFunds):
        await client.buy(count=1, period=1, country="ru", version="4", descr="t")
```

## Secrets

Load `PROXY6_API_KEY` from environment. NEVER fall back to a hardcoded default. NEVER log the constructed URL — log `method` + masked params only.
