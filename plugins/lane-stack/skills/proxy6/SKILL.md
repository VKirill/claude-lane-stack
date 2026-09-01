---
name: proxy6
description: "[RU: интеграция proxy6.net — покупка/продление прокси, пул, ipauth, scraping] proxy6.net REST API — RU proxy provider for IPv4/IPv4 Shared/IPv6/MTproto. Methods getprice/getcount/getcountry/getproxy/buy/prolong/delete/setdescr/check/ipauth via https://px6.link/api/{key}/. Money + destructive + 3 req/s rate limit. Use when: proxy6, proxy6.net, px6.link, прокси6, ipv4 shared, ipv6 прокси, mtproto, buy proxy api, getprice, prolong proxy, setdescr, getproxy, ipauth, scraping rotation ru, error_id 100, error_id 105, error_id 300, error_id 400, error_id 429, балансовая проверка, auto_prolong. SKIP: Mobileproxy/Webshare/Brightdata/Oxylabs (different provider); using a proxy in HTTP code after acquisition (→httpx/nodejs); in-browser CORS proxying."
stacks:
  - proxy6
  - ru-proxy
  - python
  - nodejs
tags:
  - proxy
  - scraping
  - ru
  - automation
  - rotation
  - billing
source: vechkasov-global-skills
risk: high-stakes
---

<!-- versions:start -->

## 🎯 Version Requirements (August 2026)

**Primary pins:**
- proxy6 API: `docs-only (stable REST, no version path)`
- Python: `3.14.x`
- Node.js: `24.x (Active LTS)`

> Source of truth: [STACK_VERSIONS.md](../../STACK_VERSIONS.md) — verified 2026-08-24

<!-- versions:end -->

## Usage

Loaded automatically when its description matches the active task. Read only the section you need, then follow the link to the relevant reference file for full detail.

## Use this skill when

- Buying / prolonging / deleting proxies through the proxy6.net REST API — calls to `buy`, `prolong`, `delete`
- Building a proxy pool from `getproxy` results, organising it via `descr` tags, rotating per request / per worker
- Pre-flighting purchases with `getprice` + `getcount` + balance check before calling `buy` (money safety)
- Setting up `ipauth` IP allowlist for production scrapers — full-replace semantics, dev/prod separation
- Implementing a rate-limit-safe client (≤ 3 req/s) with retry/backoff on 429 / `error_id` envelopes
- Debugging proxy6 error responses — `error_id` 100 (auth), 105 (IP not allowed), 300 (insufficient stock), 400 (no money), 410 (zero price), 429 (rate limited)
- Picking the right proxy `version` for the workload — 3 (IPv4 Shared), 4 (IPv4), 5 (MTproto), 6 (IPv6) — and the right country
- Building a scheduled-cleanup job for expired proxies (`state=expired`) and a renewal job before `date_end`

## Do not use this skill when

- Task uses a different proxy provider — Mobileproxy / Webshare / Brightdata / Oxylabs / Smartproxy / iProxy / ProxyEmpire — they have different APIs
- Task is actually **using** a proxy in HTTP code after acquisition — that belongs to the HTTP-client skill (`httpx` for Python, `nodejs` for Node)
- Task is in-browser CORS proxying or local proxy server (mitmproxy / squid / nginx forward proxy) — different domain
- Task is Telegram MTProto client configuration without proxy6 (mtproto auth, session strings) — use `telegram-bot` and the MTProto client docs

## Purpose

proxy6.net is one of the dominant Russian retail proxy providers — IPv4 (dedicated), IPv4 Shared, IPv6, and MTproto-flavoured proxies, sold per proxy per day with a single REST endpoint at `https://px6.link/api/{api_key}/{method}/`. It is widely used by Russian scraping shops, ad-operations teams, social-media automation, and price-monitoring pipelines that need cheap, short-lived, country-targeted proxies.

This skill is **high-stakes** because three of the ten methods cost money or destroy state and the API is hard-limited to 3 requests per second:

1. `buy` debits the merchant balance immediately; `auto_prolong` silently re-charges on expiry.
2. `prolong` debits again and (for mixed-version `ids`) returns no `price_single` — easy to miscalculate.
3. `delete` is irreversible; with the `descr` filter you can wipe an entire pool in one call.
4. `ipauth` REPLACES the full allowlist — passing a partial list deletes everything else.
5. Over-3-req/s bursts return HTTP 429, breaking unaware clients.

The skill owns provider-domain knowledge — method shapes, error semantics, version tradeoffs, billing safety, rate-limit handling, pool management via `descr` tags, and ipauth gotchas. HTTP plumbing (retries, async clients, secret loading) belongs to the runtime skill (`httpx`, `nodejs`).

## Capabilities

### API client setup

Single endpoint pattern: `https://px6.link/api/{api_key}/{method}/?{params}` (api_key in the URL path). Success envelope: `{"status":"yes", user_id, balance, currency, ...}`. Error envelope: `{"status":"no", error_id, error}`. Auth via api_key only; optional IP allowlist in dashboard (returns `error_id 105` if source IP not allowed). The key in the URL path means it appears in nginx / reverse-proxy access logs — log scrubbing is mandatory.

