# xmlstock — Реалистичные клиенты (Python + Node.js)

## Python (httpx + lxml + redis) — production-grade

```python
"""
xmlstock async client с persistence req_id, dedup, retry.
"""
from __future__ import annotations
import asyncio
import hashlib
import os
import random
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import httpx
import redis.asyncio as redis


@dataclass(frozen=True)
class Task:
    engine: str       # 'yandex-xml' | 'yandex-live' | 'google'
    query: str
    lr: int | None = None
    domain: str | None = None
    device: str = "desktop"
    page: int = 0
    tbm: str | None = None
    groupby: int | str | None = None  # only for yandex-xml

    def hash(self) -> str:
        key = f"{self.engine}|{self.query}|{self.lr}|{self.domain}|{self.device}|{self.page}|{self.tbm}|{self.groupby}"
        return hashlib.sha256(key.encode()).hexdigest()[:32]

    def url_params(self) -> dict[str, str]:
        p: dict[str, str] = {"query": self.query, "device": self.device, "page": str(self.page)}
        if self.lr is not None:
            p["lr"] = str(self.lr)
        if self.domain:
            p["domain"] = self.domain
        if self.tbm:
            p["tbm"] = self.tbm
        if self.groupby is not None:
            p["groupby"] = str(self.groupby)
        return p


CONCURRENCY = {"yandex-xml": 50, "yandex-live": 10, "google": 15}
ENDPOINTS = {
    "yandex-xml": "https://xmlstock.com/yandex/xml/",
    "yandex-live": "https://xmlstock.com/yandexlive/xml/",
    "google": "https://xmlstock.com/google/xml/",
}

POLL_INTERVAL = 25  # seconds, must be >= 20-30
MAX_POLL_ATTEMPTS = 120  # ~50 minutes


class XmlstockClient:
    def __init__(self, user: str, key: str, redis_url: str | None = None):
        self.user = user
        self.key = key
        self.http = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            http2=True,
        )
        self.r = redis.from_url(redis_url) if redis_url else None
        self.semaphores = {
            eng: asyncio.Semaphore(n) for eng, n in CONCURRENCY.items()
        }

    async def close(self):
        await self.http.aclose()
        if self.r:
            await self.r.aclose()

    async def fetch_sync(self, task: Task) -> ET.Element:
        """Hybrid режим. Retry на 210 / 55."""
        params = {"user": self.user, "key": self.key, **task.url_params()}
        attempts = 0
        delay = POLL_INTERVAL
        async with self.semaphores[task.engine]:
            while True:
                attempts += 1
                resp = await self.http.get(ENDPOINTS[task.engine], params=params)
                resp.raise_for_status()
                root = ET.fromstring(resp.content)
                err = root.find(".//error")
                if err is None:
                    return root
                code = int(err.get("code", "0"))
                if code in (210, 202):  # queued, retry same URL
                    if attempts > MAX_POLL_ATTEMPTS:
                        raise RuntimeError(f"polling timeout for {task}")
                    await asyncio.sleep(delay + random.uniform(0, 5))
                    continue
                if code in (55, 110, 20):  # rate / channel / unknown — backoff
                    await asyncio.sleep(min(delay * 2, 60) + random.uniform(0, 5))
                    delay = min(delay * 2, 60)
                    continue
                if code == 200:
                    raise RuntimeError("balance depleted")
                raise RuntimeError(f"xmlstock error {code}: {err.text}")

    async def submit_async(self, task: Task) -> str:
        """Async: возвращает req_id, persist в Redis."""
        if task.engine != "yandex-xml":
            raise ValueError("async (delayed=1) supported only on yandex-xml")
        h = task.hash()
        if self.r:
            existing = await self.r.get(f"xmlstock:task:{h}")
            if existing:
                return existing.decode()

        params = {"user": self.user, "key": self.key, "delayed": "1", **task.url_params()}
        resp = await self.http.get(ENDPOINTS[task.engine], params=params)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        req_id_el = root.find(".//req_id")
        if req_id_el is None:
            err = root.find(".//error")
            raise RuntimeError(f"submit failed: {err.text if err is not None else 'no req_id'}")
        req_id = req_id_el.text.strip()
        if self.r:
            await self.r.set(f"xmlstock:task:{h}", req_id, ex=1800)
        return req_id

    async def fetch_by_req_id(self, req_id: str, engine: str = "yandex-xml") -> ET.Element | None:
        """Один опрос. None = not ready. Raises on error 203."""
        params = {"user": self.user, "key": self.key, "req_id": req_id}
        resp = await self.http.get(ENDPOINTS[engine], params=params)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        err = root.find(".//error")
        if err is None:
            return root
        code = int(err.get("code", "0"))
        if code in (202, 201, 210):
            return None  # not ready
        if code == 203:
            raise RuntimeError("req_id expired or unknown")
        raise RuntimeError(f"poll error {code}: {err.text}")

    async def fetch_async_complete(self, task: Task) -> ET.Element:
        req_id = await self.submit_async(task)
        for _ in range(MAX_POLL_ATTEMPTS):
            await asyncio.sleep(POLL_INTERVAL + random.uniform(0, 5))
            r = await self.fetch_by_req_id(req_id, engine=task.engine)
            if r is not None:
                return r
        raise RuntimeError(f"async polling timeout for {task}")
```

