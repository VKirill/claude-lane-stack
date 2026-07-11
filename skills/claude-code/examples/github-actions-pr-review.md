# GitHub Actions — Headless PR Review with Claude Code

End-to-end pipeline: on every PR, Claude Code reviews the diff in plan mode and posts findings as a PR comment.

## Workflow file

`.github/workflows/claude-review.yml`:

```yaml
name: Claude PR Review
on:
  pull_request:
    types: [opened, synchronize, reopened]

concurrency:
  group: claude-review-${{ github.event.pull_request.number }}
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

      - name: Install Claude Code
        run: curl -fsSL https://claude.ai/install.sh | bash

      - name: Compute diff
        id: diff
        run: |
          git fetch origin ${{ github.event.pull_request.base.ref }}
          {
            echo 'DIFF<<__EOF__'
            git diff origin/${{ github.event.pull_request.base.ref }}...HEAD --stat
            echo
            git diff origin/${{ github.event.pull_request.base.ref }}...HEAD -- '*.ts' '*.tsx' '*.js' '*.py'
            echo '__EOF__'
          } >> $GITHUB_OUTPUT

      - name: Review with Claude
        id: claude
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          cat > /tmp/prompt.txt <<'EOF'
          Review the following PR diff. Identify:
          1. Security risks
          2. Likely bugs
          3. Missing test coverage
          4. Style violations

          Reply with a short Markdown report. If the PR is clean, reply exactly:
          ## Claude review: OK

          DIFF:
          EOF
          echo "${{ steps.diff.outputs.DIFF }}" >> /tmp/prompt.txt
          claude -p "$(cat /tmp/prompt.txt)" \
            --output-format json \
            --permission-mode plan \
            --max-turns 6 \
            --model claude-sonnet-4-6 \
            > /tmp/review.json
          jq -r '.result' /tmp/review.json > /tmp/review.md
          cat /tmp/review.md

      - name: Post comment
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh pr comment ${{ github.event.pull_request.number }} \
            --repo ${{ github.repository }} \
            --body-file /tmp/review.md
```

## Cost notes

- `--max-turns 6` caps reasoning loops
- `--permission-mode plan` ensures no side effects
- `claude-sonnet-4-6` is the cost/quality sweet spot; switch to `claude-haiku-4-5` for high-PR-volume repos

## Concurrency

The `concurrency:` block cancels in-flight reviews when a new commit is pushed. Avoids paying for reviews of obsolete commits.

## Failure modes

| Error | Cause |
|---|---|
| `exit code 3` | `ANTHROPIC_API_KEY` missing or invalid |
| `exit code 1` | Permission denied (plan mode should not hit this — check matchers) |
| Truncated output | Diff > model context; pre-filter diff to `--stat` + selected files |

## Variations

- Replace `claude -p` with `anthropics/claude-code-action@v1` for the official action wrapping
- Replace plan mode with `acceptEdits` to let Claude auto-fix lint issues and push back
- Add a follow-up job that approves the PR if review is clean
