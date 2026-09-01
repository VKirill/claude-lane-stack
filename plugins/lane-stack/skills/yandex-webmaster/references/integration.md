# Yandex.Webmaster — Production clients (Python + Node.js)

Production-ready async clients with OAuth refresh, retry, persistence, batch recrawl.

## Python — httpx async

```python
"""
yandex_webmaster.py — production-grade async client.
deps: httpx>=0.27, asyncpg, pydantic
"""
from __future__ import annotations
import asyncio
import random
import time
from dataclasses import dataclass, field
from typing import Any

import httpx


API_BASE = "https://api.webmaster.yandex.net/v4"
OAUTH_TOKEN_URL = "https://oauth.yandex.com/token"

RETRYABLE_HTTP = {429, 500, 502, 503, 504}
IDEMPOTENT_CONFLICT_CODES = {
    "URL_ALREADY_ADDED",
    "HOST_ALREADY_ADDED",
    "SITEMAP_ALREADY_ADDED",
    "VERIFICATION_ALREADY_IN_PROGRESS",
}


@dataclass
class OAuthCreds:
    client_id: str
    client_secret: str
    access_token: str
    refresh_token: str
    expires_at: int  # unix ts
    user_id: int | None = None


class WebmasterError(Exception):
    def __init__(self, status: int, code: str | None, message: str):
        self.status = status
        self.code = code
        self.message = message
        super().__init__(f"{status} {code}: {message}")


class WebmasterClient:
    def __init__(self, creds: OAuthCreds, on_refresh=None):
        """on_refresh: async callable(creds: OAuthCreds) — persist updated tokens."""
        self.creds = creds
        self.on_refresh = on_refresh
        self.http = httpx.AsyncClient(
            base_url=API_BASE,
            timeout=httpx.Timeout(30.0, connect=10.0),
            http2=True,
        )
        self._refresh_lock = asyncio.Lock()

    async def close(self):
        await self.http.aclose()

    # ---------- OAuth ----------

    async def _refresh_token(self) -> None:
        async with self._refresh_lock:
            # Double-check: another coroutine may have already refreshed
            if self.creds.expires_at > int(time.time()) + 60:
                return
            async with httpx.AsyncClient(timeout=10.0) as h:
                r = await h.post(
                    OAUTH_TOKEN_URL,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": self.creds.refresh_token,
                        "client_id": self.creds.client_id,
                        "client_secret": self.creds.client_secret,
                    },
                )
                r.raise_for_status()
                payload = r.json()
            self.creds.access_token = payload["access_token"]
            self.creds.refresh_token = payload.get("refresh_token", self.creds.refresh_token)
            self.creds.expires_at = int(time.time()) + int(payload["expires_in"])
            if self.on_refresh:
                await self.on_refresh(self.creds)

    # ---------- low-level request ----------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: dict | None = None,
        attempts: int = 5,
    ) -> dict[str, Any]:
        for attempt in range(attempts):
            if self.creds.expires_at <= int(time.time()) + 30:
                await self._refresh_token()

            headers = {
                "Authorization": f"OAuth {self.creds.access_token}",
                "Accept": "application/json",
            }
            r = await self.http.request(method, path, params=params, json=json, headers=headers)

            if r.status_code in (200, 201, 202):
                return r.json() if r.content else {}

            try:
                body = r.json()
                code = body.get("error_code")
                msg = body.get("error_message", "")
            except Exception:
                code = None
                msg = r.text[:200]

            if r.status_code == 401:
                if attempt == 0:
                    await self._refresh_token()
                    continue
                raise WebmasterError(r.status_code, code, msg)

            if r.status_code in RETRYABLE_HTTP and attempt < attempts - 1:
                retry_after = r.headers.get("Retry-After")
                delay = int(retry_after) if retry_after else min(2 ** attempt, 60)
                await asyncio.sleep(delay + random.uniform(0, 1.0))
                continue

            raise WebmasterError(r.status_code, code, msg)

        raise WebmasterError(0, "MAX_RETRIES", "max attempts exceeded")

    # ---------- user / hosts ----------

    async def get_user_id(self) -> int:
        data = await self._request("GET", "/user")
        self.creds.user_id = data["user_id"]
        return data["user_id"]

    async def list_hosts(self) -> list[dict]:
        uid = self.creds.user_id or await self.get_user_id()
        data = await self._request("GET", f"/user/{uid}/hosts")
        return data.get("hosts", [])

    async def add_host(self, host_url: str) -> dict:
        uid = self.creds.user_id or await self.get_user_id()
        try:
            return await self._request("POST", f"/user/{uid}/hosts", json={"host_url": host_url})
        except WebmasterError as e:
            if e.status == 409 and e.code == "HOST_ALREADY_ADDED":
                hosts = await self.list_hosts()
                for h in hosts:
                    if h["ascii_host_url"].rstrip("/") == host_url.rstrip("/"):
                        return h
            raise

    # ---------- search queries ----------

    async def search_queries_popular(
        self, host_id: str, *,
        order_by: str = "TOTAL_SHOWS",
        indicators: list[str] | None = None,
        device: str = "ALL",
        date_from: str | None = None, date_to: str | None = None,
        offset: int = 0, limit: int = 500,
    ) -> dict:
        uid = self.creds.user_id or await self.get_user_id()
        params: dict[str, Any] = {"order_by": order_by, "device_type_indicator": device,
                                   "offset": offset, "limit": limit}
        if indicators: params["query_indicator"] = indicators
        if date_from: params["date_from"] = date_from
        if date_to: params["date_to"] = date_to
        return await self._request(
            "GET", f"/user/{uid}/hosts/{host_id}/search-queries/popular", params=params)

    # ---------- recrawl ----------

    async def recrawl_quota(self, host_id: str) -> dict:
        uid = self.creds.user_id or await self.get_user_id()
        return await self._request("GET", f"/user/{uid}/hosts/{host_id}/recrawl/quota")

    async def recrawl_post(self, host_id: str, url: str) -> dict:
        """Returns {task_id, quota_remainder} or raises."""
        uid = self.creds.user_id or await self.get_user_id()
        try:
            return await self._request(
                "POST",
                f"/user/{uid}/hosts/{host_id}/recrawl/queue",
                json={"url": url},
            )
        except WebmasterError as e:
            if e.status == 409 and e.code == "URL_ALREADY_ADDED":
                return {"task_id": None, "quota_remainder": None, "already_queued": True}
            raise

    async def recrawl_task(self, host_id: str, task_id: str) -> dict:
        uid = self.creds.user_id or await self.get_user_id()
        return await self._request(
            "GET",
            f"/user/{uid}/hosts/{host_id}/recrawl/queue/{task_id}",
        )

    # ---------- sitemaps ----------

    async def add_sitemap(self, host_id: str, sitemap_url: str) -> str:
        """Idempotent sitemap submission."""
        uid = self.creds.user_id or await self.get_user_id()
        path = f"/user/{uid}/hosts/{host_id}/user-added-sitemaps"
        try:
            r = await self._request("POST", path, json={"url": sitemap_url})
            return r["sitemap_id"]
        except WebmasterError as e:
            if e.status == 409 and e.code == "SITEMAP_ALREADY_ADDED":
                data = await self._request("GET", path)
                for s in data.get("sitemaps", []):
                    if s["sitemap_url"].rstrip("/") == sitemap_url.rstrip("/"):
                        return s["sitemap_id"]
            raise

    # ---------- diagnostics ----------

    async def diagnostics(self, host_id: str) -> dict:
        uid = self.creds.user_id or await self.get_user_id()
        return await self._request("GET", f"/user/{uid}/hosts/{host_id}/diagnostics")


# ---------- batch recrawl helper ----------

async def batch_recrawl(
    client: WebmasterClient,
    host_id: str,
    urls: list[str],
    *,
    safety_margin: int = 5,
) -> dict[str, list]:
    """Send up to quota_remainder - safety URLs. Persist skipped ones for tomorrow."""
    quota = await client.recrawl_quota(host_id)
    if quota["daily_quota"] == 0:
        raise RuntimeError(f"daily_quota==0 for {host_id} — verify ownership")
    max_send = max(0, quota["quota_remainder"] - safety_margin)
    to_send = urls[:max_send]
    skipped = urls[max_send:]

    sent, queued, errors = [], [], []
    for url in to_send:
        try:
            r = await client.recrawl_post(host_id, url)
            if r.get("already_queued"):
                queued.append(url)
            else:
                sent.append({"url": url, "task_id": r["task_id"]})
                if (r.get("quota_remainder") or 0) <= safety_margin:
                    break
        except WebmasterError as e:
            if e.status == 429:
                errors.append({"url": url, "code": "QUOTA_EXCEEDED"})
                break
            errors.append({"url": url, "code": e.code or str(e.status)})
    return {"sent": sent, "already_queued": queued, "errors": errors, "skipped": skipped}
```

