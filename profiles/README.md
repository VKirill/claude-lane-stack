# Routing profiles

**PM is always Claude Code** (`dev-orchestrator`, Fable/Opus).

**Write programmer is Grok only.**

| Profile | Aux CLIs | Write | Review |
|---------|----------|-------|--------|
| `full` | Grok + Codex | **Grok** | Codex **sol** |
| `claude-codex` | Codex only | **terra** (sol if high risk) | **sol** |
| `claude-grok` | Grok | Grok | Claude reviewer |
| `claude-only` | — | Claude Sonnet/Opus workers | Claude |

GPT-5.6 only on Codex: **sol** · **terra** · **luna** (optional trivia). **No 5.5.**

```bash
agents-doctor --apply .
# → .agents/routing.profile.yaml
```

See `docs/ROUTING.md`.
