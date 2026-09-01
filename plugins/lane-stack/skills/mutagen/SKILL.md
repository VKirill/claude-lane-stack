---
name: mutagen
description: "[RU: интеграция mutagen.ru — частотность Яндекс, конкуренция, SERP-отчёты] Mutagen.ru REST API — RU SEO tool: точная частотность Yandex Wordstat, уровень конкуренции (strong), биды Директа, async check_key polling, parser.mass batch jobs, serp.report mega-tool with 22+ report types. Use when: mutagen, mutagen.ru, мутаген, api.mutagen.ru, точная частотность, частотность яндекс вордстат, конкуренция директа, mutagen.check_key, mutagen.parser.mass, mutagen.serp.report, mutagen.balance, claster_id, wordstat_qso, yandex_msk, yandex_spb, кластеризация семантики, SERP отчёт, биды директ, хвосты, упавшие фразы, parser_type, parser.mass polling, mass_id. SKIP: Yandex Wordstat direct API (→wordstat-api); Key Collector desktop (→key-collector); Topvisor/Rush Analytics/Serpstat (different SaaS); Ahrefs/Semrush (foreign SEO); Google Keyword Planner (Google data, Mutagen is Yandex-only)."
stacks:
  - mutagen
  - ru-seo
  - python
  - nodejs
tags:
  - seo
  - ru
  - keywords
  - wordstat
  - serp
  - mutagen
  - yandex
  - clustering
source: vechkasov-global-skills
risk: high-stakes
---

<!-- versions:start -->

## 🎯 Version Requirements (August 2026)

**Primary pins:**
- Mutagen API: `docs-only (stable JSON REST, no version path)`
- Python: `3.14.x`
- Node.js: `24.x (Active LTS)`

> Source of truth: [STACK_VERSIONS.md](../../STACK_VERSIONS.md) — verified 2026-08-24

<!-- versions:end -->

## Usage

Loaded automatically when its description matches the active task. Read only the section you need, then follow the link to the relevant reference file for full detail.

## Use this skill when

- Сбор семантики под Яндекс — массовая проверка точной частотности через `mutagen.parser.mass.new` (wordstat_qso для "[!фраза]")
- Проверка уровня конкуренции (`strong`) ключевых фраз через async `mutagen.check_key.new` + `mutagen.check_key.get` polling
- Получение биdов Яндекс.Директа (`direct.spec` / `direct.first` / `direct.garant`) для оценки стоимости трафика
- Парсинг левой колонки Вордстата — `wordstat_key` (до 2000 ключей, 10 страниц) или `wordstat_key_50` (первые 200 с первой страницы)
- SERP-анализ через `mutagen.serp.report` — конкуренты домена, упавшие/поднявшиеся фразы, хвосты, страницы домена, дополняющие фразы
- Region-specific data — yandex_msk, yandex_spb, yandex_minsk, yandex_nsk, yandex_ekb, yandex_rostov, yandex_kazan, yandex_nn
- Работа с проектами и `claster_id` — `mutagen.progects()` + `mutagen.progect.keywords(progect_id)` для кластеризации семантического ядра
- Building a Python/Node.js client с polling, idempotency, balance pre-check, deduplication, retry с exp backoff

## Do not use this skill when

- Прямой парсинг Яндекс Wordstat без mutagen (own scraper, official Wordstat API) — use `wordstat-api` (cascade marker)
- Desktop tool Key Collector — use `key-collector` (cascade marker)
- Другие RU SEO-сервисы — Topvisor / Rush Analytics / SpyWords / Serpstat — different APIs, use their respective skills
- Foreign SEO SaaS — Ahrefs / Semrush / Moz / SE Ranking — use respective skills; Mutagen is Yandex-only RU domestic
- Google keyword data / Google Ads Keyword Planner — Mutagen returns ONLY Yandex data; for Google use different tooling
- Using the parsed keywords downstream in scraping / content generation — that belongs to the runtime skill (`httpx`, `nodejs`, `python`)

## Purpose

Mutagen.ru is one of the dominant Russian SEO SaaS providers, used by SEO specialists, agencies, and content teams to collect Yandex semantic cores. Its core differentiator: cheap pay-per-call access to Wordstat exact-frequency variants (`wordstat_qso` = `"[!фраза]"`), proprietary competition metric (`strong`, scale ~1-25+), and a mega-tool `serp.report` covering 22+ report types — keyword info, organic positions, PPC bids, domain competitors, page-level analysis, lost/new/rising/falling keywords, и т.д.

