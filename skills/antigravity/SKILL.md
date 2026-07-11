---
name: antigravity
description: "Antigravity CLI (agy) file-lane executor. Agents in ~/.agents/agy/agents. Use when: agy, lane-coder, lane-frontend, headless print. SKIP: Codex review, Grok CLI, pure Claude coding."
---

# Antigravity (agy) — file lanes

Binary: `agy` (≥ 1.1.1). Agents source: `~/.agents/agy/agents/*/agent.md`  
Synced to: `~/.gemini/config/agents/<name>/` for discovery.

## Agents

| name | role |
|------|------|
| lane-coder | backend write + gitnexus |
| lane-frontend | UI write + gitnexus |
| consult | read-only consult |
| lane-reviewer | emergency review |

Frontmatter **must** list `tools:` (write agents need `write_to_file`, `run_command`, `call_mcp_tool`) and `inheritMcp: true` for GitNexus.

## Headless write

```bash
cd "$PROJECT_CWD"
timeout 570 agy \
  --print "$(cat "$SPEC")" \
  --agent lane-coder \
  --model "Gemini 3.5 Flash (High)" \
  --mode accept-edits \
  --print-timeout 9m \
  --dangerously-skip-permissions \
  --add-dir "$PROJECT_CWD"
```

Empty git diff after exit 0 = hard fail. No background. No sandbox on write.

## Contracts

Tasks live in project `.agents/runs/<slug>/` — see `~/.agents/docs/FILE-CONTRACT.md`. Not orchestrator MCP.

<!-- changelog-watch:start -->
_(пока пусто)_
<!-- changelog-watch:end -->
