# Sandbox Modes + Approval Policies

Codex's strongest area. The Rust core enforces filesystem and (on some platforms) network boundaries.

## Sandbox modes (`-s` / `sandbox_mode`)

| Mode | Filesystem | Bash side effects | When |
|---|---|---|---|
| `read-only` | No writes | No mutating commands | Unknown repo, review work |
| `workspace-write` | Write within `cwd` + `--add-dir` | Yes, within sandbox | Productive default |
| `danger-full-access` | No boundary | Full host shell | Container/VM only |

DFA (Danger Full Access) is **only** safe inside Docker / VM / ephemeral CI runner. The Rust sandbox cannot rescue you from `rm -rf /` in DFA mode on a host machine.

## Approval policies (`-a` / `approval_policy`)

| Policy | Prompts on |
|---|---|
| `untrusted` | Every tool call (slowest, safest) |
| `on-request` | Only when model asks for elevation (sweet spot) |
| `never` | No prompts (CI mode) |

`on-failure` (older docs) is deprecated.

## Combined recommendations

| Scenario | Recommended combo |
|---|---|
| Unfamiliar repo / first contact | `-s read-only -a untrusted` |
| Daily productive work | `--full-auto` (= `-a on-request -s workspace-write`) |
| Headless CI (read-only) | `-s read-only -a never` |
| Headless CI (auto-apply lint fixes) | `-s workspace-write -a never` (sandboxed runner only) |
| Aggressive automated refactor | `--dangerously-bypass-approvals-and-sandbox` (Docker only) |

## `--full-auto` — productive default

```bash
codex --full-auto
```

Exactly equivalent to:

```bash
codex -a on-request -s workspace-write
```

Codex will work autonomously within the workspace, only stopping to ask when it wants elevation (e.g. writing outside cwd, installing packages, network access).

## DFA — `--dangerously-bypass-approvals-and-sandbox`

```bash
docker run --rm -it -v "$PWD:/workspace" -w /workspace codex-image \
  codex --dangerously-bypass-approvals-and-sandbox
```

Use cases:
- Mass-codemod across a large monorepo
- Heavy automated refactor where every approval prompt would be friction
- Greenfield prototyping in a throwaway container

NEVER on a host machine. NEVER in a CI runner that has access to deploy credentials.

## Live switching

```text
> /permissions
```

Brings up a menu to change sandbox/approval mid-session.

## Web search policy

```toml
web_search = "cached"   # cached | live | disabled
```

`cached` is the sweet spot — Codex's web tool returns recent cached results without burning live-search quota.

## Config example

```toml
# Daily user defaults — safer than --full-auto out of the box
approval_policy = "on-request"
sandbox_mode = "read-only"
web_search = "cached"

[profiles.build]
sandbox_mode = "workspace-write"
approval_policy = "on-request"

[profiles.ci]
sandbox_mode = "read-only"
approval_policy = "never"
```

Start in the cautious top-level mode; opt into `--profile build` when you want to actually edit.

## Compare with Claude Code, OpenCode

| Concern | Codex | Claude Code | OpenCode |
|---|---|---|---|
| Sandbox levels | 3 named modes | 4 permission modes | per-tool boolean |
| Approval granularity | 3 policies | per-tool prompts via matchers | per-tool allow/deny + runtime prompt |
| Filesystem enforcement | Rust-enforced | OS-level (depends on host) | not built-in (use container) |
| Network enforcement | partial | `sandbox.network.deniedDomains` | not built-in (use container) |
| "Safe default" combo | `-s read-only -a untrusted` | `--permission-mode plan` | `--agent plan` |
| "Auto" combo | `--full-auto` | `--permission-mode bypassPermissions` | `--auto` |

Codex's sandbox is the strongest of the three at the binary level. If filesystem isolation guarantees matter and you control only the CLI (no container), Codex is the best choice.