This skill is **high-stakes** because every paid method debits the merchant balance per call, and incorrect polling/batching patterns burn money:

1. `check_key.new` creates a paid async task; calling it twice on the same keyword without persisting `task_id` doubles the spend.
2. `parser.mass.new` charges per keyword in the batch — not deduplicating means paying for duplicates.
3. `serp.report` with wrong `region` returns RU-wide data instead of city-specific, leading to wasted budget when re-running.
4. The async pattern (status: `created` → `processed` → `completed` | `rejected` | `error`) requires correct polling with exponential backoff — naive tight loops waste rate limits and create runaway poll storms.
5. UTF-8 is mandatory for Cyrillic keywords; wrong encoding silently corrupts data.
6. Public-service use requires attribution: *"Обязательным условием является размещении рядом с полученными через API данными информации о том, что они получены из Мутагена."*

The skill owns provider-domain knowledge — method shapes, parser-type semantics, region codes, filter/sort/count semantics, polling lifecycle, billing safety. HTTP plumbing belongs to the runtime skill (`httpx`, `nodejs`).

## Using via mcp-mutagen

If you are working inside the **mcp-mutagen** MCP server, the raw Mutagen async API is already wrapped for you. Two tools are available:

- **`mutagen_api`** — generic gateway to the full Mutagen API: SERP reports (`serp.report` with all 23 report types), balance, projects, and keyword analytics. Handles async polling automatically. See [references/cookbook.md](references/cookbook.md) for ready-to-run recipes.
- **`mutagen_competition`** — convenience tool for batch keyword competition checks (`check_key`), with deduplication and 30-day caching built in.

Use `mutagen_competition` for batch competition scoring; use `mutagen_api` for everything else.

### Tool signature

```
mutagen_competition({
  phrases: string[],          // required — one or more Russian search phrases
  poll_timeout_sec?: number,  // optional — max seconds to wait for results (default: 60)
  force_refresh?: boolean,    // optional — bypass 30-day result cache (default: false)
})
```

### What it returns

For each phrase: `strong` (competition score 1-25), `wordstat` (Wordstat frequency), `direct.spec` / `direct.first` / `direct.garant` (Yandex Direct bid estimates in RUB).

### What it does automatically

- Submits `check_key.new` for each phrase, persists `task_id` internally.
- Polls `check_key.get` with exponential backoff until `completed` or timeout.
- Caches results for 30 days per phrase; repeated calls within TTL are free.
- Pass `force_refresh: true` to re-query and overwrite the cache.

### Cost

~0.30 RUB per phrase. Results are cached 30 days, so repeating the same phrase within the TTL costs nothing. **Before calling with a large list, verify your Mutagen balance** — use `mutagen.balance()` directly (curl or a one-off script) or check your account dashboard at `https://mutagen.ru/?api_config`. A negative balance causes all tasks to be `rejected`.

### Example

```
mutagen_competition({phrases: ["ремонт квартир москва", "купить машину"]})
```

Returns an array of two result objects, one per phrase, with `strong`, `wordstat`, and `direct` fields.

### When to use raw API instead

Use the raw `check_key.new` + `check_key.get` pattern (documented below) when you need: custom polling timeouts, streaming partial results, or integration outside the mcp-mutagen runtime.

---

## Capabilities

### API client setup

Single endpoint pattern: `http://api.mutagen.ru/json/{api_key}/{method}/?{params}`. API key in the URL path (obtain at `https://mutagen.ru/?api_config`). UTF-8 required for all requests and source files. GET hard-limit 128KB — anything above MUST use POST with JSON-encoded params in body. Response envelope shape varies by method; status field carries lifecycle for async calls.

> Full reference: [references/setup.md](references/setup.md)

### The method surface

Account: `mutagen.balance` (баланс). Projects/Избранное: `mutagen.progects`, `mutagen.progect.keywords` (with `claster_id` for кластеризация). Async competition: `mutagen.check_key.new` + `mutagen.check_key.get`. Parser: `mutagen.parser.get` (single) + `mutagen.parser.mass.new`/`mass.list`/`mass.id` (batch). SERP mega-tool: `mutagen.serp.report` (22+ report types × 9 regions × 17 filter types).

