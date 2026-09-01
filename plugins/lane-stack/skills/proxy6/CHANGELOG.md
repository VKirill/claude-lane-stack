# Changelog — proxy6

All notable changes to this skill are documented here. Versioning follows SemVer at the skill level (description / structural changes bump MINOR; content fixes bump PATCH; trigger-routing or capability shape changes bump MAJOR).

## [1.0.0] — 2026-05-16

### Added
- Initial release of the high-stakes proxy6.net skill.
- Frontmatter description with RU+EN trigger terms and SKIP rules for non-proxy6 providers and downstream HTTP usage.
- Pattern 2 layout: navigator `SKILL.md` + 15 `references/` files.
- Coverage of all 10 documented methods: `getprice`, `getcount`, `getcountry`, `getproxy`, `setdescr`, `buy`, `prolong`, `delete`, `check`, `ipauth`.
- Coverage of all 4 proxy versions (3 IPv4 Shared, 4 IPv4, 5 MTproto, 6 IPv6) with selection guidance.
- Coverage of all 17 error codes (30 / 100 / 105 / 110 / 200 / 210 / 220 / 230 / 240 / 250 / 260 / 270 / 280 / 300 / 400 / 404 / 410) plus HTTP 429.
- Rate-limit handling at 3 req/s with safe 2 req/s client budget; token-bucket pattern; retry policy.
- Money safety: pre-buy `getprice` + `getcount` + balance check; `auto_prolong = OFF` default; balance alert threshold.
- Destructive safety: dry-run-before-delete protocol; `ipauth` full-replace warning.
- Pool management via `descr` tagging; rotation strategies (sticky / round-robin / weighted); ban detection; scheduled cleanup.
- `ipauth` strategy: full-list overwrite gotcha, dev/prod IP separation.
- Python integration: `httpx.AsyncClient` + `tenacity` + `pydantic` + `asyncio.Semaphore` rate limiter.
- Node.js / TypeScript integration: `fetch` / `axios` + `p-retry` / `axios-retry` + `bottleneck` limiter + TS response types.
- Recommended defaults SSOT for retry / timeout / concurrency / balance thresholds.
- Wrong-vs-right anti-pattern pairs (10+).
- Symptom-indexed troubleshooting reference (high-stakes requirement).
- Eval cases v3: 10+ positive, 10+ negative, edge cases.
