# Setup — mutagen.ru API client

## Base URL and method dispatch

Single endpoint pattern:

```
http://api.mutagen.ru/json/{api_key}/{method}/?{params}
```

- `{api_key}` — your private API key (path segment, NOT a query parameter)
- `{method}` — dotted method name with `/` instead of `.`, e.g. `mutagen.check_key.new` → `mutagen.check_key.new/`
- `{params}` — query string for GET, or POST body (JSON) for POST

Response is JSON.

## Where to get the API key

Dashboard: `https://mutagen.ru/?api_config`. The key shown there is the same one you embed in the URL path of every call. Keep it server-side only — anyone with the key can drain your balance.

## Encoding — UTF-8 only

The documentation states:

> «API работает в кодировке UTF-8, поэтому кодировка файла так же должна быть UTF-8»

This applies to:

- Source file encoding (your `.py` / `.ts` / `.js`)
- HTTP request body (POST)
- Query string URL-encoding of Cyrillic keywords
- Decoder used to parse the JSON response

In Python: `requests.post(..., json=..., headers={"Content-Type": "application/json; charset=utf-8"})` is correct; never `urllib.parse.quote(key, encoding="cp1251")`. In Node.js: `fetch(url)` with `URL` / `URLSearchParams` produces correct UTF-8 percent-encoding by default.

## GET vs POST — 128KB hard limit

- **GET** — URL length limited to 128KB total (path + query). Acceptable for short calls: `balance`, `progects`, `check_key.new(key)` with a short key, `parser.get`.
- **POST** — preferred for large payloads. Parameters encoded as JSON in the POST body.

Concretely:

| Method | Recommended HTTP method |
|---|---|
| `mutagen.balance` | GET |
| `mutagen.progects` | GET |
| `mutagen.progect.keywords` | GET |
| `mutagen.check_key.new` | GET (single key) |
| `mutagen.check_key.get` | GET |
| `mutagen.parser.get` | GET |
| `mutagen.parser.mass.new` | **POST** (keys_list often > GET budget) |
| `mutagen.parser.mass.list` | GET |
| `mutagen.parser.mass.id` | GET |
| `mutagen.serp.report` | **POST** when `keywords` CSV is long or filter chain is large |

Rule of thumb: if you build the URL and `len(url) > 100_000`, switch to POST. Don't wait to hit 128KB — leave headroom.

## Response envelope

The envelope shape varies by method (Mutagen does NOT have a single uniform `{status, data}` shape like some APIs). Notable shapes:

- Synchronous calls (`balance`, `progects`, `parser.get` after finish) → return the data directly with a `status` field where applicable.
- Async calls (`check_key.new` / `check_key.get`, `parser.mass.new` / `parser.mass.id`) → return `{status, task_id|id, ...}` with status in {`created`, `processed`, `completed`, `rejected`, `error`} for check_key; {`stop`, `process`, `finish`, `error`} for parser.mass.

ALWAYS validate the `status` field (when present) before reading domain fields. See [methods.md](methods.md) for per-method envelope shapes.

## Authentication and access

- API key in URL path = the only auth mechanism. No HTTP headers, no OAuth, no signing.
- The key appears in nginx / reverse-proxy access logs by default — **scrub it**.

### Log scrubbing (Angie / Nginx)

```nginx
map $request_uri $request_uri_scrubbed {
    "~^(?<prefix>/json/)[^/]+(?<suffix>/.*)$"  "${prefix}***${suffix}";
    default                                     $request_uri;
}
log_format scrubbed '... "$request_method $request_uri_scrubbed $server_protocol" ...';
access_log /var/log/nginx/mutagen.access.log scrubbed;
```

Verify after one real request: the key segment must read `***`.

### Env var pattern

```bash
# Server env
export MUTAGEN_API_KEY="..."
```

Python:

```python
import os
api_key = os.environ["MUTAGEN_API_KEY"]
```

Node.js:

```ts
const apiKey = process.env.MUTAGEN_API_KEY;
if (!apiKey) throw new Error("MUTAGEN_API_KEY not set");
```

Never check the key into git, container images, or frontend bundles.

## Restrictions on use

Per the official docs:

- **Private use only** — designed for personal use.
- **No resale** — redistributing API access is prohibited.
- **Public-service exception** — using Mutagen data inside a public-facing service requires written approval from `support@mutagen.ru` AND mandatory attribution near every displayed Mutagen-sourced data point:

> «Обязательным условием является размещении рядом с полученными через API данными информации о том, что они получены из Мутагена.»

If you ship a dashboard, report exporter, or any UI that exposes Mutagen-derived numbers to end users (not just your internal ops team), you MUST display this attribution.

## Rate limits

The documentation does not publish concrete per-second rate limits. Practical client guidance — see [recommended-defaults.md](recommended-defaults.md) for concurrency, timeouts, and polling defaults.

## Pin policy

The provider API is **docs-only and versionless** — no `v1`/`v2` path. Pin behavior via:

- Reference docs URL: `https://mutagen.ru/?p=api`
- Base URL: `http://api.mutagen.ru/json/{key}/`
- Dashboard: `https://mutagen.ru/?api_config`
- Pricing page: `https://mutagen.ru/?p=price`
- Last verified: 2026-05-16

If Mutagen publishes a breaking change (new error status, removed field, new report type), bump the skill's CHANGELOG.md MAJOR and update affected references.
