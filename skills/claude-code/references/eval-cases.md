# claude-code — Eval Cases

v3 format: **user-voice phrasing** (Russian/typos/incomplete welcome) + **Expected behavior** column (which sub-files / templates should load, not just "this skill activates").

## Positive — should activate (10)

| User-voice prompt | Expected behavior |
|---|---|
| "хочу прописать в settings.json hook чтобы prettier запускался после edit" | Load `references/hooks.md` PostToolUse section + cite `templates/settings.json.template`; cross-link `references/recommended-defaults.md` |
| "как добавить mcp сервер в claude code" | Load `references/mcp.md`; show `claude mcp add` and direct settings.json edit; cite `templates/mcp-server.json.template` |
| "запустить claude в github actions для ревью PR" | Load `references/interop.md` headless section + cite `examples/github-actions-pr-review.md` |
| "что делает /loop и /proactive" | Load `references/slash-commands.md` built-in section; clarify `/proactive` is plugin-installed not upstream |
| "сделать subagent для security review" | Load `references/subagents.md`; cite `templates/agent.md.template` with narrow `tools` allowlist |
| "как заблокировать редактирование .env" | Load `references/permissions.md` deny matchers; show `Edit(.env*)` deny rule |
| "claude update не работает" | Load `references/installation.md` update section + `references/troubleshooting.md` |
| "plan mode для рефакторинга без записи" | Load `references/permissions.md` plan-mode section |
| "настроить sandbox.network.deniedDomains" | Load `references/permissions.md` sandbox section; cite `references/recommended-defaults.md` |
| "перенести настройки claude code в opencode" | Load `references/migration.md` mapping table |

## Negative — should NOT activate (10)

| User-voice prompt | Should route to | Why |
|---|---|---|
| "anthropic sdk вызвать claude из python" | `anthropic-sdk` | Raw SDK, not CLI |
| "opencode с bun настроить" | `opencode` | Different CLI |
| "codex exec workspace-write" | `codex` | Different CLI |
| "написать свой mcp server на typescript" | `mcp-builder` | Server authoring, not consumption |
| "SKILL.md Pattern 2 как писать" | `skill-evaluation` | Skill authoring, not CLI |
| "prompt caching в claude api" | `claude-api` | API feature, not CLI |
| "code-davinci-002 deprecated" | (refuse — discontinued) | Out of scope |
| "gemini cli для ревью" | `gemini-cli` cascade | Different CLI |
| "cursor cli headless" | `cursor-cli` cascade | Different CLI |
| "cline vs code extension" | `cline` cascade | Different tool |

## Edge cases — 5

| User-voice prompt | Resolution |
|---|---|
| "CLAUDE.md vs AGENTS.md разница" | **claude-code** primary (CLAUDE.md is native); load `references/migration.md` which covers AGENTS.md side too |
| "ревью каждого PR с claude" | If CLI implied → **claude-code** (load `references/interop.md`); if raw API → cross-link `anthropic-sdk` |
| "незнакомый репо, сначала read-only" | **claude-code** (load `references/permissions.md` plan-mode section) |
| "hooks не срабатывают в opencode" | **opencode** primary (OpenCode has no native hooks); cross-link to `references/migration.md` here for context |
| "claude code с openai провайдером" | Refuse + redirect → `opencode` (multi-provider). claude-code is Anthropic-only. |

## How to verify (manual)

1. Open a fresh session with this skill at `~/.claude/skills/claude-code/`.
2. Paste each Positive prompt → confirm:
   - System reminder lists `claude-code` as an active skill
   - Response references files matching the "Expected behavior" column
3. Paste each Negative prompt → confirm `claude-code` does NOT appear in routed skills, and the suggested fallback is mentioned
4. Edge cases: confirm response explicitly cross-links ("primary: claude-code, see also: opencode/anthropic-sdk")

If a prompt routes wrong:
- Negative → Positive: tighten `description` SKIP rules
- Positive → Negative: add the missing trigger term to `description`
- Edge routes to only one skill: enrich Related Skills cross-links

Run after any change to `SKILL.md` description or major reference restructure — that's the regression check.
