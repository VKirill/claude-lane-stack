# Claude Lane Stack

**Multi-agent coding orchestration for Claude Code** — file-based task contracts, optional AGY / Grok / Codex write-review lanes, path ownership, live board, stall detection, and **orchestrator auto-merge to `main`**.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/PM-Claude%20Code-black)](https://docs.anthropic.com/en/docs/claude-code)
[![Multi-agent](https://img.shields.io/badge/pattern-multi--agent%20orchestration-purple)](#how-it-works)
[![File contracts](https://img.shields.io/badge/state-file%20based%20YAML-green)](#file-based-contracts)

> **Keywords:** Claude Code multi-agent orchestration · multi-model AI coding agents · AGY Grok Codex lanes · file-based agent contracts · solo developer agent team · auto-merge main · agent worktree · coding agent harness 2026

| Language | Guide |
|----------|--------|
| English | **This file** |
| [Русский](README.ru.md) | Full RU |
| [简体中文](README.zh-CN.md) | 中文 |
| [日本語](README.ja.md) | 日本語 |
| [Español](README.es.md) | ES |
| [Deutsch](README.de.md) | DE |
| [Français](README.fr.md) | FR |
| [한국어](README.ko.md) | KO |
| [Português (BR)](README.pt-BR.md) | PT-BR |

---

## Why Claude Lane Stack?

One developer. One **Claude Code** project manager. Optional cheaper/faster models do the typing. You never babysit git merges.

| Pain (Reddit / X 2026) | This stack |
|------------------------|------------|
| Context dies mid-feature | Fresh worker per task + `PROGRESS.md` / session-log |
| Parallel agents overwrite files | `owns_paths` + `never_touch` + `check-owns-paths` |
| “Who merges this branch?” | **PM auto-merges to `main`** (`wt-merge-main`) |
| Task MCP / heavy Postgres queue | **Files only** under `.agents/runs/` |
| Must install every CLI | `agents-doctor` picks profile from what you have |

**JTBD:** *When I ship software alone with Claude Code, I want a reliable multi-agent harness so cheaper models implement and a gate reviews—while I only talk to the PM and always land on `main`.*

---

## How it works

```text
You  →  Claude Code (dev-orchestrator PM)
              │
              ├─ fast write  → AGY (Gemini)     [optional]
              ├─ main write  → Grok 4.5         [optional]
              ├─ review      → Codex (GPT)      [optional]
              └─ ship        → wt-merge-main → main
```

- **PM is always Claude** — not optional.  
- Auxiliary CLIs are **optional**; `agents-doctor` maps fallbacks.  
- State lives in **git-visible files**, not a task MCP.

---

## Quick start

### Requirements

| Tool | Role |
|------|------|
| **[Claude Code](https://docs.anthropic.com/en/docs/claude-code)** | Required PM |
| [Antigravity / `agy`](https://antigravity.google/) | Optional fast write |
| [Grok CLI](https://x.ai/) | Optional main write |
| [Codex CLI](https://openai.com/codex/) | Optional review / emergency write |
| `git`, Python 3.10+, `rsync` | Install / doctor |

### Install

```bash
git clone https://github.com/VKirill/claude-lane-stack.git
cd claude-lane-stack
./install.sh
```

```bash
export PATH="$HOME/.agents/bin:$PATH"
cd /path/to/your/project
agents-doctor --apply .
claude --agent dev-orchestrator
```

Cold start next session: `/resume-project` or `resume-project .`

---

## Capability profiles

| Profile | You have | Write | Review |
|---------|----------|-------|--------|
| `full` | AGY + Grok + Codex | AGY + Grok | Codex |
| `claude-codex` | Codex | Codex | Codex |
| `claude-agy` | AGY | AGY | Claude reviewer |
| `claude-grok` | Grok | Grok | Claude reviewer |
| `claude-only` | Claude only | Claude subagents | Claude reviewer |

```bash
agents-doctor          # print detection
agents-doctor --apply .  # write .agents/routing.profile.yaml
```

---

## File-based contracts

```text
.agents/runs/<slug>/
  PLAN.md
  STATUS.md
  worktree.json      # if isolated
  MERGE.md           # after auto-merge
  tasks/001-*.yaml   # owns_paths, done_when, lane
  artifacts/001/report.md
```

See [docs/FILE-CONTRACT.md](docs/FILE-CONTRACT.md) and [docs/SOLO-ORCHESTRATION.md](docs/SOLO-ORCHESTRATION.md).

---

## CLI tools (`~/.agents/bin`)

| Command | Purpose |
|---------|---------|
| `agents-doctor` | Detect CLIs → routing profile |
| `resume-project` | Cold-start brief |
| `run-board` | Live `.agents/runs/BOARD.md` |
| `wt-create` / `wt-merge-main` | Worktree + **PM merge to main** |
| `lane-heartbeat` / `lane-stall-check` | Stall detection |
| `check-owns-paths` | Ownership gate after write |
| `project-memory-init` / `night-audit` | PROGRESS / LESSONS / audit |

---

## Hooks (safety + session ledger)

Shared hooks for Claude / Codex / Grok / AGY patterns:

- Block force-push, `--no-verify`, destructive SQL  
- Flag `any`, `$queryRawUnsafe`, secrets  
- Session ledger → `.agents/session-log/`  

Docs: [docs/HOOKS.md](docs/HOOKS.md)

---

## Repository layout

```text
claude-lane-stack/
  install.sh
  bin/                 # doctor + solo tooling
  agents/claude/       # dev-orchestrator + implementers
  agents/agy/          # lane-coder, lane-frontend, …
  agents/grok/         # writer instructions
  agents/codex/        # review / emergency write
  skills/              # orchestrator-lanes, lane-contract, …
  hooks/               # cross-CLI guards + ledger
  profiles/            # full, claude-codex, …
  docs/                # contracts, routing, solo mode
  templates/           # PROGRESS, LESSONS, …
  examples/
```

---

## Comparison (honest)

| | Claude Lane Stack | Raw multi-Claude tmux | Heavy swarms (Gas Town / Flow) |
|--|-------------------|------------------------|--------------------------------|
| PM model | Claude Code | Manual | Custom |
| Multi-model lanes | Yes (optional) | Usually same model | Yes, costly |
| Merge UX | Auto to `main` | You merge | Varies |
| State | Files in repo | Chat history | DB / beads |
| Install weight | Small | None | Heavy |

---

## Security

- No secrets in contracts.  
- `never_touch` for `.env*`, migrations when needed.  
- Review lane recommended for auth/pay/schema.  
- See [SECURITY.md](SECURITY.md).

---

## Contributing / License

MIT — [LICENSE](LICENSE). PRs welcome: [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Related searches this project targets

Claude Code multi-agent · multi-agent coding orchestration 2026 · orchestrate Codex and Claude · Grok coding agent workflow · Antigravity AGY agent · file-based agent task queue · solo developer AI pair programming · agent worktree auto merge · coding agent harness · Claude Code subagents production

---

**Maintainer:** [@VKirill](https://github.com/VKirill) · Built for solo operators who want a factory, not another chat window.
