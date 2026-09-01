# Integration — Python + Node.js clients, polling worker, schema

Production-grade integration patterns for Yandex Direct API v5.

## Python — async client (httpx)

```python
# direct_client.py
from __future__ import annotations

import asyncio
import logging
import os
import random
from dataclasses import dataclass
from typing import Any

import httpx


log = logging.getLogger("yandex_direct")


@dataclass
class UnitsHeader:
    consumed: int
    remaining: int
    daily_limit: int
    used_login: str | None


@dataclass
class DirectConfig:
    base_url: str
    oauth_token: str
    client_login: str | None = None
    use_operator_units: bool = False
    accept_language: str = "ru"
    timeout_sec: float = 120.0


class DirectError(Exception):
    def __init__(self, code: int, message: str, detail: str, request_id: str):
        super().__init__(f"[{code}] {message}: {detail} (rid={request_id})")
        self.code = code
        self.request_id = request_id


class DirectClient:
    def __init__(self, cfg: DirectConfig):
        self.cfg = cfg
        self._client = httpx.AsyncClient(
            base_url=cfg.base_url,
            timeout=httpx.Timeout(cfg.timeout_sec),
            headers={
                "Accept-Encoding": "gzip",
            },
            http2=False,  # Direct doesn't gain from h2; keep stable
        )

    async def close(self) -> None:
        await self._client.aclose()

    def _headers(self) -> dict[str, str]:
        h = {
            "Authorization": f"Bearer {self.cfg.oauth_token}",
            "Content-Type": "application/json; charset=utf-8",
            "Accept-Language": self.cfg.accept_language,
        }
        if self.cfg.client_login:
            h["Client-Login"] = self.cfg.client_login
        if self.cfg.use_operator_units:
            h["Use-Operator-Units"] = "true"
        return h

    @staticmethod
    def _parse_units(headers: httpx.Headers) -> UnitsHeader | None:
        raw = headers.get("Units")
        if not raw:
            return None
        try:
            c, r, d = (int(x) for x in raw.split("/"))
        except ValueError:
            return None
        return UnitsHeader(
            consumed=c,
            remaining=r,
            daily_limit=d,
            used_login=headers.get("Units-Used-Login"),
        )

    async def call(
        self,
        service: str,
        method: str,
        params: dict[str, Any],
        *,
        retries: int = 3,
    ) -> dict[str, Any]:
        body = {"method": method, "params": params}
        path = f"/json/v5/{service}"
        attempt = 0
        while True:
            attempt += 1
            try:
                r = await self._client.post(path, json=body, headers=self._headers())
            except (httpx.TimeoutException, httpx.NetworkError) as e:
                if attempt > retries:
                    raise
                await asyncio.sleep(self._backoff(attempt))
                continue

            units = self._parse_units(r.headers)
            request_id = r.headers.get("RequestId", "?")

            if units:
                log.info(
                    "direct.call",
                    extra={
                        "service": service,
                        "method": method,
                        "units_consumed": units.consumed,
                        "units_remaining": units.remaining,
                        "units_used_login": units.used_login,
                        "request_id": request_id,
                    },
                )

            data = r.json()
            if "error" in data:
                err = data["error"]
                code = int(err.get("error_code", 0))
                if code in (1, 12) and attempt <= retries:
                    await asyncio.sleep(self._backoff(attempt))
                    continue
                raise DirectError(
                    code=code,
                    message=err.get("error_string", ""),
                    detail=err.get("error_detail", ""),
                    request_id=err.get("request_id", request_id),
                )
            return data["result"]

    @staticmethod
    def _backoff(attempt: int) -> float:
        base = min(2 ** attempt, 32)
        return base + random.uniform(0, base * 0.2)


# usage
async def main() -> None:
    cfg = DirectConfig(
        base_url=os.environ["YANDEX_DIRECT_BASE_URL"],
        oauth_token=os.environ["YANDEX_DIRECT_OAUTH_TOKEN"],
        client_login=os.environ.get("YANDEX_DIRECT_CLIENT_LOGIN") or None,
    )
    async with DirectClient(cfg) as client:
        res = await client.call(
            "campaigns",
            "get",
            {
                "SelectionCriteria": {},
                "FieldNames": ["Id", "Name", "State", "Status", "Type"],
                "Page": {"Limit": 100},
            },
        )
        for c in res.get("Campaigns", []):
            print(c)


if __name__ == "__main__":
    asyncio.run(main())
```

