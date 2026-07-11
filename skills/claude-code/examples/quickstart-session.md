# Quickstart Session — Install → Auth → First Edit → Commit

Reference flow for a brand-new project setup with Claude Code.

## 1. Install

```bash
curl -fsSL https://claude.ai/install.sh | bash
claude --version
# claude 2.1.x
```

## 2. Authenticate

Subscription path:

```bash
claude login
# Opens browser → claude.ai → OAuth → returns to terminal
```

API path:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.zshrc
```

Verify:

```bash
claude doctor
```

## 3. Enter the repo, run `/init`

```bash
cd ~/projects/my-app
claude
```

In the TUI:

```text
> /init
```

Claude reads the repo (package.json, src/, tests/) and writes `CLAUDE.md` to the project root. Review it; commit it.

## 4. Add team `.claude/settings.json`

```bash
mkdir -p .claude
cp ~/.claude/skills/claude-code/templates/settings.json.template .claude/settings.json
$EDITOR .claude/settings.json   # fill in {{...}} placeholders
git add CLAUDE.md .claude/settings.json
git commit -m "chore: add Claude Code project config"
```

Add `.claude/settings.local.json` to `.gitignore`.

## 5. First edit — plan mode

```bash
claude --permission-mode plan
```

```text
> Add a /healthz endpoint to the Fastify server that returns 200 OK.
```

Claude reads `src/app/server.ts`, draws up a plan. Review.

Exit plan mode:

```text
> /plan off
```

Claude now executes — proposes Edit calls, you approve.

## 6. Format hook fires automatically

When Claude calls `Edit`, the `PostToolUse` hook runs `biome format --write $FILE_PATH`. No manual format step.

## 7. Run tests, commit

```text
> Run the tests.
```

Claude calls `Bash(npm test)` (allowed by settings). On green:

```text
> Commit with message "feat: add /healthz endpoint"
```

## 8. Compact context, continue

After a long session:

```text
> /compact
```

Or end and resume later:

```bash
# tomorrow
claude -c   # continue last session
```

## 9. Headless follow-up in CI

`.github/workflows/claude-review.yml`:

```yaml
name: Claude Review
on: pull_request
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: "Review the diff. Reply 'OK' or list concerns."
          permission-mode: plan
```

Done. From zero to in-CI in under 30 minutes.
