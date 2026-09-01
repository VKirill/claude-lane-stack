# Recommended defaults — proxy6

Single source of truth for every tunable knob. **All other files in this skill cite this table — do not redefine inline.** Source: synthesised from the proxy6.net public API spec (`https://proxy6.net/developers`), the 3 req/s published rate limit, and operational experience with RU scraping pipelines.

> Citation rule: when a recommendation depends on workload, give a default + a range + a "tune up when..." / "tune down when..." condition. Cargo-culting defaults is worse than no defaults.

## Rate limit & client throughput

| Knob | Default | Range | Tune-up when | Tune-down when | Why |
|---|---|---|---|---|---|
| Steady-state target | **2 req/s** | 1–3 req/s | none — this IS the safe maximum below 3 req/s | bursty mixed workload — go to 1 req/s | Provider limit is 3 req/s; 33% headroom protects against jitter |
| Allowed peak | **3 req/s for ≤ 1 s** | — | — | — | Bottleneck reservoir 3 / 1 s; refill 3 / 1 s |
| Max concurrent in-flight | **2** | 1–3 | rare slow endpoints | 429 storm | 2 × ~400 ms each ≈ on-budget |
| Inter-call sleep (sync code) | **≥ 340 ms** | 333–500 ms | strict 3 req/s budget | — | `1000 / 3 ≈ 333.33 ms`; round up |
| Bottleneck `minTime` | **340 ms** | 333–500 | — | — | Same as above |

## HTTP request

| Knob | Default | Range | Notes |
|---|---|---|---|
| Per-request timeout | **10 s** | 5–15 s | proxy6 normally responds in <500 ms; longer means degraded path |
| Connect timeout | **5 s** | — | Subset of overall timeout |
| HTTP method | **GET** | — | Spec is GET; servers tolerate POST but stick to documented |
| Keep-alive | **on** | — | Reduces TLS handshake cost in bursts |
| HTTP/2 | optional | — | Not required; HTTP/1.1 keep-alive is sufficient |

## Retry policy

| Knob | Default | Range | Tune-up when | Tune-down when |
|---|---|---|---|---|
| `attempts` | **5** | 3–7 | very flaky uplinks | strict latency budget |
| Backoff strategy | **exponential with full jitter** | — | — | — |
| Initial delay | **500 ms** | 250 ms – 1 s | — | provider sends Retry-After (rare) |
| Multiplier | **2** | — | — | — |
| Max delay cap | **30 s** | 10–60 s | — | — |
| Retry triggers | **HTTP 429, HTTP 5xx, network errors, `error_id 30`** | — | — | — |
| Non-retry triggers | **all other `error_id` values** | — | — | — |

So delays approximately: 500 ms → 1 s → 2 s → 4 s → 8 s (with random jitter).

## Billing safety

| Knob | Default | Notes |
|---|---|---|
| Pre-buy sequence | **`getprice` → `getcount` → balance check → `buy`** | Skipping any step risks wasted spend or 4xx |
| `auto_prolong` default | **OFF (omit flag)** | Only enable with budget alert + kill-switch |
| Balance safety margin on `buy` | **10%** (balance ≥ quote × 1.10) | Covers tier-change drift |
| Balance alert threshold | **balance < daily_burn × 7** | One week runway minimum |
| `descr` always set | **YES** | Required by ops convention even though optional in API |
| `descr` max length | **50 chars** (provider hard) | Validate client-side before call |
| `descr` character set | **`[A-Za-z0-9:_-]`** (recommended) | Avoid downstream tooling breakage |

## Destructive-action safety

| Knob | Default | Notes |
|---|---|---|
| `delete` requires explicit `ids` | **YES** | Refuse `delete(descr=...)` without prior `getproxy` dry-run unless `confirm_dry_run=False` |
| `ipauth` always passes full union | **YES** | Replace-semantics — never partial |
| `ipauth` audit log | **diff prior→new IPs** | Track who/when/why on every call |

## Pool management

| Knob | Default | Range | Notes |
|---|---|---|---|
| Pool refresh interval | **60 min** | 15–240 min | Shorter for rapidly changing pools |
| Ban-detection error window | **last 50 requests** | 20–200 | Per proxy |
| Ban-detection threshold | **30% error rate** | 10–50% | Above → quarantine |
| Quarantine cooldown | **30 min** | 10–60 min | Then probe to revive or kill |
| Daily expired-cleanup job time | **off-peak (e.g. 04:00 local)** | — | One scheduled run |
| Min pool size before refill | **70% of target** | 50–90% | Higher = more headroom |

## Versions & defaults

| Question | Default |
|---|---|
| Pick `version` for unspecified workload | `4` (IPv4 dedicated) — safest, most-compatible |
| Pick `type` for HTTP scraping | `http` — simpler client config than SOCKS |
| Pick `country` | per workload; if unspecified, `ru` (proxy6 is RU-domestic favored) |
| `period` for trial pool | `7` days |
| `period` for production pool | `30` days |
| `count` for trial pool | `5` proxies |

## Observability

| Knob | Default |
|---|---|
| Log api_key in URL | **NEVER** — mask `/api/***/` at reverse proxy |
| Log per-call structured fields | `method, masked_params, http_status, response_status, error_id, latency_ms, attempt` |
| Log response `list` payloads | **NO** — contains proxy credentials |
| Trace span name | `proxy6.<method>` |
| Trace span attributes | method name, response status, error_id, attempt |
| Metric: `proxy6_calls_total{method,status}` | counter |
| Metric: `proxy6_call_latency_seconds{method}` | histogram |
| Metric: `proxy6_balance{currency}` | gauge — update from every envelope |
| Alert: balance threshold | when below 7 × daily_burn |
| Alert: error_id 100 / 105 spike | any occurrence in prod |
| Alert: error_id 429 rate | > 5% of calls over 5 min |

## Pin policy

The provider API is **`docs-only` and versionless** — there is no `v1`/`v2` path. Pin behavior via:
- Reference docs URL: `https://proxy6.net/developers`
- Base URL: `https://px6.link/api/{key}/`
- Last verified: 2026-05-16

If proxy6 publishes a breaking change (new error code, removed field, response shape change), bump the skill's `CHANGELOG.md` MAJOR and update affected references.
