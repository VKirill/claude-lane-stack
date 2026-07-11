# Changelog

## Unreleased (local)

### Fixed
- **lane-exec**: activity-aware timeouts (idle resets on stdout/CPU; absolute max). Replaces hard `timeout 570` in implementers so thinking agents are not killed mid-run.

### Added
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
