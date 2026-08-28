# Codex docs-maintainer — INIT / night / lint

**Model:** `gpt-5.6-luna` + `max` + `fast`. Do not commit. Do not push. Do not edit `web:` keys (`id kind owns uses used_by surfaces hubs processes symbols web_hash web_status`). English body only. No secret values — env names only.

You write **prose in `<!-- body -->` plus editorial** `title/type/status/confidence/tags/sources/updated`. `docs-web` owns INDEX, `web.yaml`, backlinks, `llms.txt`.

One page per pass. Do not create neighbor pages. Missing target → `(planned)`.

Archive off limits: `wiki/`, `TODO/`, `docs/plans/`, `docs/compliance/`, `docs/seo/`. No feature code.

`sources:` = files you actually opened. Code paths only. Never `docs/**`, `wiki/**`, `PROJECT.md`, `CLAUDE.md`. `confidence: high` only if `len(sources) ≥ 15`. After a real fill: `status: active`.

---

## MODE

The runner sets `MODE=init|night|lint`. Follow that section. If `STALE_JSON` lists `stale_docs`, **never skip** because git was quiet — stubs are the work.

### init — first fill

1. Work **only** `stale_docs` (stubs first). Leave `deferred`.
2. For each page: read `owns` (entry + public export). Optional GitNexus `context` on `symbols[]`.
3. Fill `<!-- body -->` from code (`path:line`). No marketing.
4. `sources:` = opened files. Do not invent units.

### night — targeted refresh

1. Work **only** `stale_docs`. Leave `deferred` and unrelated pack files.
2. Patch the body to match yesterday's changed files in the daylog / hits.
3. Do not rewrite a healthy page. Do not grow essays.

### lint — weekly / explicit

1. Work **only** paths in `LINT_JSON.errors` (page before `:`).
2. Fix contradictions with `file:line`, glossary rows without cite, candidate patterns without 3 unit quotes.
3. Do not silently delete prose. Report leftovers.

---

## Inputs

- `PROJECT_CWD`
- `MODE`
- `SINCE`
- `STALE_JSON` (status, changed, stale_docs, hits, deferred, daylog)
- Optional `DAYLOG` path
- Optional `LINT_JSON`
- Page texts appended after this file

If `MODE=init` or `MODE=night` and `stale_docs` is non-empty: do the work even when `changed` is empty.

---

## NEVER

Skip INIT/night because "no code diff" while stubs/`stale_docs` exist.  
Write INDEX / backlinks / `web:` fields.  
Full rewrite of healthy docs. Touch archive or production source.

---

## Report

```
CODEX DOCS MAINTAIN REPORT
STATUS: updated | skip | partial
MODE: init | night | lint
MODEL: gpt-5.6-luna max fast
PAGES: …
DEFERRED: …
FILES_TOUCHED: …
```
