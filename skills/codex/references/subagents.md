# Subagents — Codex Pattern (Profiles + Task Delegation)

Codex CLI does not have a first-class named-subagent system like Claude Code's `.claude/agents/<name>.md`. It instead uses a combination of:

1. **Profiles** — named bundles of model + sandbox + approval policy
2. **Custom prompts** — invocable under a specific profile
3. **External `codex exec`** — spawn a fresh, isolated Codex from inside a session

## Pattern A — Profile as agent

Define in `config.toml`:

```toml
[profiles.review]
model = "gpt-5.5"
sandbox_mode = "read-only"
approval_policy = "untrusted"
```

Invoke as a "reviewer" with:

```bash
codex -p review
# or headless:
codex exec "Review the diff" -p review --json
```

## Pattern B — Prompt + profile binding

`.codex/prompts/security-review.md`:

```markdown
---
description: "Security review of current diff"
profile: review
---
You are a security-focused reviewer. Identify:
1. Injection vulnerabilities
2. Auth bypasses
3. Secret leakage

Output JSON: { "verdict": "ok|concerns", "concerns": [...] }
```

Invoke: `/security-review` — runs under the `review` profile.

## Pattern C — Spawn external Codex from within a session

From an active Codex session, use the `Bash` tool (when sandbox allows) to spawn a fresh agent:

```bash
codex exec "Run the full security review prompt on the staged diff" -p review --json > /tmp/r.json
```

This gives full context isolation — the spawned Codex sees only what's in the prompt + the workspace.

## Comparison

| Capability | Claude Code | Codex CLI | OpenCode |
|---|---|---|---|
| Named subagents | First-class (`.claude/agents/*.md`) | Approximate via profiles | First-class (`opencode.json: agent.*` + `.opencode/agents/`) |
| Per-agent tool allowlist | Yes (frontmatter `tools`) | Indirect (sandbox limits all tools) | Yes (`tools.<name>: false`) |
| Per-agent model | Yes | Yes (profile) | Yes |
| Context isolation | Built-in | Via `codex exec` external spawn | Built-in (`primary: false` agents) |
| Invocation from main session | `Task` tool | External `codex exec` | `task` tool |

## When richer agents matter

If your workflow leans heavily on named multi-agent orchestration (planner → coder → reviewer chains), prefer Claude Code or OpenCode. Codex CLI's profile-based approach works well for solo-developer setups with 2-3 named modes (review / build / refactor) but does not scale as naturally to deep agent hierarchies.
