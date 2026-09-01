# Integration — Python + Node.js clients, DB schema

## Python — google-api-python-client + service account

```bash
uv add google-api-python-client google-auth google-auth-httplib2
```

```python
# gsc_client.py
from __future__ import annotations
import json, time, random
from pathlib import Path
from typing import Iterator
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES_READONLY = ["https://www.googleapis.com/auth/webmasters.readonly"]
SCOPES_FULL     = ["https://www.googleapis.com/auth/webmasters"]

def build_service(sa_path: str | Path, *, full: bool = False):
    scopes = SCOPES_FULL if full else SCOPES_READONLY
    creds = service_account.Credentials.from_service_account_file(sa_path, scopes=scopes)
    # "searchconsole" v1 — single service for both Webmasters v3 and URL Inspection
    return build("searchconsole", "v1", credentials=creds, cache_discovery=False)


def _reason(e: HttpError) -> str | None:
    try:
        body = json.loads(e.content.decode())
        return body.get("error", {}).get("errors", [{}])[0].get("reason")
    except Exception:
        return None


def with_retry(fn, *, max_attempts: int = 5):
    for attempt in range(max_attempts):
        try:
            return fn()
        except HttpError as e:
            status = e.resp.status
            reason = _reason(e)
            if status == 429 and reason == "dailyLimitExceeded":
                raise
            if status in (429, 500, 503):
                sleep = min(60, (2 ** attempt) + random.uniform(0, 1))
                time.sleep(sleep)
                continue
            raise
    raise RuntimeError("retries exhausted")
```

### Search Analytics — pagination helper (25k cap)

```python
def query_all_rows(svc, site_url: str, body: dict, *, page_size: int = 25_000) -> Iterator[dict]:
    """Yields all rows across paginated 25k-cap responses."""
    start = 0
    while True:
        body = {**body, "rowLimit": page_size, "startRow": start}
        resp = with_retry(lambda: svc.searchanalytics().query(siteUrl=site_url, body=body).execute())
        rows = resp.get("rows", [])
        for r in rows:
            yield r
        if len(rows) < page_size:
            return
        start += page_size
```

Usage:

```python
svc = build_service("sa.json")
body = {
    "startDate": "2026-04-15", "endDate": "2026-05-12",
    "dimensions": ["query", "page"],
    "type": "web",
    "dataState": "final",
}
for row in query_all_rows(svc, "sc-domain:example.com", body):
    q, page = row["keys"]
    print(q, page, row["clicks"], row["impressions"], row["position"])
```

### URL Inspection batch worker with per-property daily quota

```python
import asyncio
from datetime import datetime, timezone, timedelta

PT = timezone(timedelta(hours=-7))  # PDT; -8 in winter (PST); simplified

class InspectionWorker:
    def __init__(self, svc, redis):
        self.svc = svc
        self.redis = redis

    async def _daily_ok(self, prop: str) -> bool:
        today = datetime.now(PT).strftime("%Y%m%d")
        key = f"gsc:inspect:{prop}:{today}"
        n = await self.redis.incr(key)
        if n == 1:
            midnight = datetime.now(PT).replace(hour=23, minute=59, second=59)
            await self.redis.expireat(key, int(midnight.timestamp()))
        return n <= 2000

    async def inspect(self, prop: str, url: str, *, language: str = "en-US"):
        if not await self._daily_ok(prop):
            raise RuntimeError(f"daily quota for {prop} exhausted")
        body = {"inspectionUrl": url, "siteUrl": prop, "languageCode": language}
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: with_retry(lambda: self.svc.urlInspection().index().inspect(body=body).execute())
        )
```

### Alternative — httpx + JWT directly (thin control)

When you do not want to pull in google-api-python-client (e.g. serverless):

```python
import time, jwt, httpx, json

def jwt_access_token(sa: dict, scope: str) -> str:
    now = int(time.time())
    claim = {
        "iss": sa["client_email"],
        "scope": scope,
        "aud": "https://oauth2.googleapis.com/token",
        "exp": now + 3600,
        "iat": now,
    }
    assertion = jwt.encode(claim, sa["private_key"], algorithm="RS256")
    r = httpx.post("https://oauth2.googleapis.com/token", data={
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": assertion,
    }, timeout=10)
    r.raise_for_status()
    return r.json()["access_token"]

sa = json.loads(open("sa.json").read())
tok = jwt_access_token(sa, "https://www.googleapis.com/auth/webmasters.readonly")

with httpx.Client(http2=True, timeout=30, headers={"Authorization": f"Bearer {tok}"}) as c:
    r = c.post(
        "https://www.googleapis.com/webmasters/v3/sites/sc-domain%3Aexample.com/searchAnalytics/query",
        json={"startDate": "2026-05-01", "endDate": "2026-05-12", "dimensions": ["query"], "rowLimit": 100},
    )
    r.raise_for_status()
    print(r.json())
```

## Node.js — googleapis

```bash
npm i googleapis
```

