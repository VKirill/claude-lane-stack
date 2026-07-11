---
name: antigravity
description: "Antigravity CLI (agy) file-lane executor. Agents in ~/.agents/agy/agents. Use when: agy, lane-coder, lane-frontend, headless print. SKIP: Codex review, Grok CLI, pure Claude coding."
---

# Antigravity (agy) — file lanes

Binary: `agy` (≥ 1.1.1).  
Agents source: `~/.agents/agy/agents/<name>/agent.md`  
AGY discovery copy: `~/.gemini/config/agents/<name>/agent.md` (must stay in sync).

## Agents

| name | role |
|------|------|
| lane-coder | backend/general write |
| lane-frontend | UI write |
| consult | read-only consult |
| lane-reviewer | emergency review (prefer Codex) |

## Frontmatter tools (critical — agy 1.x)

Write agents **must** list native tools, e.g.:

`write_to_file`, `replace_file_content`, `multi_replace_file_content`, `view_file`, `list_dir`, `grep_search`, `run_command`, `send_message`, …

### Banned (current agy crashes the agent on load)

- **`call_mcp_tool`** in `tools:`  
- **`inheritMcp: true`**

Symptom: `Agent execution terminated due to error` immediately with `--agent lane-*`; bare `agy --print` without `--agent` still works.

Fix:

```bash
# strip banned keys, re-sync
sed -i '/call_mcp_tool/d;/inheritMcp:/d' ~/.agents/agy/agents/<name>/agent.md
cp -a ~/.agents/agy/agents/<name>/agent.md ~/.gemini/config/agents/<name>/agent.md
# smoke (with TASK_FILE path in prompt or dummy yaml)
agy --print "TASK_FILE=/tmp/t.yaml. Reply OK." --agent lane-frontend \
  --mode accept-edits --print-timeout 30s --dangerously-skip-permissions
```

Orientation: use `grep_search` / `view_file` / `run_command` — not MCP inside AGY custom agents.

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
Supervisor: Claude agent `agy-implementer` (preflight smoke + auto-strip banned tools).

## Contracts

Tasks live in project `.agents/runs/<slug>/` — see `~/.agents/docs/FILE-CONTRACT.md`. Not orchestrator MCP.

<!-- changelog-watch:start -->
- 2026-07-11: ban call_mcp_tool/inheritMcp on lane agents (agy executor crash).
<!-- changelog-watch:end -->
