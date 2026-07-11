# Lean MCP profile

## Active global (agy / gemini / .agents)

| ON | Role |
|----|------|
| gitnexus | code graph |
| context7 | library docs |
| perplexity | web research |
| shadcn | UI components |

## Removed / never auto-start

- **orchestrator-mcp** — file runs/todos instead
- **repowise** — removed everywhere (use gitnexus)
- **agent-consult** — removed everywhere
- open-design, chrome-devtools, image-gen, agentmemory, postgres, tavily, vue-docs, nuxt-ui, mcp-books, studio-*, serena

## Codex

ON: gitnexus, context7. Heavy servers commented out in `~/.codex/config.toml`.

## Claude settings

mcpServers: no repowise / agent-consult. repowise hooks disabled (*.sh.disabled).

## Re-enable

Only if explicitly needed: restore from `*.bak-lean-mcp-*` or re-add to mcp_config.json.
\
## Superseded by hybrid MetaMCP

See [MCP-HYBRID.md](./MCP-HYBRID.md) — hosts use agentmemory + gitnexus + metamcp only.
