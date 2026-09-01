# Copy helpers (CLI)

Load when copy-lead needs a second pair of hands. **You** still own `.agents/copy/` canon files. Helpers write **inbox drafts only**.

Missing binary → say so, take the next row. Do not `run-init`. Do not invent quotes.

## Who

| Need | Runner | Model |
|---|---|---|
| Interview, lock, lift into canon | **you** (copy-lead) | — |
| Facts / URLs | skill `tavily` `/search` | REST |
| Cited report | skill `tavily` `/research` | REST |
| Open web, several pages | **Codex** | `gpt-5.6-luna` + `fast` |
| Long synthesis after luna | **Codex** | `gpt-5.6-terra` + `fast` |
| X / Twitter slang | **grok** CLI | default (X on) |
| Cheap bulk (10 H1, cut list) | **OpenCode** | `alibaba-token-plan/deepseek-v4-flash` |
| Stronger draft / 2–3 angles | **OpenCode** | `alibaba-token-plan/deepseek-v4-pro` |
| Second pass with repo in context | **cursor-agent** | `cursor-grok-4.6-medium-fast` |
| Already in the repo | `Agent(Explore)` | — |
| Unpack a page before you write | `Agent(Plan)` | — |

No `cursor-agent` → skip that row (do not invent a Cursor model). Flash missing → try `deepseek/deepseek-v4-flash`. Same for pro.

## Rules

1. One job. Prompt: question, output path, `DONE`/`FAILED`.
2. Output: `.agents/copy/research/inbox/YYYY-MM-DD-<slug>.md` (and `.json` if Tavily).
3. After `DONE` — you lift. Helper does not edit `ANAMNESIS.md` / `audience.md` / `pages/` / `INDEX.md`.
4. `locked` files: do not send them out to rewrite.

## Codex luna (default web)

```bash
mkdir -p .agents/copy/research/inbox
codex exec --ephemeral --skip-git-repo-check \
  -m gpt-5.6-luna \
  -c 'service_tier="fast"' --enable fast_mode \
  --sandbox workspace-write \
  "Research: <QUESTION>
   Write .agents/copy/research/inbox/$(date +%F)-web.md
   Every claim needs a URL. No invented quotes. No product code."
```

Escalate to `-m gpt-5.6-terra` only if luna’s note is thin and the human still wants depth.

## Grok CLI (X)

```bash
mkdir -p .agents/copy/research/inbox
grok -p --permission-mode bypassPermissions \
  "Search X/Twitter for how people talk about: <PAIN>
   8 phrases. Each: phrase + URL or @handle.
   Write .agents/copy/research/inbox/$(date +%F)-x.md"
```

## OpenCode DeepSeek

`--agent plan` (not `lane-writer`). Variant `medium`.

```bash
mkdir -p .agents/copy/research/inbox
# flash = volume; pro = fewer stronger angles
opencode run --pure --format json --dir "$(pwd)" \
  --agent plan \
  --model alibaba-token-plan/deepseek-v4-flash \
  --variant medium \
  --dangerously-skip-permissions \
  "Draft only. Do not edit Vue/CSS or locked copy files.
   Task: <BULK TASK>
   Write .agents/copy/research/inbox/$(date +%F)-flash.md
   No invented customer quotes. End with DONE or FAILED."
```

Pro: same command, `--model alibaba-token-plan/deepseek-v4-pro`.

## Cursor Grok 4.6 medium fast

Always this model. Do not pick composer / sonnet / high.

```bash
mkdir -p .agents/copy/research/inbox
cursor-agent -p --force --trust --approve-mcps \
  --sandbox disabled \
  --workspace "$(pwd)" \
  --model cursor-grok-4.6-medium-fast \
  --output-format text \
  "Read .agents/copy/ (skip locked). Task: <QUESTION>
   Write .agents/copy/research/inbox/$(date +%F)-cursor.md
   No product code. No invented quotes. End with DONE or FAILED."
```
