# Subagents

Subagents are named, scoped agents. The main session spawns them via the `Task` tool; each runs in isolated context with its own system prompt, model, and tool allowlist.

## File layout

- **Project**: `.claude/agents/<name>.md`
- **User**: `~/.claude/agents/<name>.md`

## Frontmatter

```yaml
---
name: pr-reviewer
description: "Reviews a PR diff for security and correctness. Returns a list of concerns or 'OK'."
tools:
  - Read
  - Grep
  - Bash(git diff:*)
  - Bash(git log:*)
model: claude-sonnet-4-6
---
```

| Field | Purpose |
|---|---|
| `name` | Identifier (matches filename) |
| `description` | Routing hint — main session uses this to pick the agent for a `Task` call |
| `tools` | Allowlist of tool matchers |
| `model` | Override default model for this agent |
| `color` (optional) | TUI badge colour |

Body = system prompt for the subagent.

## Body — example

```markdown
You are a focused code reviewer. Your job is to scan the provided diff
and report security/correctness issues.

Output JSON only:
{
  "verdict": "ok" | "concerns",
  "concerns": [{ "severity": "high|medium|low", "file": "...", "note": "..." }]
}

Do not fix anything. Do not run tests. Read-only review.
```

## Invocation

### Implicit (description match)

The main agent calls `Task` and supplies the user's intent. Claude Code picks the subagent whose `description` matches best.

### Explicit (`/agents`)

```text
/agents
> Select pr-reviewer
> [prompt]
```

### Programmatic (in a hook or command)

```bash
claude -p "/agents pr-reviewer Review the diff in HEAD~1..HEAD" --output-format json
```

## Context isolation

A subagent **does not** see the main session's prior messages unless they're included in the `Task` call prompt. This is a feature: each subagent has a clean, narrow context — better for review/audit work. Pass everything it needs explicitly.

## Composition patterns

- **Reviewer chain**: `code-reviewer` → `security-reviewer` → `test-coverage-reviewer`. Main session aggregates verdicts.
- **Plan + Execute split**: `planner` (Opus, read-only) returns a plan. `executor` (Sonnet, full tools) runs each step.
- **Parallel exploration**: `dispatching-parallel-agents` (superpowers skill) pattern — spawn N subagents on disjoint write scopes.

## Limits

- Subagents cannot spawn further subagents (no recursion).
- Subagents do not have access to the main session's MCP servers unless declared in their own `tools` list.
- Background subagents are not supported in CLI mode (only in interactive TUI with `/agents run --background`).
