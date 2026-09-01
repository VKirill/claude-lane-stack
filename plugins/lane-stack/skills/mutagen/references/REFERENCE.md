# mutagen — Reference index

Slim index. Open the file you actually need; do not load everything.

## Decision map

| You are about to... | Open first |
|---|---|
| Bootstrap a new mutagen client (Python or Node) | [setup.md](setup.md) → [integration-python.md](integration-python.md) or [integration-node.md](integration-node.md) |
| Call `mutagen.balance` / `mutagen.progects` / list-style methods | [methods.md](methods.md) |
| Check competition for ONE keyword (`check_key`) | [check-key-async-pattern.md](check-key-async-pattern.md) → [methods.md](methods.md) |
| Parse Wordstat frequency for MANY keywords | [batch-strategy.md](batch-strategy.md) → [parser-types.md](parser-types.md) → [methods.md](methods.md) |
| Choose the right parser (`wordstat_n` vs `wordstat_qso` vs ...) | [parser-types.md](parser-types.md) |
| Run a SERP report (organic / PPC / domain / page) | [serp-report.md](serp-report.md) → [filtering.md](filtering.md) |
| Filter a report (gr / less / range / in / like) | [filtering.md](filtering.md) |
| Pick a region for serp.report or parser | [regions.md](regions.md) |
| Estimate spend before a batch | [pricing-and-balance.md](pricing-and-balance.md) |
| Tune timeouts / poll backoff / batch size | [recommended-defaults.md](recommended-defaults.md) |
| Hit "rejected" / "error" / stuck on "processed" | [troubleshooting.md](troubleshooting.md) → [check-key-async-pattern.md](check-key-async-pattern.md) |
| Audit an existing implementation | [wrong-vs-right.md](wrong-vs-right.md) |
| Work with projects / `claster_id` | [projects-and-clustering.md](projects-and-clustering.md) |

## Files

| File | Purpose | Lines |
|---|---|---|
| [setup.md](setup.md) | API key, base URL, UTF-8, GET/POST 128KB | small |
| [methods.md](methods.md) | Every method — signature, params, response | medium |
| [check-key-async-pattern.md](check-key-async-pattern.md) | State machine, polling, idempotency | medium |
| [parser-types.md](parser-types.md) | All 9 parser types — semantics, response | small |
| [serp-report.md](serp-report.md) | 22+ report types, response shapes | medium |
| [filtering.md](filtering.md) | 17 filter types, OR-blocks, sort, count | small |
| [regions.md](regions.md) | yandex_* region values + parser region_id | small |
| [pricing-and-balance.md](pricing-and-balance.md) | Pay-per-call, balance pre-check | small |
| [batch-strategy.md](batch-strategy.md) | parser.mass over loops, dedup, batch size | small |
| [projects-and-clustering.md](projects-and-clustering.md) | Избранное, claster_id | small |
| [integration-python.md](integration-python.md) | httpx + tenacity + pydantic client | medium |
| [integration-node.md](integration-node.md) | fetch / axios + types + retry | medium |
| [recommended-defaults.md](recommended-defaults.md) | SSOT for tunable knobs | small |
| [wrong-vs-right.md](wrong-vs-right.md) | Anti-pattern pairs | medium |
| [troubleshooting.md](troubleshooting.md) | Symptom-indexed failures | medium |
| [eval-cases.md](eval-cases.md) | Routing tests | small |

## Convention

- "RU SEO" in this skill always means **Mutagen.ru** — not generic "SEO from Russia".
- `parser` refers to a parser-type value (e.g. `wordstat_qso`), never to API version (Mutagen has one stable REST endpoint).
- `region` (serp.report) ≠ `region_id` (parser methods) — different parameter, different value set; see [regions.md](regions.md).
- `task_id` is for `check_key`; `mass_id` is for `parser.mass` — never conflate.
- "точная частотность" in this skill refers specifically to `wordstat_qso` (`"[!фраза]"`) and the `region_wsqso` column.
