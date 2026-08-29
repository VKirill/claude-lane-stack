# Module: services-data

## Purpose
Single place to attach SEO data APIs used by all other modules.

## Protocol
1. `seo-services` TUI or `seo-services set <id> KEY=VAL`
2. enable + test
3. `seo-services export` → `~/secrets/seo-tools.env`
4. Optional: `seo-services project-wire` in client repo

## Providers
xmlstock · xmlriver · mutagen · dataforseo · **proxy6** · yandex_* · gsc · ga4

## Related tabs in seodoc
- **Proxy** — pool from proxy6 getproxy
- **Agents** — per-stage CLI/agent routing
- **Cluster** — SERP provider / TOP-N / temperature
- **Embed** — openai | gemini for embeddings

## Doc
`~/.agents/docs/seo/SEO-SERVICES-TUI.md`

## DataForSEO official MCP

Native server: `dataforseo-mcp-server` (https://github.com/dataforseo/mcp-server-typescript)

- Install path: `~/.agents/mcp/dataforseo-mcp-server`
- Launcher: `seo-dataforseo-mcp` (loads `~/secrets/dataforseo.env` from seodoc)
- Claude MCP name: `dataforseo` in `~/.claude.json`
- Credentials: set in **seodoc** → DataForSEO (LOGIN + PASSWORD → USERNAME/PASSWORD for MCP)

After saving creds in TUI, restart Claude session so MCP process picks env.