## Node.js — undici

```typescript
// webmaster.ts — Node 24 + TypeScript
import { request } from "undici";

const API_BASE = "https://api.webmaster.yandex.net/v4";
const OAUTH_TOKEN_URL = "https://oauth.yandex.com/token";

export interface OAuthCreds {
  clientId: string;
  clientSecret: string;
  accessToken: string;
  refreshToken: string;
  expiresAt: number; // unix seconds
  userId?: number;
}

export class WebmasterError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string | null,
    message: string,
  ) {
    super(`${status} ${code}: ${message}`);
  }
}

type OnRefresh = (creds: OAuthCreds) => Promise<void>;

export class WebmasterClient {
  private refreshing: Promise<void> | null = null;

  constructor(
    private creds: OAuthCreds,
    private onRefresh?: OnRefresh,
  ) {}

  private async refreshToken(): Promise<void> {
    if (this.refreshing) return this.refreshing;
    this.refreshing = (async () => {
      const body = new URLSearchParams({
        grant_type: "refresh_token",
        refresh_token: this.creds.refreshToken,
        client_id: this.creds.clientId,
        client_secret: this.creds.clientSecret,
      });
      const { body: rb, statusCode } = await request(OAUTH_TOKEN_URL, {
        method: "POST",
        headers: { "content-type": "application/x-www-form-urlencoded" },
        body: body.toString(),
      });
      if (statusCode !== 200) throw new WebmasterError(statusCode, null, "refresh failed");
      const d = (await rb.json()) as { access_token: string; refresh_token?: string; expires_in: number };
      this.creds.accessToken = d.access_token;
      if (d.refresh_token) this.creds.refreshToken = d.refresh_token;
      this.creds.expiresAt = Math.floor(Date.now() / 1000) + d.expires_in;
      await this.onRefresh?.(this.creds);
    })();
    try { await this.refreshing; } finally { this.refreshing = null; }
  }

  private async req<T>(method: string, path: string,
      opts: { params?: Record<string, unknown>; json?: unknown; attempts?: number } = {}): Promise<T> {
    const attempts = opts.attempts ?? 5;
    for (let attempt = 0; attempt < attempts; attempt++) {
      if (this.creds.expiresAt <= Math.floor(Date.now() / 1000) + 30) await this.refreshToken();
      const qs = opts.params ? "?" + Object.entries(opts.params).flatMap(([k, v]) =>
        Array.isArray(v) ? v.map(x => `${k}=${encodeURIComponent(String(x))}`)
                         : [`${k}=${encodeURIComponent(String(v))}`]).join("&") : "";
      const { statusCode, body, headers } = await request(`${API_BASE}${path}${qs}`, {
        method,
        headers: {
          authorization: `OAuth ${this.creds.accessToken}`,
          accept: "application/json",
          ...(opts.json ? { "content-type": "application/json" } : {}),
        },
        body: opts.json ? JSON.stringify(opts.json) : undefined,
      });
      const text = await body.text();
      const parsed = text ? (JSON.parse(text) as Record<string, unknown>) : {};
      if (statusCode >= 200 && statusCode < 300) return parsed as T;
      const code = (parsed.error_code as string) ?? null;
      const msg = (parsed.error_message as string) ?? text.slice(0, 200);
      if (statusCode === 401 && attempt === 0) { await this.refreshToken(); continue; }
      if ([429, 500, 502, 503, 504].includes(statusCode) && attempt < attempts - 1) {
        const ra = headers["retry-after"];
        const delay = ra ? Number(ra) * 1000 : Math.min(2 ** attempt * 1000, 60000);
        await new Promise(r => setTimeout(r, delay + Math.random() * 500));
        continue;
      }
      throw new WebmasterError(statusCode, code, msg);
    }
    throw new WebmasterError(0, "MAX_RETRIES", "max attempts exceeded");
  }

  async getUserId(): Promise<number> {
    const data = await this.req<{ user_id: number }>("GET", "/user");
    this.creds.userId = data.user_id;
    return data.user_id;
  }

  async recrawlQuota(hostId: string): Promise<{ daily_quota: number; quota_remainder: number }> {
    const uid = this.creds.userId ?? (await this.getUserId());
    return this.req("GET", `/user/${uid}/hosts/${hostId}/recrawl/quota`);
  }

  async recrawlPost(
    hostId: string,
    url: string,
  ): Promise<{ task_id: string | null; quota_remainder: number | null; alreadyQueued?: boolean }> {
    const uid = this.creds.userId ?? (await this.getUserId());
    try {
      return await this.req("POST", `/user/${uid}/hosts/${hostId}/recrawl/queue`, { json: { url } });
    } catch (e) {
      if (e instanceof WebmasterError && e.status === 409 && e.code === "URL_ALREADY_ADDED") {
        return { task_id: null, quota_remainder: null, alreadyQueued: true };
      }
      throw e;
    }
  }
}
```

