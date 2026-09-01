# xmlstock — Rate limits и concurrency-стратегия

## Рекомендованные настройки

| Engine | Concurrency (потоков) | RPS hard-cap | Источник |
|---|:-:|:-:|---|
| Яндекс Search API (XML) | **50** | 100 | xmlstock docs |
| Яндекс Live | **10** | 10 | xmlstock docs |
| Google XML Search | **15** | 15 | xmlstock docs |

Если "такая реализация не представляется возможной" (нет нормального семафора), документация ограничивает RPS. Но **правильный** способ — потоковая обработка.

## Принцип "одна задача в полёте → следующая"

> Отправляйте следующий запрос **сразу после получения результата** на предыдущий.

Не делать так:
- Большой пакет (>500-1000) разом → часть встанет в очередь → часть отсечётся → эффективная скорость ниже равномерной.
- Накапливать запросы и слать пачкой "раз в N секунд".

Делать так:
- Семафор на N (50/10/15), `asyncio.Semaphore` или `p-limit`.
- Каждый воркер: получил результат → берёт следующий ключ из очереди.
- На 210/202 — НЕ блокирует общую очередь, polling в фоне.

## Python (asyncio + httpx) шаблон

```python
import asyncio
import httpx

CONCURRENCY = {"yandex-xml": 50, "yandex-live": 10, "google": 15}

class XmlstockClient:
    def __init__(self, engine: str, user: str, key: str):
        self.engine = engine
        self.user = user
        self.key = key
        self.semaphore = asyncio.Semaphore(CONCURRENCY[engine])
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            limits=httpx.Limits(max_connections=CONCURRENCY[engine] * 2),
            http2=True,
        )
        self.url = {
            "yandex-xml": "https://xmlstock.com/yandex/xml/",
            "yandex-live": "https://xmlstock.com/yandexlive/xml/",
            "google": "https://xmlstock.com/google/xml/",
        }[engine]

    async def fetch(self, params: dict) -> bytes:
        async with self.semaphore:
            params = {"user": self.user, "key": self.key, **params}
            r = await self.client.get(self.url, params=params)
            r.raise_for_status()
            return r.content

    async def close(self):
        await self.client.aclose()

async def main(queries: list[str]):
    cli = XmlstockClient("yandex-xml", "11396", "key...")
    try:
        tasks = [
            cli.fetch({"query": q, "lr": 213, "groupby": 100})
            for q in queries
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for q, r in zip(queries, results):
            print(q, len(r) if isinstance(r, bytes) else f"err: {r}")
    finally:
        await cli.close()
```

С учётом 210/202 retry — оборачивать `fetch()` в `retry_async()` (см. `integration.md`).

## Node.js (p-limit + got/undici) шаблон

```typescript
import { request } from "undici";
import pLimit from "p-limit";

const CONCURRENCY = { "yandex-xml": 50, "yandex-live": 10, google: 15 } as const;

class XmlstockClient {
  private limit;
  private base: string;
  constructor(
    private engine: keyof typeof CONCURRENCY,
    private user: string,
    private key: string,
  ) {
    this.limit = pLimit(CONCURRENCY[engine]);
    this.base = {
      "yandex-xml": "https://xmlstock.com/yandex/xml/",
      "yandex-live": "https://xmlstock.com/yandexlive/xml/",
      google: "https://xmlstock.com/google/xml/",
    }[engine];
  }

  fetch(params: Record<string, string | number>) {
    return this.limit(async () => {
      const url = new URL(this.base);
      url.searchParams.set("user", this.user);
      url.searchParams.set("key", this.key);
      for (const [k, v] of Object.entries(params)) {
        url.searchParams.set(k, String(v));
      }
      const { statusCode, body } = await request(url.toString(), {
        bodyTimeout: 30_000,
        headersTimeout: 10_000,
      });
      if (statusCode !== 200) throw new Error(`HTTP ${statusCode}`);
      return await body.text();
    });
  }
}
```

## Backoff на 55 / 503

```python
async def fetch_with_backoff(client, params, max_attempts=5):
    delay = 2.0
    for attempt in range(max_attempts):
        try:
            r = await client.fetch(params)
            return r
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (502, 503, 504):
                await asyncio.sleep(delay + random.uniform(0, delay))
                delay = min(delay * 2, 60)
                continue
            raise
        # Парсим body на code 55 / 110:
        # if error_code in (55, 110, 20):
        #     await asyncio.sleep(delay + jitter); delay *= 2; continue
    raise RuntimeError("Max retries exceeded")
```

## Polling 210/202 без блокировки воркеров

**Не** делать:
```python
# ❌ блокирует worker на 30 секунд
while True:
    r = await fetch(...)
    if not pending(r): return r
    await asyncio.sleep(30)
```

При concurrency=50 это **разрешено** (потому что 50 параллельных), но при глубоком polling — занимает слот без пользы. На больших объёмах с длинным polling — лучше:

**Декомпозиция**:
- Producer ставит задачу в очередь (Redis Stream / BullMQ / DB row `status=pending`).
- Submitter воркер (concurrency=50): отправляет `delayed=1` → получает `req_id` → пишет в БД.
- Poller воркер: каждые 20-30 с делает batch `req_id` → результат / 202 / 203.
- Готовые ответы → consumer.

Это масштабируется до миллионов ключей.

## Договорённости с техподдержкой

> Если вам необходимо собрать большой объем данных и требуется заведомо большее количество потоков, рекомендуем сначала написать в нашу техподдержку.

При >100k запросов в сутки или > 50/10/15 потоков **сначала** написать в поддержку xmlstock, получить green light. Они могут поднять лимиты на конкретный аккаунт.

## Что точно НЕ делать

- ❌ `asyncio.gather(*[fetch(q) for q in 10000_queries])` без семафора — взорвёт RPS.
- ❌ Использовать одну connection без `http2` для тысяч запросов — head-of-line blocking.
- ❌ Игнорировать 55/503 без backoff — будут каскадные failures.
- ❌ Polling 202 с интервалом <20 c — словишь 201 (cache cooldown).
- ❌ Запускать пачку async-запросов утром и проверять вечером единым batch'ем — лучше потоково.

## Графики ожидаемой пропускной способности

- Яндекс XML: ~50-100 RPS × 86400 = **4-8M запросов/сутки** теоретически.
- Яндекс Live: ~10 RPS × 86400 = **~860k/сутки**.
- Google XML: ~15 RPS × 86400 = **~1.3M/сутки**.

Реальные цифры ниже из-за async-задержек, retry, балансовых ограничений.
