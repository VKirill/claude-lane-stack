# Interop — Headless, CI/CD, JSON Output

## Headless one-shot

```bash
claude -p "<prompt>" --output-format json
```

Returns:

```json
{
  "type": "result",
  "session_id": "...",
  "result": "...final assistant message...",
  "usage": { "input_tokens": 1234, "output_tokens": 567 },
  "cost_usd": 0.012
}
```

For streaming:

```bash
claude -p "<prompt>" --output-format stream-json
```

Each line is a JSON event (`message`, `tool_use`, `tool_result`, `result`).

## GitHub Actions — official

```yaml
name: PR review
on: pull_request
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: "Review this PR for security and correctness."
          permission-mode: plan
          model: claude-sonnet-4-6
```

## GitHub Actions — hand-rolled

```yaml
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - run: curl -fsSL https://claude.ai/install.sh | bash
      - run: |
          claude -p "Review the diff between origin/main and HEAD." \
            --output-format json \
            --permission-mode plan \
            --max-turns 6 \
            > review.json
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      - run: jq -r '.result' review.json | gh pr comment ${{ github.event.pull_request.number }} -F -
```

## Exit codes in CI

```bash
set -e
claude -p "..." --output-format json > out.json
case $? in
  0) ;;  # ok
  1) echo "tool denied / aborted"; exit 1 ;;
  2) echo "cancelled"; exit 2 ;;
  *) echo "internal error"; exit 1 ;;
esac
```

## Streaming output to console

```bash
claude -p "..." --output-format stream-json | jq -r 'select(.type=="message") | .content[0].text'
```

## Comparison: headless across the three CLIs

| CLI | Headless flag | Output format |
|---|---|---|
| Claude Code | `claude -p "..." --output-format json` | JSON object with `.result`, `.usage` |
| OpenCode | `opencode run "..." --json` | JSONL events |
| OpenAI Codex | `codex exec "..."` | Plain text or JSON via `--json` |

All three accept stdin piping. See `references/migration.md` for a side-by-side prompt → command translation.

## Cost control

`--max-turns N` caps reasoning loops. For headless review pipelines, 4–8 turns is usually enough. Combine with `--model claude-haiku-4-5` for bulk runs (10× cheaper than Sonnet).

## Common CI patterns

1. **PR review on every push** — `permission-mode plan`, post result as PR comment
2. **Nightly codebase audit** — full repo scan for TODOs / secrets / outdated deps, post to Slack
3. **Release-note generation** — diff between two tags, generate CHANGELOG entry
4. **Test failure triage** — pipe failing test output, get a hypothesis
