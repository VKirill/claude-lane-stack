# Changelog

## Unreleased (local, pending push)

### Fixed
- **AGY lane agents crash**: removed `call_mcp_tool` / `inheritMcp` from `lane-coder` and `lane-frontend` (agy 1.x cannot build tool converter).
- **agy-implementer**: mandatory preflight smoke; auto-strip banned tools; fail fast with `STATUS: unavailable` instead of long diagnosis.
- **antigravity skill**: documents ban + sync path `~/.agents/agy` → `~/.gemini/config/agents`.

### Added
- Beginner guides (EN/RU + locales), author/Telegram branding, conveyor visuals.
- `codex-onboarder`, `project-onboard`, file-contract solo merge tooling.
- `agents-doctor` profiles for optional AGY/Grok/Codex.

## 0.1.0
- Initial public package.