## PostgreSQL schema (search-query snapshots)

```sql
-- OAuth credentials per user of your service
CREATE TABLE wm_credentials (
  id BIGSERIAL PRIMARY KEY,
  service_user_id BIGINT NOT NULL,
  yandex_user_id BIGINT NOT NULL,
  access_token TEXT NOT NULL,
  refresh_token TEXT NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  scopes TEXT[] NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (service_user_id, yandex_user_id)
);

-- Hosts cache (host_id -> domain)
CREATE TABLE wm_hosts (
  yandex_user_id BIGINT NOT NULL,
  host_id TEXT NOT NULL,
  ascii_host_url TEXT NOT NULL,
  verified BOOLEAN NOT NULL,
  host_data_status TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (yandex_user_id, host_id)
);

-- Daily snapshot of TOP-3000 queries
CREATE TABLE wm_search_query_snapshots (
  host_id TEXT NOT NULL,
  snapshot_date DATE NOT NULL,
  query_id TEXT NOT NULL,
  query_text TEXT NOT NULL,
  device TEXT NOT NULL,  -- ALL/DESKTOP/MOBILE
  total_shows BIGINT,
  total_clicks BIGINT,
  avg_show_position DOUBLE PRECISION,
  avg_click_position DOUBLE PRECISION,
  PRIMARY KEY (host_id, snapshot_date, query_id, device)
);
CREATE INDEX wm_sq_query_text_idx ON wm_search_query_snapshots USING gin (query_text gin_trgm_ops);

-- Recrawl audit log
CREATE TABLE wm_recrawl_tasks (
  host_id TEXT NOT NULL,
  task_id TEXT PRIMARY KEY,
  url TEXT NOT NULL,
  added_time TIMESTAMPTZ NOT NULL,
  state TEXT NOT NULL,  -- IN_PROGRESS / DONE / FAILED
  checked_at TIMESTAMPTZ
);
CREATE INDEX wm_recrawl_host_state_idx ON wm_recrawl_tasks (host_id, state);

-- Daily indexing snapshot
CREATE TABLE wm_indexing_history (
  host_id TEXT NOT NULL,
  snapshot_date DATE NOT NULL,
  http_2xx BIGINT,
  http_3xx BIGINT,
  http_4xx BIGINT,
  http_5xx BIGINT,
  other_count BIGINT,
  in_search BIGINT,
  PRIMARY KEY (host_id, snapshot_date)
);
```

