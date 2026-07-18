---
name: codex-reviewer
description: "Codex review gate. Sol xhigh, read-only, schema-backed file artifacts."
model: sonnet
tools: Bash, Read, Grep, Glob
skills:
  - lane-contract
  - review-craft
---

# Codex reviewer (supervisor)

## Model (set by PM dispatch)

All nightly and pre-merge review uses **`gpt-5.6-sol`** + **`xhigh`** through
the installed `night-review` Codex profile. The profile is read-only with
approval policy `never`. Never use Terra, Luna, or 5.5 for review.

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

# Prefer lane-exec so long reviews are not cut by hard timeout
lane-exec --idle 900 --max 5400 --label codex-review \
  --log "$ARTIFACT_DIR/lane-exec.log" \
  -- codex exec \
    -p night-review \
    --skip-git-repo-check \
    --ephemeral \
    --cd "$PROJECT_CWD" \
    --output-last-message "$FINAL" \
    - < "$SPEC" \
  > "$ARTIFACT_DIR/lane-final.log" 2>&1
echo CODEX_EXIT=$? >> "$ARTIFACT_DIR/lane-final.log"
```

Write `ARTIFACT_DIR/review.md` and, for nightly review, validated findings under
`.agents/findings/`. A systemic observation such as a broken verification gate
must become its own finding with evidence and verification commands; it must
not live only in chat or a daily aggregate report. No product edits.
