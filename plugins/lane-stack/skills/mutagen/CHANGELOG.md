# Changelog — mutagen

All notable changes to this skill are documented here. SemVer at the skill level.

## [1.0.0] — 2026-05-16

### Added
- Initial high-stakes skill for the Mutagen.ru REST API (RU SEO tool — keyword frequency, competition, SERP analysis).
- SKILL.md navigator with RU+EN bilingual triggers.
- references/ Pattern 2 layout:
  - `REFERENCE.md` — index + decision map
  - `setup.md` — API key, base URL, UTF-8, GET/POST 128KB limit
  - `methods.md` — every method with full signature, params, response shape
  - `check-key-async-pattern.md` — state machine deep-dive (created → processed → completed | rejected | error), polling, idempotency
  - `parser-types.md` — wordstat_n/q/qs/no/qo/qso/key/key_50/direct
  - `serp-report.md` — 22+ report types, key columns, response shapes
  - `filtering.md` — 17 filter_type values, OR-blocks, sort, count
  - `regions.md` — yandex_ru/msk/spb/minsk/nsk/ekb/rostov/kazan/nn + parser region_id
  - `pricing-and-balance.md` — pay-per-call model, balance pre-check pattern
  - `batch-strategy.md` — parser.mass over parser.get, dedup, batch size, polling
  - `projects-and-clustering.md` — Избранное, claster_id, semantic core operations
  - `integration-python.md` — httpx + tenacity + pydantic
  - `integration-node.md` — fetch / axios + retry + types
  - `recommended-defaults.md` — SSOT for tunable knobs
  - `wrong-vs-right.md` — paired anti-patterns
  - `troubleshooting.md` — symptom-indexed failures
  - `eval-cases.md` — positive / negative / edge routing tests

### Notes
- Source of truth: official documentation at https://mutagen.ru/?p=api (verified 2026-05-16).
- API has no version path; treat as docs-only stable REST.
- Pricing intentionally not hardcoded — verify current tariff via account dashboard at https://mutagen.ru/?p=price.