## Daily-snapshot cron (pseudo)

```python
async def daily_snapshot(client, db, host_id):
    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
    INDICATORS = ["TOTAL_SHOWS", "TOTAL_CLICKS", "AVG_SHOW_POSITION", "AVG_CLICK_POSITION"]
    for offset in range(0, 3000, 500):
        page = await client.search_queries_popular(
            host_id, order_by="TOTAL_SHOWS", indicators=INDICATORS,
            offset=offset, limit=500, date_from=yesterday, date_to=yesterday,
        )
        for q in page["queries"]:
            ind = q["indicators"]
            await db.execute("""
                INSERT INTO wm_search_query_snapshots
                  (host_id, snapshot_date, query_id, query_text, device,
                   total_shows, total_clicks, avg_show_position, avg_click_position)
                VALUES ($1,$2,$3,$4,'ALL',$5,$6,$7,$8)
                ON CONFLICT (host_id, snapshot_date, query_id, device) DO UPDATE
                SET total_shows=$5, total_clicks=$6,
                    avg_show_position=$7, avg_click_position=$8
            """, host_id, yesterday, q["query_id"], q["query_text"],
              ind.get("TOTAL_SHOWS"), ind.get("TOTAL_CLICKS"),
              ind.get("AVG_SHOW_POSITION"), ind.get("AVG_CLICK_POSITION"))
        if len(page["queries"]) < 500:
            break
```

## Critical traps

**1. Quota double-spend.** Parallel `recrawl_post` via `asyncio.gather` desynchronizes the local `quota_remainder` from the server — units are lost and some URLs hit 429. **Fix**: sequential POSTs, read `quota_remainder` from each response.

**2. Token refresh race.** Two parallel coroutines with an expired token both try to refresh — two distinct token pairs, one persists first and the other overwrites. **Fix**: `asyncio.Lock` / `Mutex` around refresh (see `_refresh_lock` above).

**3. host_id mutation on scheme change.** Migrating http→https changes `host_id` (`http:example.com:80` → `https:example.com:443`). The old entry survives in the API but transitions to `NOT_LOADED`. Persist `(domain, scheme) → host_id` in a dedicated table.
