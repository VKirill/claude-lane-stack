# MCP — Model Context Protocol in Codex

Same protocol as Claude Code and OpenCode. Same server binaries. Only the config format differs (TOML).

## Configuration

In `~/.codex/config.toml` or `<project>/.codex/config.toml`:

```toml
[mcp_servers.filesystem]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", "/home/me/projects"]

[mcp_servers.github]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-github"]
env = { GITHUB_TOKEN = "${GITHUB_TOKEN}" }

[mcp_servers.postgres]
command = "node"
args = ["./tools/pg-mcp.js"]
env = { DATABASE_URL = "${DATABASE_URL}" }

[mcp_servers.remote-search]
url = "https://mcp.example.com/sse"
headers = { Authorization = "Bearer ${MCP_TOKEN}" }
```

## Transports

| Transport | When | TOML fields |
|---|---|---|
| stdio (default) | Local subprocess | `command`, `args`, `env` |
| HTTP / SSE | Remote | `url`, `headers` |

## Add via wizard

```bash
codex mcp add
```

Prompts for server name, transport, command/url, env vars; writes the TOML block. Recommended for sensitive servers — gets the escaping right.

## List & test

```bash
codex mcp list
codex mcp test github
```

In TUI: `/mcp`.

## Common servers

Same catalog as Claude Code / OpenCode:

| Server | npm package |
|---|---|
| filesystem | `@modelcontextprotocol/server-filesystem` |
| github | `@modelcontextprotocol/server-github` |
| postgres | `@modelcontextprotocol/server-postgres` |
| brave-search | `@modelcontextprotocol/server-brave-search` |
| serena | external |
| tavily | external |

## Sandbox interaction

MCP server processes run **outside** Codex's Rust sandbox — the sandbox only constrains Codex's own tool invocations. An MCP server can do anything its own process is allowed to do. Implication: vet MCP servers as carefully as you'd vet any dependency.

## Debugging

```bash
codex --debug
codex mcp test <name>
```

Common failures:

| Symptom | Likely cause |
|---|---|
| Server greyed out in `/mcp` | Handshake failed |
| "no tools" | Server didn't implement `list_tools` |
| Auth error | `${ENV_VAR}` typo or env not exported |
| Server times out | Stdio blocking on tty read |

## Security

MCP output is **untrusted context** — Codex injects it as user-content. Prompt-injection mitigations still required. Pin server versions where supported (`@modelcontextprotocol/server-X@1.2.3`).
