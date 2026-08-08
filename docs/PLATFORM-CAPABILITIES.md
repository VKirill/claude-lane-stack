# Platform capabilities — Claude Code + Codex (lane stack)

What we **use on purpose** from the host CLIs. Verified against Claude Code
**2.1.226** and Codex CLI **0.146.1 / 0.147.0** (2026-08).

## Claude Code (PM + supervisors)

| Feature | Version | Stack use |
|---------|---------|-----------|
| Agent tool + `background` / `maxTurns` frontmatter | 2.1.198+ bg default | All `agents/claude/*` one-shots close as **done** |
| Correct close: done ≠ idle | agent-view / sub-agents docs | Completion sections; no parked idle |
| `SendMessage` / `ListAgents` (local peers) | **2.1.224+** | `run-supervisor` → PM stage lines |
| `SendMessage` **start** Remote Control by `name [ref]` | **2.1.225+** | Optional operator alert on terminal block/ship |
| `TaskStop` | built-in | PM stops stuck Agents only |
| `Monitor` | built-in | Optional log watches; deploys prefer Bash+log / `lane-bg` |
| Concurrent subagent cap (default 20) | 2.1.217+ | One `run-supervisor` per run — stay well under |
| Nested spawn depth | 2.1.219+ default 3 | Stack supervisors do **not** nest fleets |
| `crossSessionInbound` / `dialogExpiry` | 2.1.224+ | Opt-in via `LANE_CROSS_SESSION_INBOUND` at install |
| Agent teams experimental | env flag | Off by default for conveyor; human opt-in only |
| Status line command | settings | `lane-statusline` |
| PreToolUse guard | settings | `guard_shell.py` via install merge |

**Not used as conveyor:** Claude Agent teams as writers, background sessions per
task, `/fork` fleets, ultraplan, cloud review as daytime accept.

### Install env knobs

```bash
# Peer messages delivered without hold (operator sessions that need unattended pings)
LANE_CROSS_SESSION_INBOUND=accept install.sh

# Or refuse all inbound peer text
LANE_CROSS_SESSION_INBOUND=refuse install.sh
```

Default: unset → Claude Code mode-based hold/accept rules.

## Codex CLI (writers + review)

| Feature | Version | Stack use |
|---------|---------|-----------|
| `codex exec` + `--json` + ephemeral CODEX_HOME | stable | `lane-session` bare lane-writer |
| `service_tier=fast` + `features.fast_mode` | stable | adoc Fast mode → lane-session |
| `--output-schema` | stable | night-review-engine typed JSON |
| **`codex exec review --base/--commit/--uncommitted`** | **0.147-era** | `night-reviewer` MODE=branch |
| **Removed `codex exec --full-auto`** | **0.147.0** | Use `-c approval_policy=never` + `--sandbox workspace-write` |
| Profiles (`-p lane-writer`, `-p night-review`) | stable | Isolated write vs read-only review |
| Multi-agent / plugins / browser / goals / memories | features | **Disabled** on bare lane-writer |
| `codex doctor` | stable | ops health (optional) |
| `codex app-server` / remote-control | experimental | **Not** the daytime conveyor (file receipts stay SoT) |
| Plugins / MCP 2026-07-28 | 0.147 | Host interactive only; not injected into bare writer home |

### Why we disable Codex multi_agent on writers

The stack’s DAG + ownership + progressive accept already multiplies work. Nested
Codex agents inside a lane double cost and blur `owns_paths`. Keep
`[agents] max_threads = 1` and `multi_agent=false` on lane-writer.

### Host interactive Codex vs bare lane

| | Host `~/.codex` | Ephemeral lane-writer |
|--|-----------------|------------------------|
| MCP / plugins / skills | yes (user) | no (tmpfs-hidden) |
| fast_mode | user choice | only if adoc `service_tier: fast` |
| web_search | cached/on | disabled |
| Report protocol | freeform | LANE_REPORT + stamped PROMPT_SHA256 |

## Claude agent role names (not brands)

| Canonical | Function | Compat alias |
|-----------|----------|--------------|
| `run-supervisor` | Watch run for **any** adoc provider | — |
| `lane-supervisor` | One `lane-ctl` action | `lane-supervisor` (deprecated) |
| `emergency-writer` | Codex shell-out after terminal block | `emergency-writer` |
| `night-reviewer` | Codex review | `night-reviewer` |
| `project-onboarder` | Codex onboard | `project-onboarder` |
| `docs-maintainer` | Codex docs | `docs-maintainer` |

adoc `main_write: qwen|grok|codex|…` selects the **process**, never a
`*-implementer` Claude agent.

## Decision rules

1. **Truth on disk** always wins over chat / peer messages / idle chips.
2. Use the **newest host tool flag** when it shortens a known path (`codex review`,
   `SendMessage` by name) — do not reinvent.
3. Do not pull experimental app-server / multi_agent into the durable conveyor
   until receipts and owns/verify stay identical.
4. Prefer **role agent names** in new prompts; keep vendor aliases only for
   transition.