### Использование

```python
async def main():
    cli = XmlstockClient(user=os.environ["XMLSTOCK_USER"], key=os.environ["XMLSTOCK_KEY"])
    try:
        # Hybrid (default)
        root = await cli.fetch_sync(Task(
            engine="yandex-xml",
            query="окна купить",
            lr=213,
            groupby=100,
        ))
        for doc in root.findall(".//doc"):
            url = doc.findtext("url")
            print(url)
    finally:
        await cli.close()

asyncio.run(main())
```

### Parsing SERP в structured

```python
def parse_yandex_serp(root: ET.Element) -> list[dict]:
    docs = []
    for i, doc in enumerate(root.findall(".//doc"), start=1):
        docs.append({
            "position": i,
            "url": doc.findtext("url"),
            "domain": doc.findtext("domain"),
            "title": doc.findtext("title"),
            "passages": [p.text for p in doc.findall("passages/passage") if p.text],
        })
    return docs
```

## Node.js (undici + fast-xml-parser + ioredis) — production-grade

```typescript
import { request } from "undici";
import { XMLParser } from "fast-xml-parser";
import { Redis } from "ioredis";
import { createHash } from "node:crypto";
import pLimit from "p-limit";

type Engine = "yandex-xml" | "yandex-live" | "google";

const CONCURRENCY: Record<Engine, number> = {
  "yandex-xml": 50,
  "yandex-live": 10,
  google: 15,
};

const ENDPOINT: Record<Engine, string> = {
  "yandex-xml": "https://xmlstock.com/yandex/xml/",
  "yandex-live": "https://xmlstock.com/yandexlive/xml/",
  google: "https://xmlstock.com/google/xml/",
};

const POLL_INTERVAL_MS = 25_000;
const MAX_POLL_ATTEMPTS = 120;

interface Task {
  engine: Engine;
  query: string;
  lr?: number;
  domain?: string;
  device?: "desktop" | "mobile" | "tablet" | "iphone" | "android";
  page?: number;
  tbm?: "images" | "video" | "news" | "turbo";
  groupby?: number | string;
}

function hashTask(t: Task): string {
  const s = `${t.engine}|${t.query}|${t.lr}|${t.domain}|${t.device ?? "desktop"}|${t.page ?? 0}|${t.tbm}|${t.groupby}`;
  return createHash("sha256").update(s).digest("hex").slice(0, 32);
}

function taskParams(t: Task): Record<string, string> {
  const p: Record<string, string> = {
    query: t.query,
    device: t.device ?? "desktop",
    page: String(t.page ?? 0),
  };
  if (t.lr !== undefined) p.lr = String(t.lr);
  if (t.domain) p.domain = t.domain;
  if (t.tbm) p.tbm = t.tbm;
  if (t.groupby !== undefined) p.groupby = String(t.groupby);
  return p;
}

const parser = new XMLParser({
  ignoreAttributes: false,
  attributeNamePrefix: "@_",
  textNodeName: "#text",
});

const sleep = (ms: number) => new Promise<void>(r => setTimeout(r, ms));

export class XmlstockClient {
  private limits = new Map<Engine, ReturnType<typeof pLimit>>();
  constructor(
    private user: string,
    private key: string,
    private redis?: Redis,
  ) {
    for (const e of Object.keys(CONCURRENCY) as Engine[]) {
      this.limits.set(e, pLimit(CONCURRENCY[e]));
    }
  }

  private buildUrl(engine: Engine, extra: Record<string, string>): string {
    const u = new URL(ENDPOINT[engine]);
    u.searchParams.set("user", this.user);
    u.searchParams.set("key", this.key);
    for (const [k, v] of Object.entries(extra)) u.searchParams.set(k, v);
    return u.toString();
  }

  private async fetchOnce(engine: Engine, extra: Record<string, string>) {
    const url = this.buildUrl(engine, extra);
    const { statusCode, body } = await request(url, {
      bodyTimeout: 30_000,
      headersTimeout: 10_000,
    });
    if (statusCode !== 200) {
      throw new Error(`HTTP ${statusCode} from xmlstock`);
    }
    const text = await body.text();
    const parsed = parser.parse(text);
    const err = parsed?.yandexsearch?.response?.error ?? parsed?.googlesearch?.response?.error;
    return { text, parsed, error: err };
  }

  async fetchSync(task: Task): Promise<any> {
    return this.limits.get(task.engine)!(async () => {
      let delay = POLL_INTERVAL_MS;
      for (let attempt = 0; attempt < MAX_POLL_ATTEMPTS; attempt++) {
        const { parsed, error } = await this.fetchOnce(task.engine, taskParams(task));
        if (!error) return parsed;
        const code = Number(error["@_code"]);
        if (code === 210 || code === 202) {
          await sleep(delay + Math.random() * 5000);
          continue;
        }
        if (code === 55 || code === 110 || code === 20) {
          await sleep(delay * 2 + Math.random() * 5000);
          delay = Math.min(delay * 2, 60_000);
          continue;
        }
        if (code === 200) throw new Error("balance depleted");
        throw new Error(`xmlstock error ${code}: ${error["#text"] ?? ""}`);
      }
      throw new Error(`polling timeout for ${task.query}`);
    });
  }

  async submitAsync(task: Task): Promise<string> {
    if (task.engine !== "yandex-xml") {
      throw new Error("async (delayed=1) supported only on yandex-xml");
    }
    const h = hashTask(task);
    if (this.redis) {
      const existing = await this.redis.get(`xmlstock:task:${h}`);
      if (existing) return existing;
    }
    const { parsed, error } = await this.fetchOnce(task.engine, {
      ...taskParams(task),
      delayed: "1",
    });
    if (error) throw new Error(`submit error ${error["@_code"]}`);
    const reqId = parsed?.yandexsearch?.response?.req_id;
    if (!reqId) throw new Error("no req_id in response");
    if (this.redis) await this.redis.set(`xmlstock:task:${h}`, String(reqId), "EX", 1800);
    return String(reqId);
  }

  async fetchByReqId(reqId: string, engine: Engine = "yandex-xml"): Promise<any | null> {
    const { parsed, error } = await this.fetchOnce(engine, { req_id: reqId });
    if (!error) return parsed;
    const code = Number(error["@_code"]);
    if (code === 202 || code === 201 || code === 210) return null;
    if (code === 203) throw new Error("req_id expired");
    throw new Error(`poll error ${code}`);
  }

  async fetchAsyncComplete(task: Task): Promise<any> {
    const reqId = await this.submitAsync(task);
    for (let i = 0; i < MAX_POLL_ATTEMPTS; i++) {
      await sleep(POLL_INTERVAL_MS + Math.random() * 5000);
      const r = await this.fetchByReqId(reqId, task.engine);
      if (r) return r;
    }
    throw new Error("async polling timeout");
  }
}
```

