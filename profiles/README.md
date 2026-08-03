# Routing profiles

**PM is always Claude Code** (`dev-orchestrator`, Fable/Opus).

**Write programmer is switchable: Kimi (default), Qwen, Grok, or AGY 3.6.** Claude's `run-supervisor` is source-read-only
and can issue only typed `run-controller` actions. `lane-supervisor` remains the
typed one-lane diagnostic profile.

| Profile | Aux CLIs | Write | Review |
|---------|----------|-------|--------|
| `full` | Kimi + Qwen + Grok + AGY + Codex | **Kimi** (Qwen/Grok/AGY/**Codex luna+max** selectable) | Codex **sol** |
| `claude-qwen` | Qwen | Qwen | Claude reviewer |
| `claude-kimi` | Kimi | Kimi K3-256k | Claude reviewer |
| `claude-agy` | AGY | AGY | Claude reviewer |
| `claude-codex` | Codex only | **terra** (sol if high risk) | **sol** |
| `claude-grok` | Grok | Grok | Claude reviewer |
| `claude-only` | — | Claude Sonnet/Opus workers | Claude |

GPT-5.6 only on Codex: **sol** · **terra** · **luna** (optional trivia). **No 5.5.**

```bash
# New / existing project — full-screen TUI (tabs, toggles)
cd your-project && agents-doctor
# same: agents-doctor tui .

# Linear wizard (no full-screen)
agents-doctor setup .

# Non-interactive
agents-doctor setup . --yes --writer-provider qwen --night-review off
agents-doctor setup . --yes --writer-provider codex --night-review off   # gpt-5.6-luna + effort max
agents-doctor --apply --writer-provider qwen --night-review on --max-fix-tasks 5 .

# → .agents/routing.profile.yaml (+ .agents/night-shift.yaml when night flags used)
```

Without a project profile the orchestrator defaults to **kimi**. Always run setup (or `--apply --writer-provider …`) once per repo.

See `docs/ROUTING.md`.
**Codex programmer (`main_write: codex`):** bare profile
`profiles/codex/lane-writer.config.toml` — no host MCP, no plugins, no user
skills. Ephemeral `CODEX_HOME` = auth + that config; host `~/.codex` masked in
bubblewrap. Model default: `gpt-5.6-luna` + effort `max`.
