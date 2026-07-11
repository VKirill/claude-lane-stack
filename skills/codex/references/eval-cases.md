# codex — Eval Cases

v3 format: **user-voice phrasing** (Russian/typos/incomplete welcome) + **Expected behavior** column (which sub-files / templates should load).

## Positive — should activate (10)

| User-voice prompt | Expected behavior |
|---|---|
| "поставь openai codex через npm" | Load `references/installation.md` npm path |
| "sandbox_mode workspace-write в config.toml" | Load `references/permissions.md` + `references/config.md`; cite `references/recommended-defaults.md` |
| "codex exec в CI с sandbox=read-only" | Load `references/interop.md` headless section + cite `examples/github-actions-pr-review.md` |
| "что делает --full-auto" | Load `references/permissions.md`; explain `-a on-request -s workspace-write` shorthand |
| "[profiles.review] блок в config" | Load `references/config.md` profiles section; cite `templates/config.toml.template` + `references/recommended-defaults.md` |
| "добавить github mcp server в codex" | Load `references/mcp.md`; show `codex mcp add` + TOML block |
| "где codex хранит токены auth" | Load `references/installation.md` auth section + `references/troubleshooting.md` |
| "ChatGPT подписка вместо api key" | Load `references/installation.md` auth modes |
| "что такое codex app-server" | Load `references/interop.md` app-server section (v0.130+ feature) |
| "перенести .codex/config.toml в opencode" | Load `references/migration.md` mapping |

## Negative — should NOT activate (10)

| User-voice prompt | Should route to | Why |
|---|---|---|
| "claude code /loop slash" | `claude-code` | Different CLI |
| "opencode.json с несколькими провайдерами" | `opencode` | Different CLI |
| "openai python sdk вызвать gpt-5.5" | `openai-sdk` | SDK not CLI |
| "code-davinci-002 модель" | (refuse — discontinued) | Out of scope |
| "github copilot cli auth" | (clarify — different vendor/tool) | Naming collision |
| "написать свой mcp server" | `mcp-builder` | Server authoring |
| "anthropic prompt caching" | `claude-api` / `anthropic-sdk` | Different vendor |
| "SKILL.md Pattern 2 как писать" | `skill-evaluation` | Skill authoring |
| "aider python pair-programmer" | `aider` cascade | Different tool |
| "cursor cli headless" | `cursor-cli` cascade | Different tool |

## Edge cases — 5

| User-voice prompt | Resolution |
|---|---|
| "хочу использовать codex" | **codex** primary — verify they mean the modern agentic CLI (likely) not deprecated 2021 model (flag if ambiguous) |
| "AGENTS.md schema" | Either **codex** or **opencode**. Default to **codex** if user mentions ChatGPT/OpenAI; **opencode** if multi-provider |
| "лучший cli для sandboxed агента" | **codex** — strongest Rust-enforced sandbox; load `references/permissions.md` |
| "ChatGPT в терминале" | **codex** (official OpenAI agentic terminal) — but clarify since some users mean web ChatGPT shortcuts |
| "OpenAI CLI" | **codex** (modern OpenAI CLI agent); note the separate `openai` Python CLI is different — for SDK use `openai-sdk` |

## How to verify (manual)

1. Open a fresh session with this skill at `~/.claude/skills/codex/`.
2. Paste each Positive prompt → confirm:
   - System reminder lists `codex` as active
   - Response references files matching the "Expected behavior" column
3. Paste each Negative prompt → confirm `codex` does NOT appear, and the fallback skill is mentioned
4. Edge cases: confirm cross-link is explicit ("primary: codex, see also: opencode/openai-sdk")

If a prompt routes wrong:
- Negative → Positive: tighten SKIP rules in `description`
- Positive → Negative: add the missing trigger term
- Edge routes only to one: enrich Related Skills cross-links

Run after any `SKILL.md` description or major reference restructure — that's the regression check.