```ts
// gsc-client.ts
import { google } from "googleapis";
import type { searchconsole_v1 } from "googleapis";

export function buildClient(saPath: string, full = false): searchconsole_v1.Searchconsole {
  const scopes = full
    ? ["https://www.googleapis.com/auth/webmasters"]
    : ["https://www.googleapis.com/auth/webmasters.readonly"];
  const auth = new google.auth.GoogleAuth({ keyFile: saPath, scopes });
  return google.searchconsole({ version: "v1", auth });
}

const PAGE_SIZE = 25_000;

export async function* queryAllRows(
  sc: searchconsole_v1.Searchconsole,
  siteUrl: string,
  body: searchconsole_v1.Schema$SearchAnalyticsQueryRequest,
): AsyncGenerator<searchconsole_v1.Schema$ApiDataRow> {
  let startRow = 0;
  while (true) {
    const { data } = await withRetry(() =>
      sc.searchanalytics.query({
        siteUrl,
        requestBody: { ...body, rowLimit: PAGE_SIZE, startRow },
      }),
    );
    const rows = data.rows ?? [];
    for (const r of rows) yield r;
    if (rows.length < PAGE_SIZE) return;
    startRow += PAGE_SIZE;
  }
}

async function withRetry<T>(fn: () => Promise<T>, max = 5): Promise<T> {
  for (let attempt = 0; attempt < max; attempt++) {
    try {
      return await fn();
    } catch (e: any) {
      const status = e?.code ?? e?.response?.status;
      const reason = e?.errors?.[0]?.reason;
      if (status === 429 && reason === "dailyLimitExceeded") throw e;
      if ([429, 500, 503].includes(status)) {
        const delay = Math.min(60_000, 2 ** attempt * 1000 + Math.random() * 1000);
        await new Promise((r) => setTimeout(r, delay));
        continue;
      }
      throw e;
    }
  }
  throw new Error("retries exhausted");
}
```

Usage:

```ts
const sc = buildClient("./sa.json");

for await (const row of queryAllRows(sc, "sc-domain:example.com", {
  startDate: "2026-04-15",
  endDate: "2026-05-12",
  dimensions: ["query", "page"],
  type: "web",
  dataState: "final",
})) {
  const [q, page] = row.keys!;
  console.log(q, page, row.clicks, row.impressions, row.position);
}
```

## Service account access — IMPORTANT

A service account **cannot self-grant** access in Search Console. A human user must:

1. Open Search Console → choose the property → Settings → Users and permissions.
2. Click "Add user".
3. Email: `xxx@<project>.iam.gserviceaccount.com` (the `client_email` field of the JSON key).
4. Role: **Restricted** for read-only (Search Analytics, URL Inspection, Sitemaps list) or **Full** for sitemap submit / sites add.
5. For the **Indexing API** — **Owner** is required, not Full.

Verification:

```python
svc = build_service("sa.json")
for s in svc.sites().list().execute().get("siteEntry", []):
    print(s["siteUrl"], s["permissionLevel"])
# Expect properties with permissionLevel siteRestrictedUser / siteFullUser / siteOwner
# Not siteUnverifiedUser
```

## PostgreSQL schema — daily snapshot

```sql
CREATE TABLE gsc_search_analytics (
  id              bigserial PRIMARY KEY,
  site_url        text        NOT NULL,
  date            date        NOT NULL,
  query           text        NOT NULL DEFAULT '',
  page            text        NOT NULL DEFAULT '',
  country         text        NOT NULL DEFAULT '',
  device          text        NOT NULL DEFAULT '',
  search_appearance text      NOT NULL DEFAULT '',
  clicks          double precision NOT NULL,
  impressions     double precision NOT NULL,
  ctr             double precision NOT NULL,
  position        double precision NOT NULL,
  data_state      text        NOT NULL DEFAULT 'final',
  fetched_at      timestamptz NOT NULL DEFAULT now()
);

-- Uniqueness for UPSERT — all dimensions + date + site
CREATE UNIQUE INDEX gsc_sa_unique
  ON gsc_search_analytics (site_url, date, query, page, country, device, search_appearance);

CREATE INDEX gsc_sa_query_trgm  ON gsc_search_analytics USING gin (query gin_trgm_ops);
CREATE INDEX gsc_sa_date        ON gsc_search_analytics (date DESC);
CREATE INDEX gsc_sa_site_date   ON gsc_search_analytics (site_url, date DESC);

-- URL Inspection cache
CREATE TABLE gsc_url_inspection (
  site_url        text        NOT NULL,
  inspection_url  text        NOT NULL,
  verdict         text,
  coverage_state  text,
  indexing_state  text,
  page_fetch_state text,
  last_crawl_time timestamptz,
  google_canonical text,
  user_canonical  text,
  result          jsonb       NOT NULL,
  inspected_at    timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (site_url, inspection_url)
);

CREATE INDEX gsc_ui_verdict       ON gsc_url_inspection (verdict);
CREATE INDEX gsc_ui_coverage      ON gsc_url_inspection (coverage_state);
CREATE INDEX gsc_ui_inspected_at  ON gsc_url_inspection (inspected_at DESC);
```

Upsert pattern (Python):

```python
async def upsert_row(conn, site_url, date, dims, metrics):
    await conn.execute("""
        INSERT INTO gsc_search_analytics
          (site_url, date, query, page, country, device, search_appearance,
           clicks, impressions, ctr, position)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
        ON CONFLICT (site_url, date, query, page, country, device, search_appearance)
        DO UPDATE SET
          clicks      = EXCLUDED.clicks,
          impressions = EXCLUDED.impressions,
          ctr         = EXCLUDED.ctr,
          position    = EXCLUDED.position,
          fetched_at  = now()
    """, site_url, date, *dims, *metrics)
```

## End-to-end recipe

1. Daily cron 06:00 UTC (after the 2-3 day lag) → fetch `searchanalytics.query` for `[today-3, today-3]` with `dimensions=[query,page,country,device]`, `dataState=final`, paginated by 25k.
2. Upsert into `gsc_search_analytics` keyed by date + dims.
3. Diff against the previous day → mark new/changed URLs → enqueue into the `urlInspection` worker.
4. Inspection worker with per-property daily counter in Redis, sleeping `86400 / 2000 ≈ 43s` between requests; persist results into `gsc_url_inspection`.
5. Sitemap monitoring — `sitemaps.list` once a day → alert when `errors > 0` or sitemap not downloaded for > 7 days.
