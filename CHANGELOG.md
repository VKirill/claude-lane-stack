# Changelog

## Unreleased (local)

### Changed
- **Language policy**: all agent-written files English; chat with human Russian (`docs/LANGUAGE.md`).

### Fixed
- **lane-exec**: activity-aware timeouts (idle resets on stdout/CPU; absolute max). Replaces hard `timeout 570` in implementers so thinking agents are not killed mid-run.

### Added
- **Dual onboard scenarios** (`minimal` vs `full`):
  - Auto maturity score in `project-onboard` → `.agents/onboard.scenario.yaml`
  - Override: `--minimal` / `--full` or `ONBOARD_SCENARIO=`
  - Full seeds: GOTCHAS, GLOSSARY, TESTING, deployment, nested `apps/*/CLAUDE.md`, optional SECURITY
  - Skip seed when case-insensitive sibling exists (`gotchas.md` vs `GOTCHAS.md`)
  - Docs: `docs/ONBOARD-SCENARIOS.md`; Codex `onboard.md` + `docs-maintain` scenario-aware
  - Templates: `GOTCHAS.md`, `GLOSSARY.md`, `TESTING.md`, `deployment.md`

- **GPT-5.6 routing** (Sol / Terra / Luna): no GPT-5.5. See `docs/ROUTING.md`, `profiles/claude-codex.yaml`.
  - Write default: **terra** (+ xhigh medium); high-risk: **sol** xhigh
  - Review/ship: **sol** xhigh
  - Onboard / docs-maintain: **terra** high
  - Luna: trivia only, not default lanes
- **Onboard** seeds `docs/ARCHITECTURE.md` + README anamnesis pattern; Codex fills from evidence.
- **docs-maintainer**: `docs-maintain-project`, `docs-maintain-all`, skill + `codex-docs-maintainer` agent.
- Templates: `ARCHITECTURE.md`, `README.anamnesis.md`.

### Fixed
- AGY: ban `call_mcp_tool` / `inheritMcp` on lane agents; agy-implementer preflight.

## 0.1.0
- Initial public package (file contracts, solo merge, beginner guides).
