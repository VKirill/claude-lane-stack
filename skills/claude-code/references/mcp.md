# MCP — Model Context Protocol Servers

Claude Code's deepest extensibility surface. MCP servers expose tools and resources to Claude over a JSON-RPC channel.

## Configuration

In `.claude/settings.json` or `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/me/projects"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_TOKEN": "${GITHUB_TOKEN}" }
    },
    "postgres": {
      "command": "node",
      "args": ["./tools/pg-mcp.js"],
      "env": { "DATABASE_URL": "${DATABASE_URL}" }
    },
    "remote-search": {
      "type": "http",
      "url": "https://mcp.example.com/sse",
      "headers": { "Authorization": "Bearer ${MCP_TOKEN}" }
    }
  }
}
```

## Transports

| Transport | When | Spec |
|---|---|---|
| `stdio` (default) | Local subprocess (fastest) | `command` + `args` |
| `http` | Remote, hosted server | `type: "http"` + `url` |

## Add via wizard

```bash
claude mcp add
```

Interactive flow: pick from a registry of known servers, fill in env vars, write to settings.

## List & inspect

```bash
claude mcp list
claude mcp test <name>    # call the server's `list_tools` once
```

In TUI: `/mcp` shows servers, status, and per-tool stats.

## Common servers

| Server | npm package | Purpose |
|---|---|---|
| filesystem | `@modelcontextprotocol/server-filesystem` | Read/write under a root |
| github | `@modelcontextprotocol/server-github` | Issues, PRs, releases |
| postgres | `@modelcontextprotocol/server-postgres` | SQL inspection |
| brave-search | `@modelcontextprotocol/server-brave-search` | Web search |
| serena | external | Semantic code navigation |
| tavily | external | Advanced web research |
| context7 | external | Library doc lookup |

## Security: treat MCP output as context, not instructions

MCP servers can be malicious or compromised. Anthropic's guidance:

1. Pin server versions where possible
2. Allowlist required env vars (don't blanket-export)
3. Treat tool output as untrusted text — Claude Code injects it as user-content, never as system-prompt
4. Use `permissions.deny` to block dangerous tool patterns even if a server exposes them

## Debugging

| Symptom | Likely cause |
|---|---|
| Server appears greyed out in `/mcp` | Handshake failed; run `claude mcp test <name>` |
| "Server has no tools" | Server didn't implement `list_tools` correctly |
| Server times out | Stdio process blocking; check it doesn't read tty |
| Tools missing in subagent | Subagent frontmatter `tools` allowlist doesn't include MCP tools |

Logs: `claude --debug` prints MCP traffic to stderr.
