---
name: metamcp
description: Hybrid MetaMCP gateway — agentmemory + gitnexus direct; all other MCP tools via MetaMCP discover/call
---

# MetaMCP (hybrid)

## Layout

| Host-level (direct) | Behind MetaMCP (`~/.agents/metamcp.mcp.json`) |
|---------------------|-----------------------------------------------|
| **agentmemory** | context7, postgres, github, shadcn |
| **gitnexus** | open-design, chrome-devtools, vue-docs |
| **metamcp** | mcp-books, perplexity, image-gen |
| | remotion-documentation, codex-mcp-server |

**Never behind MetaMCP (removed):** `orchestrator-mcp`, `agent-consult`, `repowise`.

Launcher: `/home/ubuntu/.agents/bin/metamcp-run`  
Config: `/home/ubuntu/.agents/metamcp.mcp.json`  
Env secrets: `/home/ubuntu/.agents/metamcp.env` (600)

## MetaMCP tools (`@mentu/metamcp@0.4.1` → 4 tools)

1. `mcp_discover` — search tools / list servers (first call can cold-start many children — prefer `mcp_call` when you know the server)
2. `mcp_provision` — resolve capability → server  
3. `mcp_call` — call a child tool (**prefer this**)  
4. `mcp_execute` — multi-step JS sandbox over servers  

> 0.5.x docs mention skill tools; installed 0.4.1 exposes the four core tools only.

## How to call (examples)

**Direct (no MetaMCP):**
- `mcp__agentmemory__memory_recall` / `memory_remember` / …
- `mcp__gitnexus__impact` / `query` / `context` / `detect_changes`

**Via MetaMCP:**
```
mcp_discover { "query": "screenshot" }
mcp_call {
  "server": "chrome-devtools",
  "tool": "take_screenshot",
  "args": { ... }
}
```

```
mcp_call {
  "server": "github",
  "tool": "<tool_name>",
  "args": { ... }
}
```

```
mcp_call {
  "server": "perplexity",
  "tool": "perplexity_search",
  "args": { "query": "..." }
}
```

```
mcp_call {
  "server": "context7",
  "tool": "resolve-library-id",  # or docs tool name from discover
  "args": { ... }
}
```

## Rules

1. Prefer **direct** gitnexus + agentmemory — do not route them through MetaMCP.
2. For anything else: `mcp_discover` once if unsure, then `mcp_call`.
3. Do not invent host-level MCP servers; add children only in `metamcp.mcp.json`.
4. After editing child config, restart CLI sessions (hot-reload may apply inside MetaMCP only).

## Install / smoke

```bash
# package
npm i -g @mentu/metamcp
# or: npx @mentu/metamcp --config ~/.agents/metamcp.mcp.json

# smoke
~/.agents/bin/metamcp-run   # should speak MCP on stdio
```
