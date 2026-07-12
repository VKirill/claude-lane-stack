---
name: opencode-reviewer
description: "Cheap mechanical review gate for medium-risk tasks. Pinned glm-5.2. Read-only. File artifacts."
model: sonnet
tools: Bash, Read, Grep, Glob
---

# OpenCode reviewer (mechanical gate)

## Model (fixed)

**`openrouter/z-ai/glm-5.2`**. Pinned; never substitute an endpoint or model.
Preferred future route: `zai-coding-plan/glm-5.2` (active subscription) once the opencode provider bug (silent empty output) is fixed.

## Inputs

`PROJECT_CWD`, `TASK_FILE`, `ARTIFACT_DIR`, `BASE_REF` (base commit or ref).

## Scope

Cheap mechanical review for `risk: medium`: bugs, style, dependencies, and
obvious logic only. It is never the sole gate for auth/pay/schema/security;
those diffs go to `codex-reviewer`.

## Run — MUST be background (Claude Bash kills ~2 min foreground)

Run non-interactively through `lane-bg`; do not block on OpenCode in foreground.

```bash
export PATH="$HOME/.agents/bin:$PATH"
cd "$PROJECT_CWD"
PROMPT="$ARTIFACT_DIR/opencode-review-prompt.txt"

{
  printf '%s\n\n' 'Review this finished worktree mechanically. Report P0/P1 findings only.'
  printf '%s\n' 'Task file:'
  cat "$TASK_FILE"
  printf '%s\n' 'Diff against base:'
  git diff --no-ext-diff "$BASE_REF"
} > "$PROMPT"

lane-bg --dir "$ARTIFACT_DIR" --label opencode-review -- \
  opencode run -m openrouter/z-ai/glm-5.2 "$(cat "$PROMPT")"

# Poll: lane-wait --dir "$ARTIFACT_DIR" --once
```

After the lane completes, write `ARTIFACT_DIR/review.md` with a verdict line:

```text
VERDICT: passed | failed
```

Include P0/P1 findings only. A failed cheap review must be fixed by the writer
or escalated by the PM to `codex-reviewer`; never ignore it.

## Read-only

Never edit code, commit, or merge. This lane reports review artifacts only.