> Full reference: [references/methods.md](references/methods.md)

### Async `check_key` pattern (state machine)

State flow: `created` → `processed` → `completed` | `rejected` | `error`. Poll `check_key.get(task_id)` with **exponential backoff starting at 2-3 s capped at 30 s, max 60 attempts**. While not `completed`, response mirrors `check_key.new`: `{task_id, status}`. On `completed`: returns `key`, `strong` (конкуренция), `wordstat`, `tails`, `direct.{spec,first,garant}` (ставки в Директе), `vital`, `vital_site` (тематический сайт). **CRITICAL**: persist `task_id` so retries on transient errors don't double-spend. `rejected` is terminal — re-submitting blindly re-charges.

> Full reference: [references/check-key-async-pattern.md](references/check-key-async-pattern.md)

### Parser types — Wordstat frequency variants

Nine parser types map to Wordstat modifier semantics: `wordstat_n` (broad, no quotes), `wordstat_q` (`""` phrase match), `wordstat_qs` (`!""` exact form), `wordstat_no` (`[]` order-locked), `wordstat_qo` (`"[]"`), `wordstat_qso` (`"[!]"` — точная частотность, эталон для SEO), `wordstat_key` (левая колонка Вордстата, до 2000 ключей, 10 страниц + правая колонка/ассоциации), `wordstat_key_50` (первые 200 с первой страницы), `direct` (биды Директа со shows/bid1/bid2/bid3/all_positions). Picking the wrong variant gives wrong frequency and wastes budget.

> Full reference: [references/parser-types.md](references/parser-types.md)

### SERP report — 22+ report types

`mutagen.serp.report` is a single endpoint switching on the `report` parameter. Keyword reports (require `keyword` / `keywords` CSV ≤1000): `report_keyword_info`, `report_keyword_tailings` (хвосты), `report_keyword_variations`, `report_keyword_expansion` (дополняющие фразы), `report_keyword_positions_organic`, `report_keyword_positions_ppc`. Domain reports: `report_keywords_organic` + `_up`/`_down`/`_new`/`_lost` (поднявшиеся/упавшие/новые/потерянные), `report_keywords_ppc`, `report_keywords_ppc_history`, `report_domain_pages`, `report_domain_subdomains`, `report_domain_competitors`, `report_domain_competitors_ppc`, `report_domain_advert`, `report_domain_advert_active`, `report_domain_info`. Page reports: `report_page_info`, `report_page_competitors`, `report_page_recommended_keywords`.

> Full reference: [references/serp-report.md](references/serp-report.md)

### Filtering, sorting, row-count

17 filter types: `gr` (>), `gr_or_eq` (>=), `less` (<), `less_or_eq` (<=), `eq` (=), `not_eq` (!=), `range` (min+max numeric), `in`/`not_in` (CSV list up to 1024), `like`/`not_like` (substring), `like_any`/`not_like_any` (CSV up to 1024), `like_start`/`like_finish` (prefix/suffix), `is` (boolean). Combine with `"or":1` marker to start an OR-block (default AND). Sort: `"column"` asc or `"-column"` desc, one column per request. `count: 1` returns only `{"count": N}` — use for cheap row-count probes before paginating.

> Full reference: [references/filtering.md](references/filtering.md)

### Regions

For `serp.report`: nine `region` values — `yandex_ru` (global, keyword-only reports), `yandex_msk`, `yandex_spb`, `yandex_minsk`, `yandex_nsk`, `yandex_ekb`, `yandex_rostov`, `yandex_kazan`, `yandex_nn`. For parser methods: `region_id="0"` = no region (default); numeric region codes accepted as comma-separated list, `-` prefix excludes (e.g. `"255,-17"`). **Mismatch between intended region and actual call returns useless data** — region-specific frequency differs by orders of magnitude.

> Full reference: [references/regions.md](references/regions.md)

### Pricing & balance safety

Mutagen is pay-per-call. `mutagen.balance()` returns current rubles. Documentation does NOT publish per-call costs in the API page — verify current tarification at `https://mutagen.ru/?p=price`. Pattern: always call `mutagen.balance()` before any paid batch and gate operation on `balance >= expected_cost * 2`. Track expected cost client-side (count of keys × known per-call rate from your account dashboard).

