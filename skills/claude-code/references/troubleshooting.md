# Troubleshooting — claude-code

Symptom-indexed. Find what you see, follow diagnosis, apply fix.

---

## Hook is configured but never fires

**Symptoms**
- `.claude/settings.json` has a hook entry; `claude` runs Edit/Write but no hook output appears
- No error message — silent no-op

**Diagnose**
```bash
# 1. Confirm settings.json is valid JSON
jq . .claude/settings.json

# 2. Confirm settings precedence — local overrides project, project overrides user
claude --debug 2>&1 | grep -i 'settings\|hook'

# 3. Match the event name exactly (case-sensitive)
# Valid: PreToolUse, PostToolUse, UserPromptSubmit, Stop, SessionStart,
#        SubagentStart, Notification, PreCompact
```

**Common causes**
- Event name typo (e.g., `PreToolCall` instead of `PreToolUse`)
- Hook in `~/.claude/settings.json` overridden by empty `hooks: {}` in project settings
- Matcher doesn't match (e.g., `matcher: "Edit"` requires the tool to be exactly `Edit`, not `Write`)
- Hook command exits non-zero on parse — Claude Code swallows the error in non-debug mode

**Fix**
- Run `claude --debug` and watch the hook lifecycle line for the event in question
- Confirm matcher with a deliberately-broad `matcher: ".*"` to isolate
- Make the hook command print to stderr on entry: `echo "hook fired" >&2`

See `references/hooks.md` for event names and JSON contract.

---

## MCP server not connecting (handshake fails)

**Symptoms**
- `/mcp` shows server status "error" or "disconnected"
- `claude --debug` logs `MCP server <name> exited with code <n>` or `handshake timeout`

**Diagnose**
```bash
# 1. Run the MCP server command manually and confirm it speaks MCP on stdio
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | <your-mcp-command>

# 2. Check timeout — default 30s, some heavy servers (serena indexing) need longer
# 3. Confirm command path resolves (PATH issue when launched as subprocess)
which <command>
```

**Common causes**
- Command not in `PATH` of the spawned subprocess (especially with `uvx`, `npx` first-runs)
- Server uses HTTP transport but registered as stdio (or vice versa)
- Server crashes on startup (missing dep, missing env var)
- `cwd` not set; server expects to be launched from project root

**Fix**
- Use absolute paths in `command`
- Add `env` block in the MCP server entry with required vars
- Bump `timeout` to 60000 ms for first-time `uvx`/`npx` cold installs
- See `references/recommended-defaults.md` for canonical MCP block

---

## Skill not activating when expected

**Symptoms**
- User prompt matches the skill's `description` keywords but skill doesn't load
- System reminder doesn't list the skill

**Diagnose**
1. Check skill location — `~/.claude/skills/<name>/SKILL.md` (user) or `.claude/skills/<name>/SKILL.md` (project)
2. Validate frontmatter: `name` matches directory, `description` is non-empty
3. Confirm `description` has trigger terms a model would match — see `skill-evaluation` skill for description engineering
4. Try a more on-point prompt that uses the exact trigger terms

**Common causes**
- `name` in frontmatter doesn't match directory name
- `description` too generic — competing skills win the routing
- Skill file has YAML parse error — Claude Code skips silently
- Skill is in `.claude/skills/` but the working directory is elsewhere — project-level skills are dir-scoped

**Fix**
- Run `claude /skills` to list loaded skills
- Tighten description per the `skill-evaluation` skill (trigger terms + SKIP rules)
- Move to user-global location if cross-project: `~/.claude/skills/<name>/`

---

## settings.json precedence confusion

**Symptoms**
- Change in `~/.claude/settings.json` has no effect
- Or change in `.claude/settings.local.json` not picked up
- Two settings files seem to fight

**Precedence (most-specific wins)**
1. `.claude/settings.local.json` (project, user-private)
2. `.claude/settings.json` (project, committed)
3. `~/.claude/settings.json` (user-global)
4. Built-in defaults

**Diagnose**
```bash
claude --debug 2>&1 | grep -i 'resolved settings\|loaded settings'
```

**Common cause**
- Trying to set a deny rule in `~/.claude/settings.json` while project has its own `permissions.deny` array — the project array **replaces**, not merges
- `.claude/settings.local.json` accidentally committed and read on another machine

**Fix**
- Keep user-global settings minimal — MCP servers + theme; project-specific in repo settings
- Confirm `.claude/settings.local.json` is in `.gitignore`

---

## Permission denied unexpectedly

**Symptoms**
- Claude says "blocked by permissions" for a tool you expected to be allowed
- `Bash(npm test)` works but `Bash(npm test -- --watch)` blocked

**Common causes**
- Matcher is glob-strict: `Bash(npm test:*)` (with `:*`) allows arguments; `Bash(npm test)` does not
- Project-level `permissions.allow` is empty array → blocks everything (use `null` or omit to inherit)
- A `PreToolUse` hook returned `{"decision":"block"}` and the reason was suppressed

**Fix**
- Use `:*` suffix for tools that take arguments: `Bash(npm test:*)`, `Edit(src/**)`
- For files: `Edit(src/**)` matches `src/a.ts` and `src/sub/b.ts`
- Check hook output: `claude --debug` shows hook decisions

See `references/permissions.md` and `references/recommended-defaults.md` for canonical matcher patterns.

---

## `claude update` fails

**Symptoms**
- `claude update` exits non-zero
- New release announced but local CLI still old

**Diagnose**
```bash
claude --version
# Compare to https://github.com/anthropics/claude-code/releases (or `npm view @anthropic-ai/claude-code version`)

# If installed via npm:
npm i -g @anthropic-ai/claude-code@latest

# If installed via native installer:
curl -fsSL https://claude.ai/install.sh | bash
```

**Common causes**
- Mixed install paths — npm version coexists with native binary; `which claude` shows surprise location
- Permission issue on the install dir (npm global on macOS w/o nvm)
- Network egress blocks downloading binary asset

**Fix**
- Pick one install path; remove the other
- For npm: use `nvm` or fix npm global prefix to a user-owned dir
- For native: ensure `~/.local/bin` (or wherever installer puts it) is in `PATH`

---

## More symptoms?

Capture: `claude --version`, `claude --debug` output during repro, contents of all three settings.json files (redacted), and platform (`uname -a`). Open an issue at <https://github.com/anthropics/claude-code/issues> with that bundle.
