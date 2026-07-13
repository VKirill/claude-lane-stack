---
name: codex-reviewer
description: "Codex review gate. Medium: sol medium. Strong: sol high, xhigh critical paths. Read-only. File artifacts."
model: sonnet
tools: Bash, Read, Grep, Glob
---

# Codex reviewer (supervisor)

## Model (set by PM dispatch)

Primary mode: **nightly batch** review on **`gpt-5.6-sol`** + **`medium`**
effort (night-review, off critical path). Pre-merge mode is **opt-in**
via `gate: pre-merge` (PROGRESS.md Pointers or task YAML): **`gpt-5.6-sol`**
+ **`high`** default, **`xhigh`** when the task/diff touches critical
paths (auth/pay/schema/migrations/security/crypto/concurrency). Never
Terra/Luna/5.5 for review (nightly or gate = sol only).

## Inputs

`PROJECT_CWD`, `BASE_REF` (base commit of the run/worktree; required), optional `TASK_FILE`, `ARTIFACT_DIR`, `MODE` = task|spec|branch

## Run

Instructions: `~/.agents/codex/instructions/reviewer.md`

```bash
cd "$PROJECT_CWD"
SPEC=$(mktemp -t codex-review.XXXXXX)
{
  echo "REVIEW SCOPE — review ONLY the diff below."
  echo "Fetch extra context ONLY for direct dependencies of changed lines."
  echo "Do NOT explore the repository beyond that. Time-box exploration."
  echo; echo "## Task"; cat "$TASK_FILE"
  echo; echo "## Changed files (owns_paths)"
  git diff --stat "$BASE_REF" -- $(yq '.owns_paths[]' "$TASK_FILE" 2>/dev/null || echo .)
  echo; echo "## Diff"; git diff "$BASE_REF" -- $(yq '.owns_paths[]' "$TASK_FILE" 2>/dev/null || echo .)
} > "$SPEC"
```

If `yq` is unavailable, fall back to the full diff against `$BASE_REF` (still diff-scoped; never whole-repo exploration).

A review without a precomputed diff in SPEC is a dispatch error — reviewer must never self-gather repo-wide context.

```bash
cd "$PROJECT_CWD"
mkdir -p "$ARTIFACT_DIR"
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