### Async context manager

```python
class DirectClient:
    async def __aenter__(self) -> "DirectClient":
        return self
    async def __aexit__(self, *exc: Any) -> None:
        await self.close()
```

## Stats TSV worker (Python)

```python
# stats_worker.py
import asyncio
import csv
import io
import logging
from dataclasses import dataclass
from typing import Any

import httpx

log = logging.getLogger("direct_stats")


@dataclass
class StatsJob:
    client: str
    report_name: str
    payload: dict[str, Any]


class StatsWorker:
    """
    Submits a stats TSV job, polls until ready, returns parsed rows.
    Honors Retry-After. Body must stay identical across polls.
    """

    def __init__(self, cfg: DirectConfig):
        self.cfg = cfg
        self._client = httpx.AsyncClient(
            base_url=cfg.base_url,
            timeout=httpx.Timeout(300.0),
            headers={"Accept-Encoding": "gzip"},
        )

    async def close(self) -> None:
        await self._client.aclose()

    def _headers(self) -> dict[str, str]:
        h = {
            "Authorization": f"Bearer {self.cfg.oauth_token}",
            "Content-Type": "application/json; charset=utf-8",
            "Accept-Language": self.cfg.accept_language,
            "processingMode": "offline",
            "returnMoneyInMicros": "false",
            "skipReportHeader": "true",
            "skipColumnHeader": "true",
            "skipReportSummary": "true",
        }
        if self.cfg.client_login:
            h["Client-Login"] = self.cfg.client_login
        return h

    async def run(self, job: StatsJob, max_polls: int = 60) -> list[dict[str, str]]:
        body = {"params": job.payload}
        for poll in range(max_polls):
            r = await self._client.post("/json/v5/reports", json=body, headers=self._headers())
            if r.status_code == 200:
                return self._parse_tsv(r.text, job.payload["FieldNames"])
            if r.status_code in (201, 202):
                retry = int(r.headers.get("Retry-After", "60"))
                log.info(
                    "direct.stats.poll",
                    extra={
                        "report_name": job.report_name,
                        "http": r.status_code,
                        "retry_after": retry,
                        "poll": poll,
                    },
                )
                await asyncio.sleep(retry + retry * 0.1)
                continue
            if r.status_code == 400:
                raise RuntimeError(f"stats bad request: {r.text[:500]}")
            if r.status_code >= 500:
                await asyncio.sleep(min(2 ** poll, 60))
                continue
            r.raise_for_status()
        raise TimeoutError(f"stats job {job.report_name} not ready after {max_polls} polls")

    @staticmethod
    def _parse_tsv(text: str, field_names: list[str]) -> list[dict[str, str]]:
        # With skip* headers on, body is data-only.
        rows: list[dict[str, str]] = []
        reader = csv.reader(io.StringIO(text), delimiter="\t")
        for raw in reader:
            if not raw:
                continue
            rows.append({k: v for k, v in zip(field_names, raw, strict=False)})
        return rows
```

## Node.js (TypeScript) — mirror