> Full reference: [references/pricing-and-balance.md](references/pricing-and-balance.md)

### Batch strategy — `parser.mass` over loops

`parser.mass.new` accepts `keys_list` (array or CSV) with a `name` tag for tracking; returns `{id, status}`. Poll `parser.mass.id(mass_id)` until `status: "finish"`. Always deduplicate `keys_list` before submit (case-fold + trim Cyrillic) — duplicates are charged. Single-shot `parser.get` is for one-off probes only; never loop over `parser.get` — use `parser.mass.new` for ≥2 keys.

> Full reference: [references/batch-strategy.md](references/batch-strategy.md)

### Projects / Избранное + `claster_id`

`mutagen.progects()` lists user projects (`{progect_id, name}`). `mutagen.progect.keywords(progect_id)` returns `[{keyword, claster_id}]` — the cluster id is the link to the кластеризация tool on the site (`/?p=clasterization`). Use projects for ops tracking, not pipeline state.

> Full reference: [references/projects-and-clustering.md](references/projects-and-clustering.md)

### Python integration

`httpx.AsyncClient` with `tenacity` exp-backoff retry on transient errors, `pydantic` envelope schemas, env var `MUTAGEN_API_KEY`, polling helper for `check_key`/`parser.mass`, dedup helper for keys_list, balance pre-check.

> Full reference: [references/integration-python.md](references/integration-python.md)

### Node.js / TypeScript integration

`fetch` / `axios` with retry, TypeScript types per method, env-based key, polling pattern via `setTimeout` exp-backoff, batch dedup.

> Full reference: [references/integration-node.md](references/integration-node.md)

## Behavioral Traits

- Reads `mutagen.balance()` BEFORE any paid batch (`check_key.new`, `parser.mass.new`, `serp.report`); gates execution on balance ≥ expected_cost × 2
- Persists every `task_id` (check_key) and `mass_id` (parser.mass) to durable storage BEFORE the first poll — recovery after crash must not re-submit and re-charge
- Polls `check_key.get` / `parser.mass.id` with **exponential backoff starting 2-3 s, cap 30 s, max 60 attempts** — never tight-loops
- Always uses `parser.mass.new` for ≥2 keys instead of a `parser.get` loop — batching reduces per-call overhead
- Deduplicates `keys_list` (case-fold + strip Cyrillic whitespace) BEFORE submit — duplicates are charged
- Always specifies `region` explicitly on `serp.report`; never relies on defaults — region mismatch silently returns wrong data
- Uses `count: 1` on `serp.report` to probe row count before paginating with `limit` — cheap probe over expensive full fetch
- POST over GET when total URL length approaches 128KB — typically ≥50 keys in `keys_list` or long filter chains
- UTF-8 enforced end-to-end — source files, HTTP body, response decode, terminal
- Loads `api_key` from `MUTAGEN_API_KEY` env var; scrubs from access logs (key is in URL path)
- Treats `rejected` and `error` statuses as terminal — never auto-resubmits without explicit handling
- Uses values from [recommended-defaults.md](references/recommended-defaults.md) — no inline magic numbers

## Important Constraints

- NEVER hardcode `api_key` in source, commit history, or client bundles — it grants full balance-spending power
- NEVER call `check_key.new` or `parser.mass.new` without a prior `mutagen.balance()` check and known per-call cost
- NEVER call `check_key.new` on the same keyword twice without checking persistent `task_id` first — double-charges
- NEVER tight-loop `check_key.get` / `parser.mass.id` — use exp backoff (2-3 s → 30 s cap, max 60 attempts)
- NEVER use GET with > 50 keys or long filter chains — 128KB hard cap rejects; switch to POST
- NEVER auto-resubmit on `rejected` / `error` — terminal states, requires manual triage
- NEVER mix yandex regions without intent — `yandex_ru` is global keyword-only, city codes give regional SERP / frequency
- NEVER republish raw Mutagen data on a public service without the required attribution to Мутаген
- NEVER call without timeout — pin per-request timeout (30 s default)
- NEVER log the full request URL — `api_key` is in the URL path and ends up in nginx access logs / APM
- ALWAYS validate envelope shape (`status`, presence of `task_id` / `id` / `data`) before reading domain fields
- ALWAYS UTF-8 encode Cyrillic keywords and source files

## Related Skills

