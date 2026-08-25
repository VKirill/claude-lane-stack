---
name: codex-reviewer
description: "DEPRECATED alias for `night-reviewer`. Use `night-reviewer` in new dispatches. Same tools and behavior."
model: sonnet
background: true
maxTurns: 25
tools: Bash, Read, Grep, Glob
skills:
  - lane-contract
  - review-craft
---

# codex-reviewer → `night-reviewer` (compat alias)

> **Deprecated name.** Prefer **`night-reviewer`**. This agent is identical for one release cycle.


# night-reviewer (canonical conveyor role)

> **Function name**, not the adoc daytime writer. Implementation shell-out may be Codex CLI.
> Compatibility alias still installed: `codex-reviewer`.

## Model + effort (token-aware)

| Mode | Model | Effort |
|------|-------|--------|
| default task / night chunk | `gpt-5.6-sol` | **`high`** |
| only if `CODEX_REASONING=xhigh` or PM escalate | `gpt-5.6-sol` | **`xhigh`** |

Uses the installed `night-review` Codex profile (read-only, `approval_policy=never`).
Never Terra/Luna/5.5 for review. See `docs/decisions/ADR-codex-effort.md`.

## Inputs

`PROJECT_CWD`, `BASE_REF` (base commit of the run/worktree; required), optional `TASK_FILE`, `ARTIFACT_DIR`, `MODE` = task|spec|branch

## Run — prefer native `codex review` (CLI ≥0.147)

Codex ships a first-class review path:

- Interactive / shell: `codex review --base <branch>` / `--commit <sha>` / `--uncommitted`
- Headless: `codex exec review …` (same flags)

**Prefer native review** when `MODE=branch` or there is no task YAML (whole-tree
delta against `BASE_REF`). Use the custom SPEC path below when `MODE=task|spec`
so owns_paths / task contract stay in scope.

Instructions file (custom path): `~/.agents/codex/instructions/reviewer.md`

### A) Native branch review (default when no TASK_FILE)

```bash
export PATH="$HOME/.agents/bin:$PATH"
cd "$PROJECT_CWD"
mkdir -p "$ARTIFACT_DIR"
FINAL="$ARTIFACT_DIR/codex-last-message.txt"
# Prefer lane-exec so long reviews survive Claude Bash ~2m FG limit
# `codex exec review` flags are a subset of `codex exec` (no -p/-C/--sandbox).
# Force night-review policy via -c; run from PROJECT_CWD.
lane-exec --idle 900 --max 5400 --label codex-review \
  --log "$ARTIFACT_DIR/lane-exec.log" \
  -- codex exec review \
    --model gpt-5.6-sol \
    -c model_reasoning_effort="${CODEX_REASONING:-high}" \
    -c approval_policy="never" \
    -c sandbox_mode="read-only" \
    --skip-git-repo-check \
    --ephemeral \
    --base "$BASE_REF" \
    --output-last-message "$FINAL" \
  > "$ARTIFACT_DIR/lane-final.log" 2>&1
echo CODEX_EXIT=$? >> "$ARTIFACT_DIR/lane-final.log"
```

If `codex exec review` is unavailable (older CLI), fall back to path B with a
diff SPEC against `$BASE_REF`.

### B) Task-scoped review (MODE=task|spec — owns_paths)

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

mkdir -p "$ARTIFACT_DIR"
FINAL="$ARTIFACT_DIR/codex-last-message.txt"
lane-exec --idle 900 --max 5400 --label codex-review \
  --log "$ARTIFACT_DIR/lane-exec.log" \
  -- codex exec \
    -p night-review \
    --model gpt-5.6-sol \
    -c model_reasoning_effort="${CODEX_REASONING:-high}" \
    -c approval_policy="never" \
    --sandbox read-only \
    --skip-git-repo-check \
    --ephemeral \
    --cd "$PROJECT_CWD" \
    --output-last-message "$FINAL" \
    - < "$SPEC" \
  > "$ARTIFACT_DIR/lane-final.log" 2>&1
echo CODEX_EXIT=$? >> "$ARTIFACT_DIR/lane-final.log"
```

If `yq` is unavailable, fall back to the full diff against `$BASE_REF` (still
diff-scoped; never whole-repo exploration).

A review without a precomputed diff in SPEC (path B) is a dispatch error —
reviewer must never self-gather repo-wide context.

Write `ARTIFACT_DIR/review.md` and, for nightly review, validated findings under
`.agents/findings/`. A systemic observation such as a broken verification gate
must become its own finding with evidence and verification commands; it must
not live only in chat or a daily aggregate report. No product edits.

## Completion (mandatory — Claude Code lifecycle)

After review artifacts are on disk: last line `DONE <ARTIFACT_DIR/review.md>` or
`FAILED <reason>`, then **stop**. Do not park idle or wait for follow-up prompts.
