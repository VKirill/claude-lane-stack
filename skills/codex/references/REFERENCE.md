# codex — Reference Index

| If you want to... | Open |
|---|---|
| Install, auth (ChatGPT or API key), pick a model | [installation.md](installation.md) |
| Look up a CLI flag (`-s`, `-a`, `--full-auto`, `--profile`) | [cli-flags.md](cli-flags.md) |
| Edit `config.toml` (profiles, model, sandbox) | [config.md](config.md) |
| Run a slash command or author a custom prompt | [commands.md](commands.md) |
| Use profiles like subagents | [subagents.md](subagents.md) |
| Configure MCP servers | [mcp.md](mcp.md) |
| Understand sandbox modes + approval policies | [permissions.md](permissions.md) |
| Run headless in CI, use `codex app-server` | [interop.md](interop.md) |
| Migrate config from Claude Code or OpenCode | [migration.md](migration.md) |
| Verify routing (positive/negative/edge tests) | [eval-cases.md](eval-cases.md) |

## Quick patterns

**Safe default for unfamiliar repos:**
```bash
codex -s read-only -a untrusted
```

**Productive default:**
```bash
codex --full-auto
```

**Headless one-shot in CI:**
```bash
codex exec "Review the diff. Reply 'OK' or list concerns." -s read-only -a never --json
```

**Profile usage:**
```bash
codex -p review     # uses [profiles.review] from config.toml
```

**Disambiguation reminder**: modern Codex is the agentic CLI tool. The 2021-era `code-davinci-002` model is discontinued.
