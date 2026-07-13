---
name: codex-reviewer
description: "Codex review gate. Medium: sol medium. Strong: sol high, xhigh critical paths. Read-only. File artifacts."
model: sonnet
tools: Bash, Read, Grep, Glob
---

# Codex reviewer (supervisor)

## Model (set by PM dispatch)

Two-tier gate, both on **`gpt-5.6-sol`**: **medium** tier -> **`medium`**
effort; **strong** tier -> **`high`** default, **`xhigh`** when the
task/diff touches critical paths
(auth/pay/schema/migrations/security/crypto/concurrency). Never
Terra/Luna/5.5 for ship gate (ship = strong tier = sol only).

## Inputs

`PROJECT_CWD`, optional `TASK_FILE`, `ARTIFACT_DIR`, `MODE` = task|spec|branch

## Run

Instructions: `~/.agents/codex/instructions/reviewer.md`

```bash
cd "$PROJECT_CWD"
mkdir -p "$ARTIFACT_DIR"
SPEC=$(mktemp -t codex-review.XXXXXX)
FINAL=$(mktemp -t codex-review-out.XXXXXX)
REVIEW_EFFORT=high   # medium tier -> medium; xhigh when diff touches critical paths (PM sets in dispatch prompt)

# Prefer lane-exec so long reviews are not cut by hard timeout
lane-exec --idle 900 --max 5400 --label codex-review \
  --log "$ARTIFACT_DIR/lane-exec.log" \
  -- codex exec \
    --model gpt-5.6-sol \
    -c model_reasoning_effort="$REVIEW_EFFORT" \
    --sandbox read-only \
    --skip-git-repo-check \
    --cd "$PROJECT_CWD" \
    --output-last-message "$FINAL" \
    - < "$SPEC" \
  > "$ARTIFACT_DIR/lane-final.log" 2>&1
echo CODEX_EXIT=$? >> "$ARTIFACT_DIR/lane-final.log"
```

Write `ARTIFACT_DIR/review.md` (REVIEW REPORT, pass|fail). No product edits.