> Full reference: [references/setup.md](references/setup.md)

### The 10 methods

`getprice` (price calc) · `getcount` (stock check) · `getcountry` (countries by version) · `getproxy` (list owned proxies, paged) · `setdescr` (update comment tag) · `buy` (purchase — money) · `prolong` (extend — money) · `delete` (irreversible) · `check` (validate one proxy) · `ipauth` (full-replace allowlist).

> Full reference: [references/methods.md](references/methods.md)

### Proxy versions (3/4/5/6)

Four `version` values map to four distinct products with different prices and protocol support: **3** = IPv4 Shared (cheapest, shared across users), **4** = IPv4 dedicated, **5** = MTproto (Telegram-specific), **6** = IPv6. Pick by target: IPv6 only works against IPv6-aware destinations; MTproto only for Telegram clients; IPv4 Shared is fine for low-trust scraping but flags faster on sensitive sites.

> Full reference: [references/proxy-versions.md](references/proxy-versions.md)

### Rate limit handling (3 req/s budget)

Provider enforces 3 requests per second. Practical client budget: **2 req/s** (33% headroom) under steady load, brief bursts up to 3. Use a token bucket / leaky bucket gate or per-call sleep ≥ 333 ms. Retry policy: 429 → backoff base 500 ms, cap 30 s, max 5 attempts; never retry 4xx envelope errors except `error_id 30` (unknown — single retry).

> Full reference: [references/rate-limit-and-retry.md](references/rate-limit-and-retry.md)

### Purchase and billing safety

Canonical pre-buy sequence: `getprice(count, period, version)` → `getcount(country, version)` → balance check (from any successful envelope) → `buy(...)`. Always set `descr` to a stable ops tag so the order is reattributable later. Default `auto_prolong = OFF` — surprise renewals are a top operational complaint. Document a balance-low threshold (alert when `balance < N × daily_burn`).

> Full reference: [references/purchase-and-billing.md](references/purchase-and-billing.md)

### Pool management & rotation

Organise live proxies by `descr` tag (e.g. `descr=pool:scraper-A:prod`). Rotation strategies: **sticky** (worker keeps one proxy until ban / expiry), **round-robin** (per-request from a shuffled pool), **weighted** (prefer freshest by `date_end`). Ban detection: track per-proxy 4xx/5xx ratio; quarantine on threshold; replace via `buy` with the same `descr`. Schedule a daily cleanup that `getproxy(state=expired)` → `delete(ids=...)`.

> Full reference: [references/pool-management.md](references/pool-management.md)

### IP authentication strategy

