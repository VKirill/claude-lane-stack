# MCP hybrid layout (2026-07-11)

## Goal

Hosts see **3** MCP servers. MetaMCP collapses the rest into **4** tools (`@mentu/metamcp@0.4.1`).

## Host MCP (all CLIs)

1. `agentmemory` — always
2. `gitnexus` — always
3. `metamcp` — gateway → `~/.agents/metamcp.mcp.json`

## CLI config map (verified)

| CLI | Config | Host servers |
|-----|--------|--------------|
| **Claude** | `~/.claude.json` | agentmemory, gitnexus, metamcp |
| **Grok** | `~/.grok/config.toml` | agentmemory, gitnexus, metamcp |
| **Codex** | `~/.codex/config.toml` | agentmemory, gitnexus, metamcp (+ plugin `github@openai-curated` → GitHub Copilot MCP) |
| **OpenCode** | `~/.config/opencode/opencode.json` → `mcp` | agentmemory, gitnexus, metamcp |
| **Mimo** | `~/.config/mimocode/mimocode.json` → `mcp` | agentmemory, gitnexus, metamcp |

## Behind MetaMCP

context7, postgres, github (selfy gateway), shadcn, open-design, chrome-devtools, vue-docs, mcp-books, perplexity, image-gen, remotion-documentation, codex-mcp-server

## Removed from hosts

orchestrator-mcp, agent-consult, repowise

## Project `.mcp.json`

Prefer empty `{"mcpServers":{}}` so projects don't re-add host servers.
Remotion lives only under MetaMCP.

Known intentional project MCP:
- `sites/my_studio/.mcp.json` — studio-scenarios-mcp, studio-db-mcp

## Files

| Path | Role |
|------|------|
| `~/.agents/metamcp.mcp.json` | child catalog |
| `~/.agents/metamcp.env` | secrets (600) |
| `~/.agents/bin/metamcp-run` | launcher |
| `~/.agents/skills/metamcp/SKILL.md` | agent usage |

## Smoke

```bash
metamcp --version
mimo mcp list
codex mcp list
claude mcp list
opencode mcp list
```

## Repowise purge (2026-07-11)

- MCP: never in hybrid hosts / metamcp children
- `pipx uninstall repowise`
- removed `~/.local/bin/repowise*`
- disabled/masked systemd `repowise-sync-all.{timer,service}`
- archived `tools/repowise-codex` under `~/.agents/backups/repowise-purge-*`
- Codex MEMORY banner: do not use Repowise; use GitNexus

## Host-level `chrome-devtools` for `browser-qa` (macOS and Linux desktops)

`browser-qa` prefers a host-level `chrome-devtools` MCP over MetaMCP. Two ways to attach:

| Mode | Command | Dialog | Sees user's tabs |
|------|---------|--------|------------------|
| **`chrome-qa` profile** (recommended) | `chrome-qa start` → `chrome-devtools-mcp --browserUrl http://127.0.0.1:9333` | none | no — separate profile under `~/.agents/chrome-qa` |
| `--autoConnect` | `chrome://inspect/#remote-debugging` → *Allow remote debugging* → `chrome-devtools-mcp --autoConnect` | Chrome asks **on every client connection** | yes — every open tab |

```bash
# recommended: dedicated QA profile, fixed port, no consent dialog
chrome-qa start            # idempotent; CHROME_QA_PORT=9333, CHROME_QA_DIR=~/.agents/chrome-qa
claude mcp add --scope user --transport stdio chrome-devtools -- \
  npx -y chrome-devtools-mcp@latest --browserUrl http://127.0.0.1:9333
```

Log in to test sites inside the `chrome-qa` window once; the profile persists.
Install browser extensions there only when a case needs them. `chrome-qa stop`
closes it. With `--autoConnect` the agent must open its own page (`new_page`),
never touch other tabs and close its pages; Chrome shows the consent dialog each
time the MCP server connects and that cannot be pre-approved on the default profile.
