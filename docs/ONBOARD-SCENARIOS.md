# Onboard scenarios + Diátaxis LLM pack

## Axes

| Axis | Values |
|------|--------|
| Scenario | `minimal` \| `full` |
| Depth | `fast` \| `deep` |
| UI | `has_ui` → `docs/DESIGN.md` |
| Deploy | `has_deploy` → `docs/RUNBOOK.md` |
| Refresh | `weekly` via docs-maintainer |
| Taxonomy | [Diátaxis](https://diataxis.fr/) in `docs/llm/TAXONOMY.yaml` (**no tutorials**) |

## Standards

AGENTS.md · Claude lean memory · llms.txt · Diátaxis · `@google/design.md` · structured YAML indexes

## Pack

| Path | Diátaxis |
|------|----------|
| `docs/llm/TAXONOMY.yaml` | reference (classifier) |
| `docs/llm/API_SURFACE.yaml` | reference — all public APIs |
| `docs/llm/MODULE_MAP.yaml` | reference — module contracts |
| `docs/llm/TEST_INDEX.yaml` | reference — command → proves |
| `docs/llm/FLOWS.md` | explanation |
| `docs/ARCHITECTURE.md` | explanation |
| `docs/RUNBOOK.md` | how-to (deploy) |
| `docs/DESIGN.md` | reference (UI, Google format) |

## Deep pipeline

```text
layout (+ TAXONOMY) → maps (MODULE_MAP + API_SURFACE + TEST_INDEX)
  → flows → passport (+ DESIGN/RUNBOOK) → per-app packs (apps/*/CLAUDE+docs)
  → VALIDATION → report
```

## One-shot CLI

```bash
project-onboard .                 # full: auto-detect + seed + Codex/Cursor fill
project-onboard . --seed-only     # stubs only
ONBOARD_DRY_RUN=1 project-onboard .   # wire-check without calling the model
```

## Weekly

```bash
ONBOARD_REFRESH=weekly  # docs-maintainer ≈ 7 days
```