```typescript
// direct-client.ts
import { setTimeout as sleep } from "node:timers/promises";

export interface UnitsHeader {
  consumed: number;
  remaining: number;
  dailyLimit: number;
  usedLogin: string | null;
}

export interface DirectConfig {
  baseUrl: string;
  oauthToken: string;
  clientLogin?: string;
  useOperatorUnits?: boolean;
  acceptLanguage?: "ru" | "en";
  timeoutMs?: number;
}

export class DirectError extends Error {
  constructor(
    public code: number,
    message: string,
    public detail: string,
    public requestId: string,
  ) {
    super(`[${code}] ${message}: ${detail} (rid=${requestId})`);
  }
}

export class DirectClient {
  constructor(private cfg: DirectConfig) {}

  private headers(): HeadersInit {
    const h: Record<string, string> = {
      Authorization: `Bearer ${this.cfg.oauthToken}`,
      "Content-Type": "application/json; charset=utf-8",
      "Accept-Language": this.cfg.acceptLanguage ?? "ru",
      "Accept-Encoding": "gzip",
    };
    if (this.cfg.clientLogin) h["Client-Login"] = this.cfg.clientLogin;
    if (this.cfg.useOperatorUnits) h["Use-Operator-Units"] = "true";
    return h;
  }

  private parseUnits(headers: Headers): UnitsHeader | null {
    const raw = headers.get("Units");
    if (!raw) return null;
    const [c, r, d] = raw.split("/").map(Number);
    if ([c, r, d].some(Number.isNaN)) return null;
    return {
      consumed: c,
      remaining: r,
      dailyLimit: d,
      usedLogin: headers.get("Units-Used-Login"),
    };
  }

  async call<T>(
    service: string,
    method: string,
    params: Record<string, unknown>,
    retries = 3,
  ): Promise<T> {
    const url = `${this.cfg.baseUrl}/json/v5/${service}`;
    const body = JSON.stringify({ method, params });

    for (let attempt = 1; attempt <= retries + 1; attempt++) {
      const ctrl = new AbortController();
      const t = setTimeout(() => ctrl.abort(), this.cfg.timeoutMs ?? 120000);
      let res: Response;
      try {
        res = await fetch(url, {
          method: "POST",
          headers: this.headers(),
          body,
          signal: ctrl.signal,
        });
      } catch (e) {
        clearTimeout(t);
        if (attempt > retries) throw e;
        await sleep(this.backoff(attempt));
        continue;
      }
      clearTimeout(t);

      const units = this.parseUnits(res.headers);
      const requestId = res.headers.get("RequestId") ?? "?";
      const data = (await res.json()) as {
        error?: {
          error_code: number;
          error_string: string;
          error_detail: string;
          request_id: string;
        };
        result?: T;
      };

      if (units) {
        console.log(
          JSON.stringify({
            evt: "direct.call",
            service,
            method,
            units,
            requestId,
          }),
        );
      }

      if (data.error) {
        const code = data.error.error_code;
        if ((code === 1 || code === 12) && attempt <= retries) {
          await sleep(this.backoff(attempt));
          continue;
        }
        throw new DirectError(
          code,
          data.error.error_string,
          data.error.error_detail,
          data.error.request_id,
        );
      }
      return data.result as T;
    }
    throw new Error("unreachable");
  }

  private backoff(attempt: number): number {
    const base = Math.min(2 ** attempt, 32);
    return (base + Math.random() * base * 0.2) * 1000;
  }
}
```

## TypeScript types for major shapes

```typescript
export type CampaignState = "ON" | "OFF" | "SUSPENDED" | "ENDED" | "CONVERTED" | "ARCHIVED";
export type CampaignStatus = "DRAFT" | "MODERATION" | "ACCEPTED" | "REJECTED";
export type StatusPayment = "ALLOWED" | "DISALLOWED";

export type CampaignType =
  | "TEXT_CAMPAIGN"
  | "UNIFIED_CAMPAIGN"
  | "MOBILE_APP_CAMPAIGN"
  | "DYNAMIC_TEXT_CAMPAIGN"
  | "CPM_BANNER_CAMPAIGN"
  | "SMART_CAMPAIGN"
  | "CPM_VIDEO_CAMPAIGN";

export interface CampaignBase {
  Id: number;
  Name: string;
  Type: CampaignType;
  Status: CampaignStatus;
  State: CampaignState;
  StatusPayment: StatusPayment;
  StartDate: string;
  EndDate?: string;
  DailyBudget?: { Amount: number; Mode: "STANDARD" | "DISTRIBUTED" };
  Funds?: { Mode: "SHARED_ACCOUNT_FUNDS" | "CAMPAIGN_FUNDS" };
}

export interface DirectErrorItem { Code: number; Message: string; Details: string }
export interface DirectActionResult { Id?: number; Errors?: DirectErrorItem[]; Warnings?: DirectErrorItem[] }
export interface AddCampaignsResult { AddResults: DirectActionResult[] }
export interface GetCampaignsResult { Campaigns: CampaignBase[]; LimitedBy?: number }

export interface UnitsBody {
  consumed: number;
  remaining: number;
  dailyLimit: number;
  usedLogin: string | null;
}
```

## PostgreSQL schema for caching + idempotency

