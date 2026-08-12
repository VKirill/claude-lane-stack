# Doc layout (LLM agents)

> Phase 1 output. Standards: [AGENTS.md](https://agents.md/) · [llms.txt](https://llmstxt.org/) · [Diátaxis](https://diataxis.fr/) · Claude lean memory · `@google/design.md`.  
> Classifier file: `docs/llm/TAXONOMY.yaml`. Tutorials omitted on purpose.

| Path | Diátaxis | Load | Role |
|------|----------|------|------|
| `CLAUDE.md` | how-to | always | Session ops |
| `AGENTS.md` | how-to | always | Cross-tool entry |
| `llms.txt` / `docs/llm/INDEX.md` | reference | always | Curated map |
| `docs/llm/TAXONOMY.yaml` | reference | on_demand | Classifier |
| `docs/llm/MODULE_MAP.yaml` | reference | on_demand | Module contracts |
| `docs/llm/API_SURFACE.yaml` | reference | on_demand | Public API catalog |
| `docs/llm/TEST_INDEX.yaml` | reference | on_demand | Verify matrix |
| `docs/llm/FLOWS.md` | explanation | on_demand | Critical flows |
| `docs/ARCHITECTURE.md` | explanation | on_demand | Boundaries |
| `docs/DESIGN.md` | reference | on_demand | UI (`has_ui`) |
| `docs/RUNBOOK.md` | how-to | on_demand | Ops (`has_deploy`) |
| `docs/TESTING.md` / `deployment.md` | how-to | on_demand | Verify / ship |
| `docs/gotchas.md` / `decisions.md` | explanation | on_demand | Traps / ADR |
| `.agents/PROGRESS.md` / `.agents/LESSONS.md` | how-to / explanation | on_demand | Living memory |
| `apps/<name>/CLAUDE.md` | how-to | on_demand | Local session rules |
| `apps/<name>/docs/*` | how-to / reference | on_demand | Scoped app passport (phase4b) |

## Rules

- Prefer YAML indexes over wiki essays; no per-function prose catalogs.
- Root `docs/llm/*` = monorepo map. Each real `apps/*` also gets a **scoped** local pack (`CLAUDE` + `docs/`) so agents working in that app load local truth first.
- Local packs must not paste the whole monorepo ARCHITECTURE.
- Weekly: `docs-maintainer` + `ONBOARD_REFRESH=weekly` (refresh app packs when that app’s code changed).
