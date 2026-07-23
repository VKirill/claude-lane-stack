# Routing profiles

**PM is always Claude Code** (`dev-orchestrator`, Fable/Opus).

**Write programmer is switchable: Qwen (default), Grok, or AGY 3.6.** Claude's `run-supervisor` is source-read-only
and can issue only typed `run-controller` actions. `lane-supervisor` remains the
typed one-lane diagnostic profile.

| Profile | Aux CLIs | Write | Review |
|---------|----------|-------|--------|
| `full` | Qwen + Grok + AGY + Codex | **Qwen** (Grok/AGY selectable) | Codex **sol** |
| `claude-qwen` | Qwen | Qwen | Claude reviewer |
| `claude-agy` | AGY | AGY | Claude reviewer |
| `claude-codex` | Codex only | **terra** (sol if high risk) | **sol** |
| `claude-grok` | Grok | Grok | Claude reviewer |
| `claude-only` | — | Claude Sonnet/Opus workers | Claude |

GPT-5.6 only on Codex: **sol** · **terra** · **luna** (optional trivia). **No 5.5.**

```bash
agents-doctor --apply .
# → .agents/routing.profile.yaml
```

See `docs/ROUTING.md`.
