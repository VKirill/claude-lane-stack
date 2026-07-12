# Changelog

## Unreleased

### Added
- **Tiered review policy**: none for micro/low, pinned `opencode-reviewer` (`openrouter/z-ai/glm-5.2`) for medium, and unchanged Codex Sol xhigh for high-risk/ship; micro commits now include `[micro:<slug>]`.
- **Micro path tier** (score 0–2): skips PLAN/worktree/board/heartbeat/reviewer for trivial ≤2-file changes; adds `verify` field (`none`|`smoke`|`tests`) to the task YAML contract. See `docs/ROUTING.md`, `docs/SOLO-ORCHESTRATION.md`, `docs/FILE-CONTRACT.md`.
- **Run-scoped warm AGY/Grok sessions**: `lane-session` resumes native conversations across related tasks, preserves up to three parallel slots, rotates after seven successful tasks by default (hard max ten), and invalidates failed/stale sessions.
- AGY preflight smoke is cached by CLI version and agent-definition hash instead of spending a model call before every task.

### Fixed
- Provider output is streamed through `lane-exec` for correct idle detection; interrupted lanes terminate the complete provider process group before releasing a session slot.

## 1.1.0 — 2026-07-11

Deep onboard, dual scenarios, activity-aware lanes, and Claude Bash background survival.

### Docs
- Full refresh of README (EN/RU) + v1.1.0 blocks on all locale READMEs; BEGINNER EN/RU + locale notes; ROUTING/LANE-EXEC/ONBOARD/COMPARISON/PROJECT-MEMORY/FILE-CONTRACT/llms.txt/install.sh aligned to current product.

## 1.1.0 details

### Changed
- **Language policy**: all agent-written files English; chat with human Russian (`docs/LANGUAGE.md`).

### Fixed
- **Lane background under Claude Bash**: long `lane-exec`/`agy`/`grok`/`codex` must use **`lane-bg`** + poll **`lane-wait --once`**. Foreground Bash is killed ~2 minutes by the host (not lane-exec idle/max). Implementers + dev-orchestrator + LANE-EXEC updated.
- **lane-exec**: activity-aware timeouts (idle resets on stdout/CPU; absolute max). Replaces hard `timeout 570` in implementers so thinking agents are not killed mid-run.

### Added
- **Onboard depth** `fast` | `deep` (default: full→deep, minimal→fast):
  - Forensic deep checklist in Codex `onboard.md` (entrypoints, flows, wiki↔code, verify, ship, secrets)
  - Auto `deep-scan.md` evidence pack under `.agents/runs/_onboard/artifacts/001/`
  - Flags: `--deep` / `--fast`, `ONBOARD_DEPTH=`, `/project-onboard deep`
  - Nested deploy detect (maxdepth 3 compose/Dockerfile) for maturity score
  - Deep uses **gpt-5.6-sol** high; fast uses terra high
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
