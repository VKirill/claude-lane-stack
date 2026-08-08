# Claude agents — lane conveyor (role names)

Agents are named by **function in the conveyor**, not by which model brand
writes product code. Daytime writer provider comes from **adoc** /
`.agents/routing.profile.yaml` (`main_write: qwen|grok|codex|kimi|agy`).

## Canonical roster

| Agent | Role | What it does | Backend tool |
|-------|------|--------------|--------------|
| `dev-orchestrator` | PM | Plans, dispatches, merges | Claude (Fable) |
| `run-supervisor` | Watch | Starts + watches `run-controller` for **any** provider | Claude Haiku + Bash |
| `lane-supervisor` | One action | Single `lane-ctl` status/retry/verify/accept | Claude + lane-ctl |
| `emergency-writer` | Emergency write | Shell-out write **after** terminal block | Codex Terra/Sol |
| `night-reviewer` | Review | Night/branch read-only review | Codex Sol |
| `project-onboarder` | Onboard | CLAUDE.md / docs pack | Codex Terra/Sol |
| `docs-maintainer` | Docs | Nightly ARCHITECTURE/PROGRESS refresh | Codex Terra |

## Compatibility aliases (deprecated)

| Alias | Prefer |
|-------|--------|
| `codex-implementer` | `emergency-writer` |
| `codex-reviewer` | `night-reviewer` |
| `codex-onboarder` | `project-onboarder` |
| `codex-docs-maintainer` | `docs-maintainer` |
| `grok-implementer` | `lane-supervisor` |

Aliases keep the same tools and body for one transition period so old prompts
and sessions still resolve. **Do not use aliases in new task text.**

## What is *not* a Claude agent

| adoc / process | How it runs |
|----------------|-------------|
| `main_write: qwen` | `run-controller` → `lane-session` → qwen CLI |
| `main_write: grok` | same → grok CLI |
| `main_write: codex` | same → `codex exec` (lane-writer profile) |
| `main_write: kimi` / `agy` | same |

There is **no** `qwen-implementer` / `kimi-implementer` Claude agent — and there
should not be. One watch agent + one process pool is the conveyor.

## Dispatch cheatsheet (PM)

```text
normal run     → Agent(run-supervisor)
typed recovery → Agent(lane-supervisor)   # not grok-implementer
terminal block → Agent(emergency-writer)  # not “spawn codex because adoc is qwen”
night review   → night-shift / Agent(night-reviewer)
onboard        → Agent(project-onboarder)
docs           → Agent(docs-maintainer)
```

See also: `docs/PLATFORM-CAPABILITIES.md`, `docs/ROUTING.md`.
