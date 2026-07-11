# Routing profiles

**PM is always Claude Code** (`dev-orchestrator`).

| Profile | Requires | Write | Review |
|---------|----------|-------|--------|
| `full` | AGY + Grok + Codex | AGY fast, Grok main | Codex |
| `claude-codex` | Codex | Codex | Codex |
| `claude-agy` | AGY | AGY | Claude reviewer agent |
| `claude-grok` | Grok | Grok | Claude reviewer agent |
| `claude-only` | — | Claude subagents | Claude reviewer |

Generate for your machine:

```bash
agents-doctor --apply .
# → .agents/capabilities.json
# → .agents/routing.profile.yaml
```