`ipauth` sets the full list of source IPs allowed to use the proxies (separate from API allowlist — that's in the dashboard). Critical gotcha: every `ipauth` call REPLACES the prior list. Always send the complete union of dev + prod + CI IPs; pass `ip=delete` to clear all bindings. Prefer ipauth over user/pass for production worker fleets — fewer secrets in code.

> Full reference: [references/ipauth-strategy.md](references/ipauth-strategy.md)

### Python integration (httpx + tenacity)

Async `httpx.AsyncClient` with `tenacity` retry decorators, `pydantic` models for response shapes, api_key in env var (`PROXY6_API_KEY`), per-method functions returning typed envelopes, rate-limit token bucket via `asyncio.Semaphore` + sleep.

> Full reference: [references/integration-python.md](references/integration-python.md)

### Node.js / TypeScript integration

`fetch` or `axios` with `axios-retry` / `p-retry`, TypeScript types for each method's response, env-based key, rate limit via `p-limit` or `bottleneck`.

> Full reference: [references/integration-node.md](references/integration-node.md)

## Behavioral Traits

- Reads `getprice` + `getcount` + envelope `balance` BEFORE every `buy` — never trusts an outdated balance value
- Always passes `descr` on `buy` for ops attribution; never relies on `id` alone for identifying a logical pool
- Defaults `auto_prolong` to OFF; opts in only when there's a documented billing-alert path
- Treats every `ipauth` call as a full-list overwrite — composes the union of all known IPs before sending
- Caps client throughput at **2 req/s** (headroom under the 3 req/s provider limit); centralises the limiter so all callers share it
- Retries only on `429`, network errors, `5xx`, and `error_id 30` — never retries `100/105/200/210/220/230/240/250/260/270/280/300/400/404/410`
- Stores `id`, `ip`, `port`, `user`, `pass`, `date_end`, `descr`, `active` from `getproxy` in a local table and refreshes daily
- Runs `delete` with `ids=` only after a `getproxy` dry-run that lists exactly those ids — never blindly with `descr=` filter
- Uses values from [recommended-defaults.md](references/recommended-defaults.md) — no inline magic numbers
- Loads `api_key` from `PROXY6_API_KEY` env var; scrubs it from access logs at the reverse proxy

## Important Constraints

- NEVER hardcode `api_key` in source, commit history, or client bundles — it grants full balance-spending power
- NEVER call `buy` without a fresh `getprice` + `getcount` + balance check — silent overdraft / out-of-stock buys waste money
- NEVER pass a partial IP list to `ipauth` — it REPLACES the allowlist, instantly cutting off prod workers not in the call
- NEVER enable `auto_prolong=1` without a budget alert and an off-switch — runaway charges are the #1 incident class
- NEVER call `delete` with `descr=` filter without a `getproxy(descr=...)` dry-run that prints every id about to die
- NEVER exceed 3 req/s — even short bursts to 5–10 req/s trigger 429 storms that stall the whole client until backoff drains
- NEVER assume `prolong` mixed-version returns `price_single` — for heterogenous `ids` the field is ABSENT; sum from `list`
- NEVER log the full request URL — `api_key` is in the path and ends up in nginx access logs / APM
- ALWAYS scrub `api_key` from reverse-proxy access logs (Angie/Nginx `log_format` with regex masking)
- ALWAYS validate response shape against the envelope schema before reading domain fields — error envelopes are JSON-200, not HTTP-4xx

## Related Skills

**90%-filter applied** — mainstream 2026 choices used in scraping / automation pipelines.

### Runtime & HTTP clients (where the proxy is actually used)
- ✓ `httpx` — Python async HTTP client (primary runtime for scraping with proxy6 outputs)
- ✓ `nodejs` — Node 24 (alternative scraping runtime)
- ✓ `python` — Python 3.14 (parent runtime for scraping pipelines)

### Validation & testing
- ✓ `pydantic` — validate proxy6 response envelopes and proxy records
- ✓ `pytest` — test the client and rotation logic against fixture envelopes

### RU-SaaS pattern peers (quality bar)
- ✓ `cloudpayments` — RU payment SaaS skill (high-stakes pattern reference)
- ✓ `yookassa` — RU payment SaaS skill (high-stakes pattern reference)

### Persistence & scheduling
- ✓ `redis` — Redis 8 (token-bucket rate limiter, pool cache)
- ✓ `postgresql` — PostgreSQL 18 (pool state, descr tagging, expiry tracking)

### Code discipline
- ✓ `karpathy-guidelines`

## API Reference

Domain-specific references (Pattern 2) — load only what's relevant:

| Topic | File |
|---|---|
| Index, decision map, when-to-use which doc | [references/REFERENCE.md](references/REFERENCE.md) |
| API key handling, log scrubbing, IP allowlist, rate-limit overview | [references/setup.md](references/setup.md) |
| All 10 methods — params, response shapes, examples | [references/methods.md](references/methods.md) |
| Proxy versions 3/4/5/6 — IPv4 Shared vs IPv4 vs MTproto vs IPv6, when to use which | [references/proxy-versions.md](references/proxy-versions.md) |
| All 17 error codes — diagnose / cause / fix (symptom-indexed) | [references/error-codes.md](references/error-codes.md) |
| Rate limit & retry — 3 req/s budget, token bucket, tenacity / p-retry config, 429 backoff | [references/rate-limit-and-retry.md](references/rate-limit-and-retry.md) |
| Purchase & billing — getprice→getcount→buy idempotency, balance check, auto_prolong, descr tagging | [references/purchase-and-billing.md](references/purchase-and-billing.md) |
| Pool management — descr organisation, rotation, ban detection, scheduled cleanup | [references/pool-management.md](references/pool-management.md) |
| ipauth strategy — when to use, full-replace semantics, dev/prod separation | [references/ipauth-strategy.md](references/ipauth-strategy.md) |
| Python integration — httpx, tenacity, pydantic, asyncio limiter | [references/integration-python.md](references/integration-python.md) |
| Node.js / TS integration — fetch/axios, p-retry, types, bottleneck limiter | [references/integration-node.md](references/integration-node.md) |
| **Recommended defaults** — SSOT: rate budget, request timeout, retry policy, auto_prolong default, balance threshold | [references/recommended-defaults.md](references/recommended-defaults.md) |
| **Wrong vs Right** — paired anti-patterns: key leakage, missing retry, blind delete, ipauth wipe, auto_prolong runaway | [references/wrong-vs-right.md](references/wrong-vs-right.md) |
| **Troubleshooting** — symptom-indexed: 429 storm, 100 auth, 105 IP block, 300 stock, 400 balance, 410 zero price, descr overflow, mixed-version prolong, accidental delete | [references/troubleshooting.md](references/troubleshooting.md) |
| Eval cases — routing tests (positive + negative + edge) | [references/eval-cases.md](references/eval-cases.md) |

**How to use**: open the topic file relevant to the current task. Purchase work → `purchase-and-billing.md` + `methods.md`. Rate-limit / 429 work → `rate-limit-and-retry.md` + `troubleshooting.md`. Pool work → `pool-management.md`. New integration → `setup.md` + `integration-python.md` or `integration-node.md`. Tuning knobs → `recommended-defaults.md`.
