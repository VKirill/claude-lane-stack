# Project layout: `.agents/seo/`

File-based SEO control plane per project (mirrors `.agents/runs/` for code, but for SEO research and execution).

## Tree

```text
.agents/seo/
  BOARD.md                          # optional global board across projects
  <project-slug>/
    PROJECT.md                      # identity: domain, markets, owners, goals
    STATUS.md                       # phase, blockers, next action (English)
    BOARD.md                        # live SEO task board for this project
    passport/
      project-passport.md           # Collector + Validator output
      gaps.md                       # missing data + how to collect
      sources.md                    # URLs, exports, API property ids
    discovery/
      01-niche.md
      02-demand.md
      03-audience.md
      04-serp-reality.md
      05-entities-trust.md
      06-ai-search.md
      intent/
        latent/                     # per-query Latent Intent outputs
        classifier/                 # Search Intent Classifier batches
      raw/                          # optional intermediate LLM dumps
    strategy/
      01-strategy.md                # Q* vs NavBoost, cocoons, milestones
      backlog.yaml                  # prioritized work items
      cocoons/                      # per-cocoon topology notes
    technical/
      audit.md                      # T-E-E-A / technical findings
      fixes.yaml                    # concrete fix list
    content/
      plan.md
      clusters/                     # cluster → page job maps
      pages/<url-slug>/
        brief.md
        gist-plan.md
        draft.md
        cvd.md
        humanized.md
        meta.md
        schema.json
      reviews/
    offpage/
      link-plan.md
      listicle/
      entity-footprint/
      brand-poisoning/
    measurement/
      baseline.md
      hypotheses.md
      gsc/ ga4/ metrica/            # dated exports or query receipts
    evidence/
      serp/<date-region>/           # SERP dumps
      exports/                      # GSC CSV, etc.
    prompts-used/
      log.tsv                       # date, system, version path, model, artifact path
    runs/
      <run-slug>/
        PLAN.md
        STATUS.md
        tasks/
          001-….yaml                # optional bridge to code workers
        artifacts/
```

## Language

| Surface | Language |
|---|---|
| Chat with human | Russian (default) |
| `STATUS.md`, `BOARD.md`, task YAML, technical filenames | English preferred |
| Client-facing strategy prose | RU or EN per client |
| Leak signal tokens | English (`NavBoost`, `contentEffort`, …) |

## `prompts-used/log.tsv`

```tsv
date	system	version_path	model	phase	artifact
2026-08-07	GIST Content Logic	originals/…/GIST Content Logic Skill-v-3-3.md	claude-opus	content	content/pages/foo/gist-plan.md
2026-08-07	LinguaForensic	…/83/AI-detect-v-3-9-4-full.md	claude-sonnet	content	content/pages/foo/detect.md
```

## Status fields (STATUS.md)

```markdown
# STATUS — <project-slug>
phase: passport|discovery|strategy|technical|content|offpage|measure
updated: YYYY-MM-DD
blockers: …
next: …
markets: RU|EN|…
search_engines: google|yandex|both
```

## Promotion to code

When a fix needs repository changes:

1. Write acceptance criteria under `technical/fixes.yaml` or `content/...`
2. Create `.agents/seo/<project>/runs/<slug>/` with PLAN
3. Either implement via SEO agent (content files only) or hand `dev-orchestrator` a run under project `.agents/runs/` with `owns_paths`