```sql
-- Account cache (latest snapshot)
CREATE TABLE direct_campaigns_cache (
  id              BIGINT PRIMARY KEY,
  client_login    TEXT NOT NULL,
  name            TEXT NOT NULL,
  type            TEXT NOT NULL,
  status          TEXT NOT NULL,
  state           TEXT NOT NULL,
  status_payment  TEXT,
  start_date      DATE,
  end_date        DATE,
  daily_budget_micro BIGINT,
  raw             JSONB NOT NULL,
  fetched_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_dcc_client ON direct_campaigns_cache (client_login);

-- Idempotency for add operations
CREATE TABLE direct_idempotency (
  business_key    TEXT PRIMARY KEY,        -- e.g. "campaign:<client>:<name>"
  direct_id       BIGINT NOT NULL,         -- returned Id
  service         TEXT NOT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Audit log of write operations
CREATE TABLE direct_audit (
  id              BIGSERIAL PRIMARY KEY,
  client_login    TEXT NOT NULL,
  operator        TEXT NOT NULL,           -- user/system who issued
  service         TEXT NOT NULL,
  method          TEXT NOT NULL,
  request_id      TEXT,
  body            JSONB NOT NULL,
  response        JSONB,
  units_consumed  INT,
  units_used_login TEXT,
  http_status     INT,
  error_code      INT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_dat_client ON direct_audit (client_login, created_at);

-- Stats jobs (TSV polling)
CREATE TABLE direct_stats_jobs (
  id              BIGSERIAL PRIMARY KEY,
  client_login    TEXT NOT NULL,
  report_name     TEXT NOT NULL,
  payload         JSONB NOT NULL,
  status          TEXT NOT NULL DEFAULT 'queued',   -- queued | processing | done | failed
  http_code       INT,
  retry_after     INT,
  last_poll       TIMESTAMPTZ,
  result_path     TEXT,
  request_id      TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (client_login, report_name)
);
```

## Money-side double-spend trap

When write call fails on network/timeout, do **not** blindly resend `add`/`update`. The first request may have reached Direct already and changed state — a blind retry will:

- Create a duplicate campaign (`add` retry).
- Apply the bid increase twice (`Bids.set` retry over already-set bid).
- Re-submit moderation that already succeeded.

**Resolution before retry**:

1. Read business key from `direct_idempotency`. If `direct_id` is present, the previous call succeeded — skip.
2. Otherwise call `get` filtered by the business key. If the object exists in Direct, store the `Id` and skip the retry.
3. Only if no record on either side -> safe to retry `add`.

For `update`/`set` with idempotent semantics (setting state, not deltas) the retry is safe **if** the payload is absolute (e.g. `SearchBid: 5_000_000` not "+10%"). Always work in absolute values.

## Auth refresh

OAuth tokens expire (up to 1 year). On `error_code in {506, 1002, 1003}`:

- Stop all in-flight workers (sentinel flag).
- Run refresh flow on `https://oauth.yandex.ru/token` with `grant_type=refresh_token`.
- Persist new `access_token` and `refresh_token`.
- Resume workers.

Do not retry the failed request automatically — re-validate inputs and re-issue from app logic, since the token might have been revoked due to permission removal (not just expiry).

## Local CLI for sandbox smoke

```bash
# .env.sandbox
YANDEX_DIRECT_BASE_URL=https://api-sandbox.direct.yandex.com
YANDEX_DIRECT_OAUTH_TOKEN=y0_AgAAAA...
YANDEX_DIRECT_CLIENT_LOGIN=

python -m direct_client  # uses base_url + token from env
```

Smoke-test sequence: `Clients.get` -> `Campaigns.get` -> `Campaigns.add` (test campaign) -> `Ads.add` (1 ad) -> `Ads.moderate` -> wait -> `Ads.get` (verify ACCEPTED) -> `Reports/v5/reports` (TSV with one campaign).

## Observability minimum

- Structured logs per call: `service`, `method`, `units_consumed`, `units_remaining`, `units_used_login`, `request_id`, `http`, `error_code`.
- Daily roll-up: total units by client, top methods by cost.
- Alerts: `units_remaining < 20%`, `error 153`, `error 506/1002`, polling stuck >3 cycles.
- Trace context propagation: include trace id in `User-Agent` to map to internal trace.