**90%-filter applied** — mainstream 2026 choices used in RU SEO pipelines.

### Runtime & HTTP clients
- ✓ `httpx` — Python async HTTP client (primary runtime for SEO scripting)
- ✓ `python` — Python 3.14 (parent runtime for SEO scripting)
- ✓ `nodejs` — Node 24 (alternative runtime)

### Validation & testing
- ✓ `pydantic` — validate Mutagen envelopes (status field, completed-vs-pending response shapes)
- ✓ `pytest` — test polling logic, dedup, balance gating against fixtures

### RU-SaaS pattern peers (quality bar)
- ✓ `proxy6` — RU SaaS skill (high-stakes pattern reference; pay-per-call, polling)
- ✓ `cloudpayments` — RU payment SaaS (high-stakes pattern reference)
- ✓ `yookassa` — RU payment SaaS (high-stakes pattern reference)

### Persistence & scheduling
- ✓ `redis` — Redis 8 (task_id / mass_id cache, idempotency dedup)
- ✓ `postgresql` — PostgreSQL 18 (semantic core storage, batch state, claster_id mapping)
- ✓ `bullmq` — BullMQ 5 (background poller for `check_key` / `parser.mass`)

### Code discipline
- ✓ `karpathy-guidelines`

## API Reference

Domain-specific references (Pattern 2) — load only what's relevant:

| Topic | File |
|---|---|
| Index, decision map, when-to-use which doc | [references/REFERENCE.md](references/REFERENCE.md) |
| API key handling, base URL, UTF-8, GET vs POST 128KB limit, dashboard | [references/setup.md](references/setup.md) |
| Every method — signature, params, response shape, examples | [references/methods.md](references/methods.md) |
| `check_key` async lifecycle — state machine, polling, idempotency, rejected handling | [references/check-key-async-pattern.md](references/check-key-async-pattern.md) |
| Parser types — wordstat_n/q/qs/no/qo/qso/key/key_50/direct, semantics, response shapes | [references/parser-types.md](references/parser-types.md) |
| All 22+ serp.report types, when to use which, response shape, key columns | [references/serp-report.md](references/serp-report.md) |
| All 17 filter_types, OR-blocks, sort syntax, count=1 row count | [references/filtering.md](references/filtering.md) |
| Regions — yandex_ru/msk/spb/minsk/nsk/ekb/rostov/kazan/nn + parser region_id codes | [references/regions.md](references/regions.md) |
| Pricing model, balance pre-check pattern, daily quota safety | [references/pricing-and-balance.md](references/pricing-and-balance.md) |
| Batch strategy — parser.mass over parser.get, dedup, batch size, polling | [references/batch-strategy.md](references/batch-strategy.md) |
| Projects (Избранное) — mutagen.progects, progect.keywords, claster_id, кластеризация | [references/projects-and-clustering.md](references/projects-and-clustering.md) |
| Python integration — httpx, tenacity, pydantic, asyncio, polling helper | [references/integration-python.md](references/integration-python.md) |
| Node.js / TS integration — fetch / axios, types, retry, polling | [references/integration-node.md](references/integration-node.md) |
| **Recommended defaults** — SSOT: timeouts, polling backoff, batch size, balance threshold | [references/recommended-defaults.md](references/recommended-defaults.md) |
| **Wrong vs Right** — paired anti-patterns: key leakage, polling without backoff, missing balance check, duplicate keys, region mismatch | [references/wrong-vs-right.md](references/wrong-vs-right.md) |
| **Troubleshooting** — symptom-indexed: balance 0, stuck on processed, rejected loops, 128KB rejection, encoding, attribution | [references/troubleshooting.md](references/troubleshooting.md) |
| Eval cases — routing tests (positive RU/EN + negative + edge) | [references/eval-cases.md](references/eval-cases.md) |
| **Cookbook** — mutagen_api recipes: free-tier methods, Top-4 SERP reports, all 23 report types table, async polling, pitfalls | [references/cookbook.md](references/cookbook.md) |

**How to use**: open the topic file relevant to the current task. New integration → `setup.md` + `integration-python.md` or `integration-node.md`. Async work → `check_key-async-pattern.md` + `batch-strategy.md`. SERP analysis → `serp-report.md` + `filtering.md`. Tuning → `recommended-defaults.md`. Audit existing code → `wrong-vs-right.md`.
