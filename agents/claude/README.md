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
| `emergency-writer` | Emergency write | Shell-out write **after** terminal block | adoc emergency writer (default GPT-6 Luna/high/Fast) |
| `night-reviewer` | Review | Night/branch read-only review | Codex Sol |
| `project-onboarder` | Onboard | CLAUDE.md / docs pack | Codex Terra/Sol |
| `docs-maintainer` | Docs | INIT + nightly living docs/ | Codex Luna max fast |
| `memory-maintainer` | Memory | Opt-in fact corpus | Codex (adoc `stages.memory`) |
| `design-lead` | Design | Extract/refresh/audit `docs/DESIGN.md` | Claude |
| `seo-specialist` | SEO | DrMax harness, `.agents/seo/`, `seo-*` CLI | Claude |
| `copy-lead` | Copy | Audience + pages, `.agents/copy/` | Claude |
| `tavily` | Search | Tavily REST, `.agents/research/` | Claude |
| `browser-qa` | Browser QA | Live click + replay under `.agents/qa/` | Jev + chrome-qa (CDP) |

Removed brand aliases (`codex-implementer`, `grok-implementer`, …). Dispatch
the function name only.

## What is *not* a Claude agent

| adoc / process | How it runs |
|----------------|-------------|
| `main_write: qwen` | `run-controller` → `lane-session` → qwen CLI |
| `main_write: grok` | same → grok CLI |
| `main_write: codex` | same → `codex exec` (lane-writer profile) |
| `main_write: kimi` / `agy` / `cursor` / `opencode` | same |

There is **no** `qwen-implementer` / `kimi-implementer` Claude agent — and there
should not be. One watch agent + one process pool is the conveyor.

## Dispatch cheatsheet (PM)

```text
normal run     → Agent(run-supervisor)
typed recovery → Agent(lane-supervisor)
terminal block → Agent(emergency-writer)
night review   → night-shift / Agent(night-reviewer)
onboard        → Agent(project-onboarder)
docs           → Agent(docs-maintainer)
memory         → Agent(memory-maintainer)
design         → Agent(design-lead)
seo            → Agent(seo-specialist)
copy           → Agent(copy-lead)
tavily         → Agent(tavily)
browser QA     → Agent(browser-qa)
```

See also: `docs/PLATFORM-CAPABILITIES.md`, `docs/ROUTING.md`.
