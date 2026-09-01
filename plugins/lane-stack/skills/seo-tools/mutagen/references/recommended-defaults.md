# Recommended defaults — mutagen

Single source of truth for every tunable knob. **All other files in this skill cite this table — do not redefine inline.** Source: synthesised from the official Mutagen API docs (`https://mutagen.ru/?p=api`) and operational experience with RU SEO pipelines.

> Citation rule: when a recommendation depends on workload, give a default + a range + a "tune up when..." / "tune down when..." condition.

## HTTP request

| Knob | Default | Range | Notes |
|---|---|---|---|
| Per-request timeout | **30 s** | 15-60 s | Most calls respond in < 1 s; batch / report calls may legitimately take longer; cap before infinite hang |
| Connect timeout | **10 s** | 5-15 s | Subset of overall timeout |
| HTTP method (small calls) | **GET** | — | balance, progects, check_key.new, parser.get |
| HTTP method (large calls) | **POST** | — | parser.mass.new, serp.report with large keywords/filter |
| GET URL size hard limit | **128 KB** | — | Provider hard limit; switch to POST before this |
| GET URL size client cap | **100 KB** | — | Leave headroom; switch to POST above this |
| Keep-alive | **on** | — | Reduces TLS handshake cost in bursts |
| Encoding | **UTF-8** | — | Required by provider; no negotiation |

## Retry policy (network / transient)

| Knob | Default | Range | Notes |
|---|---|---|---|
| `attempts` | **5** | 3-7 | Network-level retries (connection reset, 5xx) only |
| Backoff strategy | **exponential with full jitter** | — | — |
| Initial delay | **500 ms** | 250 ms - 1 s | — |
| Multiplier | **2** | — | — |
| Max delay cap | **30 s** | 10-60 s | — |
| Retry triggers | **HTTP 5xx, network errors (timeout, reset, DNS)** | — | — |
| Non-retry triggers | **Application-level `status: rejected` / `error`**; HTTP 4xx | — | Terminal — manual triage |

Delays: ~500 ms → 1 s → 2 s → 4 s → 8 s (with random jitter).

## Polling — `check_key.get`

| Knob | Default | Range | Notes |
|---|---|---|---|
| Initial poll delay | **2 s** | 1-5 s | Most check_key tasks complete in 5-30 s |
| Backoff multiplier | **1.5** | 1.2-2.0 | Gentler than HTTP retry — don't overshoot |
| Max single sleep | **30 s** | 15-60 s | — |
| Max poll attempts | **60** | 30-120 | ~10-15 min total budget |
| On `completed` | **stop, return data** | — | — |
| On `rejected` / `error` | **stop, raise terminal error** | — | DO NOT auto-resubmit |
| Idempotency lookup | **YES — check task_id store first** | — | Avoid double-charging |

## Polling — `parser.mass.id`

| Knob | Default | Range | Notes |
|---|---|---|---|
| Initial poll delay | **5 s** | 3-10 s | Batches take longer to start than check_key |
| Backoff multiplier | **1.5** | — | — |
| Max single sleep | **60 s** | 30-120 s | — |
| Max poll attempts | **120** | 60-240 | ~30 min total budget |
| On `finish` | **stop, return data** | — | — |
| On `error` | **stop, raise terminal error** | — | DO NOT auto-resubmit |

## Batch sizing — `parser.mass.new`

| Knob | Default | Range | Tune up when | Tune down when |
|---|---|---|---|---|
| Keys per batch | **500-1000** | 100-2000 | very simple parser (`wordstat_n`) | complex parser (`wordstat_key`) on rare phrases |
| Max in-flight batches per account | **2** | 1-3 | account isolated, no other consumers | shared account |
| Dedup before submit | **MANDATORY** | — | — | — |
| Normalize before dedup | **strip + collapse whitespace + casefold** | — | — | — |

## Concurrency — `check_key.new`

| Knob | Default | Range | Notes |
|---|---|---|---|
| Max concurrent submits | **5** | 1-10 | Conservative — Mutagen doesn't publish a published RPS cap |
| Inter-submit gap | **~200 ms** | 100-500 ms | Smooths burst on the submission side |

## Balance safety

| Knob | Default | Notes |
|---|---|---|
| Pre-batch balance check | **MANDATORY** | Call `mutagen.balance()` before any paid batch |
| Balance safety multiplier | **2.0** (balance ≥ expected_cost × 2.0) | Higher (1.5x is min) for variable-cost reports |
| Daily spend budget | **per-pipeline config value** | Block when day's spend would exceed |
| Balance alert: warn | **balance < daily_burn × 7** | 1 week runway |
| Balance alert: critical | **balance < daily_burn × 2** | Top up now |
| Balance alert: page | **balance < daily_burn × 0.5** | On-call wake-up |
| `count: 1` probe on `serp.report` | **MANDATORY for unknown row counts** | Cheap probe before expensive pull |

## SERP report safety

| Knob | Default | Notes |
|---|---|---|
| `region` specified explicitly | **YES** | Never rely on default; region mismatch = silent wrong data |
| `limit` set explicitly | **YES** | Never rely on default; unbounded pull = unexpected bill |
| `region_wsqso` minimum filter | **≥ 30 (niche) / ≥ 100 (general)** | Drop near-zero-volume noise |
| `words` max | **≤ 7-10** | Drop ultra-long-tail garbage |

## Persistence

| Knob | Default | Notes |
|---|---|---|
| `task_id` persistence | **MANDATORY before first poll** | Crash recovery requires durable state |
| `mass_id` persistence | **MANDATORY before first poll** | Same |
| Result cache TTL | **7-30 days** | Workload-dependent; SEO data ages well |

## Observability

| Knob | Default |
|---|---|
| Log api_key in URL | **NEVER** — mask `/json/***/` at reverse proxy |
| Log per-call structured fields | `method, masked_params, http_status, response_status, latency_ms, attempt` |
| Trace span name | `mutagen.<method>` |
| Trace span attributes | method, status, attempt, latency_ms |
| Metric: `mutagen_calls_total{method,status}` | counter |
| Metric: `mutagen_call_latency_seconds{method}` | histogram |
| Metric: `mutagen_balance_rub` | gauge — update from every `balance` call |
| Metric: `mutagen_check_key_completed_total` / `_rejected_total` / `_error_total` | counter |
| Alert: rejected rate | > 5% over 1 h |
| Alert: balance below threshold | per balance thresholds above |

## Encoding

| Knob | Default |
|---|---|
| Source file encoding | **UTF-8** |
| HTTP body encoding | **UTF-8** |
| Response decode | **UTF-8** |
| Terminal locale (for ops scripts) | **`LANG=ru_RU.UTF-8` or `C.UTF-8`** |

## Pin policy

The provider API is **docs-only and versionless** — there is no `v1`/`v2` path. Pin behavior via:

- Reference docs URL: `https://mutagen.ru/?p=api`
- Base URL: `http://api.mutagen.ru/json/{key}/`
- Dashboard: `https://mutagen.ru/?api_config`
- Pricing page: `https://mutagen.ru/?p=price`
- Last verified: 2026-05-16

If Mutagen publishes a breaking change (new status, removed field, new report type), bump the skill's `CHANGELOG.md` MAJOR and update affected references.