## POST с XML body (Python)

```python
async def post_yandex_xml(client: httpx.AsyncClient, user: str, key: str, body: str, **url_params):
    params = {"user": user, "key": key, **url_params}
    r = await client.post(
        "https://xmlstock.com/yandex/xml/",
        params=params,
        content=body.encode("utf-8"),
        headers={"Content-Type": "application/xml; charset=utf-8"},
    )
    r.raise_for_status()
    return r.content

body = """<?xml version="1.0" encoding="UTF-8"?>
<request>
  <query>Окна &amp; двери</query>
  <maxpassages>2</maxpassages>
  <page>0</page>
  <groupings>
    <groupby attr="d" mode="deep" groups-on-page="100" docs-in-group="1" />
  </groupings>
</request>
"""

# амперсанд в query экранирован как &amp; — иначе error 18
```

## Хранение результатов

Минимальная схема в PostgreSQL:

```sql
CREATE TABLE xmlstock_serp (
    id BIGSERIAL PRIMARY KEY,
    task_hash CHAR(32) NOT NULL,
    engine TEXT NOT NULL,
    query TEXT NOT NULL,
    lr INT,
    domain_zone TEXT,
    device TEXT,
    page INT,
    tbm TEXT,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw_xml TEXT NOT NULL,
    parsed_docs JSONB NOT NULL,
    UNIQUE (task_hash, captured_at)
);
CREATE INDEX ON xmlstock_serp (engine, query, lr, device, captured_at DESC);
```

Парсинг — отдельным шагом, чтобы можно было перепарсить без повторной оплаты.

## Сравнение: xmlstock vs собственный скрапер через proxy6

| Аспект | xmlstock | Собственный скрапер + proxy6 |
|---|---|---|
| Цена 1k запросов Яндекс | ~18 ₽ | прокси + капчи 100-300 ₽ + риск банов |
| Стабильность | официальный Search API на стороне Яндекса | плавающие капчи, HTML breaking changes |
| Параметры | все официальные | надо имитировать UA, cookies, регион |
| Скорость | 50/10/15 потоков из коробки | зависит от пула прокси |
| Структурированные сниппеты | да (`<passages>`, `<title>`, и т.д.) | парсить из HTML руками |
| Парсинг ads/scroller/related | да (Live) | да, но руками |
| Поддержка | техподдержка | разработка и поддержка своими силами |
| Когда выбрать собственный | низкие объёмы (<100/мес), нестандартные SERP-фичи которых нет в API | |

Для коммерческого SEO на средних/больших объёмах → xmlstock.
