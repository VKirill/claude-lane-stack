# Quickstart Session — Install → ChatGPT Login → First Edit

## 1. Install

```bash
npm i -g @openai/codex
codex --version
# codex-cli 0.130.x
```

## 2. Auth via ChatGPT subscription

```bash
codex login
# Opens browser → chatgpt.com → OAuth → token stored in ~/.codex/auth.json
```

Or via API key:

```bash
export OPENAI_API_KEY="sk-..."
```

Verify:

```bash
codex doctor
```

## 3. Project init

```bash
cd ~/projects/my-app
codex
> /init
```

`/init` writes `AGENTS.md` (portable to OpenCode too).

## 4. Configure profiles

```bash
mkdir -p .codex
cp ~/.claude/skills/codex/templates/config.toml.template .codex/config.toml
$EDITOR .codex/config.toml   # fill {{...}}
git add AGENTS.md .codex/config.toml
git commit -m "chore: add Codex CLI configuration"
```

Add `.codex/auth.json` to `.gitignore` (or just `.codex/auth*`).

## 5. First edit — read-only first

Top-level config has `sandbox_mode = "read-only"`, so unfamiliar work starts safe:

```bash
codex
> Add a /healthz endpoint to the Fastify server.
```

Codex drafts a plan but cannot write (read-only sandbox).

## 6. Switch to build profile to execute

```bash
codex -p build
> Add a /healthz endpoint to the Fastify server.
```

Or live-switch:

```text
> /permissions
> Set sandbox to workspace-write
> Set approvals to on-request
```

Equivalent to `--full-auto`.

## 7. Heavy refactor with gpt-5.5

```bash
codex -p refactor
> Migrate src/auth/ from Express to Fastify.
```

Uses gpt-5.5 with high reasoning effort. More tokens, better at multi-file changes.

## 8. Headless follow-up in CI

`.github/workflows/codex-review.yml`:

```yaml
- run: npm i -g @openai/codex@0.130.0
- run: |
    codex exec "Review the diff" -p ci-review --json > /tmp/r.json
    jq -r '.result' /tmp/r.json
  env: { OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }} }
```

`-p ci-review` uses `[profiles.ci-review]` from `config.toml`: read-only, no approvals.

## 9. (Optional) Embed via app-server

For a custom UI that wraps Codex:

```bash
codex app-server --stdio
```

Drive it with JSON commands over stdio.

Done. From install to in-CI in ~20 minutes, with Rust-enforced sandbox for free.
