---
name: project-onboard
description: Primary project onboarding for Claude Lane Stack. Diátaxis-classified LLM pack (MODULE_MAP, API_SURFACE, TEST_INDEX, TAXONOMY, RUNBOOK, Google DESIGN.md). Schemas + validation in references/. Weekly docs-maintainer. Use when: info, справка, lane-stack:project-onboard info, /project-onboard, онбординг, init project, bootstrap CLAUDE.md, deep onboard, wiki→llm docs.
argument-hint: "[info]"
---

# Project onboard (Claude Lane Stack)

## Info (print and stop)

If `$ARGUMENTS` is `info`, or the user says `info` / `справка` / `как запускать` this skill:
print the block below **verbatim** (Russian), then **stop**. Do not start onboard.

```text
project-onboard — первичная карта репо (CLAUDE.md + LLM-pack)

Когда
- Нет CLAUDE.md / пустой или чужой репо.
- Уже живой UI без DESIGN.md → design-lead (project-design), не повторный onboard.

Как открыть шпаргалку
- /lane-stack:project-onboard info
- каталог: /lane-stack:info

Запуск
- /project-onboard
- /project-onboard deep
- /project-onboard /path/to/repo fast
- CLI: project-onboard .
- агент: project-onboarder (Codex, не Grok)

Флаги
- deep / fast — глубина
- full / minimal — scenario
- --seed-only — только заглушки, без модели

После
- RU-саммари: поверхности, модули, тесты, DESIGN?, RUNBOOK?
- has_ui → docs/DESIGN.md (Google)
- docs включены + паспорт тонкий → сначала этот скилл / project-onboarder, потом docs-maintainer
- weekly refresh: docs-maintainer, не этот скилл
```

## Who runs it

| Role | How |
|------|-----|
| **One-shot CLI** | `project-onboard .` (detect + seed + Codex/Cursor fill) |
| **Default writer** | **Codex** (`stages.onboard` from adoc) |
| Instructions | `~/.agents/codex/instructions/onboard.md` |
| Model / effort / fast | **adoc** `stages.onboard` |
| Weekly refresh | `docs-maintainer` (`ONBOARD_REFRESH=weekly`) |
| Existing UI, no DESIGN.md | `design-lead` (skill `project-design`) — extract, do not re-onboard |

Default CLI = full pipeline. `--seed-only` = stubs without model. Do **not** use Grok.

## References (MUST load before filling)

| Ref | What |
|-----|------|
| [references/PACK-SCHEMAS.md](references/PACK-SCHEMAS.md) | Author every file (Diátaxis + schemas) |
| [references/VALIDATION.md](references/VALIDATION.md) | Shell + acceptance; refuse `complete` |
| [references/design-md-standard.md](references/design-md-standard.md) | Full `@google/design.md` canon |
| https://diataxis.fr/ | Tutorial / how-to / reference / explanation |
| https://agents.md/ · https://llmstxt.org/ | Agent entry + curated index |

**Classifier file in every project:** `docs/llm/TAXONOMY.yaml`  
We **omit tutorials** from the LLM pack.

## Pack summary

| File | Diátaxis | Load |
|------|----------|------|
| CLAUDE / AGENTS | how-to | always |
| `apps/*/CLAUDE.md` + `apps/*/docs/` | how-to + reference | on_demand (per-app pack, phase4b) |
| llms.txt / INDEX | reference | always |
| TAXONOMY / MODULE_MAP / API_SURFACE / TEST_INDEX | reference | on_demand |
| ARCHITECTURE / FLOWS / gotchas / ADR | explanation | on_demand |
| RUNBOOK / TESTING / deployment | how-to | on_demand |
| DESIGN (`has_ui`) | reference | on_demand |

## Deep pipeline

```text
Phase0 seed
  → Pass A (model): Phase1–4 root pack
  → Host: onboard_app_packs prepare (skeletons + project API_SURFACE → apps/*)
  → Pass B (model): Phase4b fill each apps/* + Phase5
  → Host: VALIDATION gate (fail thin/catch-all packs)
  → report
```
Deep monorepo (≥2 apps) uses this **two-pass pipeline**. Toy/single-app stays single-pass.

## Signals

| Signal | Extra files |
|--------|-------------|
| `has_ui` | `docs/DESIGN.md` (Google format) |
| `has_deploy` / `signals.deploy` | `docs/RUNBOOK.md` |

## MUST (PM)

1. Passport thin: spawn **project-onboarder** (or `project-onboard`). Wait `DONE`.
2. If `stages.docs.enabled`: then spawn **docs-maintainer**. Never both at once.
3. Writer reads skill `references/`.
4. After: RU summary — surfaces, modules, tests, DESIGN?, RUNBOOK?, validation.

## After checklist

- [ ] PACK-SCHEMAS followed  
- [ ] VALIDATION green or GAPS listed  
- [ ] TAXONOMY / API_SURFACE / MODULE_MAP / TEST_INDEX real  
- [ ] MODULE_MAP covers apps (+ runners/hot libs) or GAPS  
- [ ] Phase4b: each `apps/*` walked → **filled** local CLAUDE + docs/ (not stubs; surfaces projected/split)  
- [ ] Webhooks split per provider; auth unknown ≤40%  
- [ ] MANIFEST always_load lean (CLAUDE/AGENTS/INDEX only)  
- [ ] decisions.md 3–5 evidenced ADRs (deep full) or GAPS  
- [ ] FLOWS notification includes stream handler + queue consumer when present  
- [ ] has_ui ⇒ DESIGN Google format  
- [ ] has_deploy ⇒ RUNBOOK  
- [ ] phase artifacts + report under `.agents/runs/_onboard/artifacts/001`  
- [ ] MANIFEST weekly refresh  

