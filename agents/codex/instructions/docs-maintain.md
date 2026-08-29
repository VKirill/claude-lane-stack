# Codex docs-maintainer — INIT / night / lint

**Model:** `gpt-5.6-luna` + `max` + `fast`. Do not commit. Do not push. Do not edit `web:` keys (`id kind owns uses used_by surfaces hubs processes symbols web_hash web_status`). English body only. No secret values — env names only.

The host runner runs `project-onboard` with this same Luna model **before** wiki fill when `apps/*/CLAUDE.md` (or root CLAUDE) is still a stub. You still fill any `apps/*/CLAUDE.md` listed in `STALE_DOCS`.

You write **prose in `<!-- body -->` plus editorial** `title/type/status/confidence/tags/sources/updated`. `docs-web` owns INDEX, `web.yaml`, backlinks, `llms.txt`.

One page per pass. Do not create neighbor pages. Missing target → `(planned)`.

Archive off limits: `wiki/`, `TODO/`, `docs/plans/`, `docs/compliance/`, `docs/seo/`. No feature code.

`sources:` = files you actually opened. Code paths only. Never `docs/**`, `wiki/**`, `PROJECT.md`, `CLAUDE.md`. `confidence: high` only if `len(sources) ≥ 15`. After a **complete** fill: `status: active`. If the page is still below the floor, leave `status: stub`.

---

## MODE

The runner sets `MODE=init|night|lint`. Follow that section. If `STALE_JSON` lists `stale_docs`, **never skip** because git was quiet, because `status` is already `active`, or because a short TL;DR exists. Thin active pages are unfinished.

### Completeness floor (INIT and thin refill)

A future coding agent must act from **this page alone**. A 200–400 word blurb is a stub. Do not mark `active` until the page matches its kind:

| kind | Required body |
|---|---|
| unit / surface / `docs/packages/*` / `docs/apps/*` | TL;DR. `## Purpose`. `## Public API` as a **table** of every public export (`Symbol \| file:line \| Purpose`). One mermaid if there is a flow. `## Configuration` (env names only) when the unit reads env. `## Gotchas`. ≥700 words, ≥12 **real** cites. |
| architecture / `apps/*/docs/ARCHITECTURE.md` | Context mermaid. ≥3 H2. For an app pack: 2–5 numbered flows with `file:line`. ≥500 words, ≥12 cites. |
| `apps/*/docs/FLOWS.md` | 2–5 critical flows only. Numbered steps + mermaid + `file:line` each step. |
| gotchas | `## Critical` and `## High`. Each bullet: symptom / cause `file:line` / workaround. ≥6 items, ≥8 cites. |
| hub | `## Scope` + consumer table + what this hub does **not** own. ≥400 words, ≥8 cites. |
| data-model | `erDiagram` + table groups + invariants. ≥10 cites. |
| runbook | Start, smoke, stop, rollback. Numbered steps. ≥400 words, ≥6 cites. |
| glossary | One row per unit/hub + domain terms. 4th column is `file:line`. |
| patterns | Only repeats seen in ≥3 units. Each pattern quotes 3 code sites. |
| `apps/*/CLAUDE.md` | Local passport, not a wiki essay. ≤60 lines. `## What` (runtime role). `## Owns` (paths + composition roots). `## Never / Always` — ≥3 evidenced bullets (`file:line`). `## Verify` — real scoped command. `## Pointers` → `./docs/`. Do not leave Owns+Pointers only. |

**Cites:** open the file, count its lines, put a line that exists. `path:999` on a 40-line file is a fail. Ranges like `file.ts:12-40` are allowed only if both ends exist.

Do not copy `.next/`, `dist/`, or `node_modules/` into prose or `sources:`.

### init — first fill / thin refill

1. Work **only** `stale_docs` (stubs and thin pages first). Leave `deferred`.
2. For each page: read `owns` (entry + public export + the files you will cite). Optional GitNexus `context` on `symbols[]`.
3. Replace `<!-- body -->` from code. No marketing. Meet the floor above.
4. `sources:` = opened files. Do not invent units.
5. Never skip because the page is already `active`.

### night — targeted refresh

1. Work **only** `stale_docs`. Leave `deferred` and unrelated pack files.
2. If the hit reason is thin/stub → treat that page as **init** (grow to the floor).
3. If the hit is only yesterday's diff on a complete page → patch the changed cites. Do not rewrite a healthy page. Do not grow essays.

### lint — weekly / explicit

1. Work **only** paths in `LINT_JSON.errors` (page before `:`).
2. Fix `thin:`, `cite_oob:`, contradictions, glossary rows without cite, candidate patterns without 3 unit quotes.
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

Skip INIT/night because "no code diff" or "already active" while stubs/`stale_docs`/thin pages exist.  
Write INDEX / backlinks / `web:` fields.  
Mark `active` on a page below the floor.  
Invent `file:line`. Touch archive or production source.  
Skip `apps/*/CLAUDE.md` when it is in `STALE_DOCS` — that file is the local passport and you fill it. Still never put `CLAUDE.md` in wiki `sources:`.

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
LEFT_STUB: …   # still below floor
```
