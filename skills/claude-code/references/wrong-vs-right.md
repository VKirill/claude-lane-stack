# Wrong vs Right — claude-code

Side-by-side contrast for common Claude Code footguns. Both sides keep under 15 lines so the point lands quickly.

---

### Hook decision: blocking vs annotating

**❌ Wrong — non-safety hook returns blocking decision, breaks productivity:**

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Edit",
      "hooks": [{
        "type": "command",
        "command": "prettier --check $CLAUDE_FILE_PATH || echo '{\"decision\":\"block\",\"reason\":\"prettier failed\"}'"
      }]
    }]
  }
}
```

**✅ Right — formatter hook fixes in place, never blocks:**

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Edit",
      "hooks": [{ "type": "command", "command": "prettier --write $CLAUDE_FILE_PATH" }]
    }]
  }
}
```

**Why it matters:** `PreToolUse` is for hard safety gates (block `rm -rf`, block edits to `.env`). `PostToolUse` is for fix-up — running a formatter and blocking the edit causes Claude to retry the same edit repeatedly, burning tokens. Format in place; if you must signal a problem, write to stderr and let the next pass see the file's state.

---

### settings.json: local override vs broken project settings

**❌ Wrong — committing `.claude/settings.local.json` and letting it diverge from project settings:**

```bash
# .gitignore — missing entry
# .claude/settings.local.json — committed
{
  "permissions": { "allow": ["Bash(*)"] }  # disables all project denies for everyone
}
```

**✅ Right — `.local.json` is user-private; project settings carry the contract:**

```bash
# .gitignore
.claude/settings.local.json

# .claude/settings.json — committed, the team contract
{
  "permissions": { "deny": ["Bash(rm -rf:*)", "Edit(.env*)"] }
}
```

**Why it matters:** `.claude/settings.local.json` is **user-private overrides**, not team configuration. If it's committed, one developer's `acceptEdits` accidentally becomes the team's policy. The deny rules in `.claude/settings.json` are the team contract — `.local.json` lets each developer relax them for their own sandbox.

---

### MCP server allowlist: explicit vs wildcard

**❌ Wrong — wildcard allow on sandbox network:**

```json
{
  "sandbox": {
    "network": {
      "deniedDomains": [],
      "allowedDomains": ["*"]
    }
  }
}
```

**✅ Right — default-deny, explicit allowlist:**

```json
{
  "sandbox": {
    "network": {
      "deniedDomains": ["*"],
      "allowedDomains": [
        "api.anthropic.com",
        "registry.npmjs.org",
        "github.com"
      ]
    }
  }
}
```

**Why it matters:** Claude Code's MCP servers (especially community ones) can exfiltrate context to attacker-controlled domains if a prompt-injection lands. Default-deny + explicit allowlist is the cheap defense. Wildcard allow makes the sandbox decorative.

---

### Permission matcher: argument-bearing tool

**❌ Wrong — matcher misses argument variants:**

```json
{ "permissions": { "allow": ["Bash(npm test)"] } }
```
This allows literally `npm test` and nothing else. `npm test -- --watch` is blocked.

**✅ Right — `:*` suffix permits arguments:**

```json
{ "permissions": { "allow": ["Bash(npm test:*)"] } }
```

**Why it matters:** Without `:*`, the matcher requires an exact string match. Every CI flag, every `--watch`, every extra arg blocks. This is the #1 cause of "permission prompts I thought I configured away."

---

### CLAUDE.md size: lean vs bloated

**❌ Wrong — 1500-line CLAUDE.md with full architecture docs inline:**

CLAUDE.md gets injected at every session start. A 1500-line file burns context before Claude has read your prompt.

**✅ Right — under 500 lines; defer detail to docs/:**

```md
# CLAUDE.md

Stack, ports, commands → see PROJECT.md
Architecture diagram → see docs/architecture.md
API conventions → see docs/api.md

## Conventions (the only thing Claude needs at session start)
- Always run `npm run lint` before committing
- Treat `.env*` as forbidden
...
```

**Why it matters:** CLAUDE.md is "what Claude must remember on every turn", not "everything about the project". Lean CLAUDE.md + pointers to docs/ keeps the working context budget for the actual task.
