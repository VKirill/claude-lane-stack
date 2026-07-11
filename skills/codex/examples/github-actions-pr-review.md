# GitHub Actions — Headless PR Review with Codex (Read-Only Sandbox)

End-to-end pipeline using Codex's Rust-enforced read-only sandbox for safety.

## Workflow

`.github/workflows/codex-review.yml`:

```yaml
name: Codex PR Review
on:
  pull_request:
    types: [opened, synchronize, reopened]

concurrency:
  group: codex-review-${{ github.event.pull_request.number }}
  cancel-in-progress: true

jobs:
  review:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
      contents: read
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          ref: ${{ github.event.pull_request.head.sha }}

      - name: Setup Node + Codex
        uses: actions/setup-node@v4
        with: { node-version: '24' }
      - run: npm i -g @openai/codex@0.130.0

      - name: Compute diff
        run: |
          git fetch origin ${{ github.event.pull_request.base.ref }}
          git diff origin/${{ github.event.pull_request.base.ref }}...HEAD > /tmp/diff.patch
          wc -l /tmp/diff.patch

      - name: Review with Codex
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          PROMPT=$(cat <<'EOF'
          Review the attached PR diff. Identify:
          1. Security risks (high priority)
          2. Likely bugs
          3. Missing test coverage
          4. Style violations

          Output Markdown. If clean, reply exactly: ## Codex review: OK
          EOF
          )
          codex exec "$PROMPT$(echo; cat /tmp/diff.patch)" \
            -p ci-review \
            --json \
            > /tmp/run.json
          jq -r '.result' /tmp/run.json > /tmp/review.md
          cat /tmp/review.md

      - name: Comment PR
        env: { GH_TOKEN: ${{ secrets.GITHUB_TOKEN }} }
        run: gh pr comment ${{ github.event.pull_request.number }} --repo ${{ github.repository }} --body-file /tmp/review.md
```

Where `.codex/config.toml` defines:

```toml
[profiles.ci-review]
model = "gpt-5.5"
sandbox_mode = "read-only"
approval_policy = "never"
web_search = "disabled"
```

## Why this is safer than the other CLIs in CI

Codex's `sandbox_mode = "read-only"` is **Rust-enforced** — even a malicious prompt cannot get the agent to write to the filesystem, because the sandbox refuses the syscall at the binary level. Claude Code and OpenCode rely on the model behaving + OS perms.

Combined with `approval_policy = "never"` and `web_search = "disabled"`, this profile is a hard read-only ceiling.

## Cost notes

- `gpt-5.5` is the cheapest interactive model
- Average PR review: ~2500 prompt tokens, ~400 completion tokens
- ChatGPT Plus / Pro: covered by subscription quota
- API: pennies per review

## Failure modes

| Error | Cause |
|---|---|
| `exit 3` | `OPENAI_API_KEY` missing or invalid |
| Truncated diff | Diff > model context; use `--stat` + selected files |
| "approval policy mismatch" | Profile sets `never` but model wanted to elevate — restrict the prompt or upgrade to `--full-auto` (in a different profile) |

## Variations

- Replace `codex exec` with `codex app-server` if you want a long-lived in-CI process
- Use `-p refactor` (gpt-5.5 + high reasoning) for high-stakes merge-to-main PRs
- Stack two jobs: `gpt-5.5` with low reasoning for cheap first-pass; same model with high reasoning only if first pass reports concerns

## Compare with Claude Code & OpenCode actions

| Property | Codex CI | Claude Code CI | OpenCode CI |
|---|---|---|---|
| Sandbox guarantee | Rust-enforced | Permission matchers (OS-level) | Container layer |
| Default model | gpt-5.5 | claude-sonnet-4-6 | provider-of-choice |
| Cheapest variant | gpt-5.5 | claude-haiku-4-5 | groq/llama-3.3-70b-versatile |
| Native action | (community) | `anthropics/claude-code-action@v1` | (community) |
