# Claude Lane Stack

<p align="center">
  <img src="docs/images/01-hero-conveyor.jpg" alt="Claude Lane Stack — multi-agent coding conveyor" width="100%" />
</p>

**Multi-agent coding orchestration for Claude Code** — file-based task contracts, optional AGY / Grok / Codex write-review lanes, path ownership, live board, stall detection, and **orchestrator auto-merge to `main`**.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/PM-Claude%20Code-black)](https://docs.anthropic.com/en/docs/claude-code)
[![Multi-agent](https://img.shields.io/badge/pattern-multi--agent%20orchestration-purple)](#how-it-works)
[![Telegram](https://img.shields.io/badge/Telegram-Помогающий%20маркетолог-2CA5E0?logo=telegram)](https://t.me/pomogay_marketing)

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

## Author

<p align="center">
  <a href="https://github.com/VKirill">
    <img src="https://avatars.githubusercontent.com/u/17155104?v=4" width="120" height="120" alt="VKirill — Помогающий маркетолог" style="border-radius:50%" />
  </a>
</p>

<p align="center">
  <strong>Кирилл Вечкасов</strong> · <a href="https://github.com/VKirill">@VKirill</a><br/>
  Канал: <a href="https://t.me/pomogay_marketing"><strong>Помогающий маркетолог</strong></a> · <code>t.me/pomogay_marketing</code>
</p>

Я собираю рабочие конвейеры, а не «ещё один чат с нейросетью».  
**Claude Lane Stack** — про то, как одному человеку держать команду агентов: PM на Claude, дешёвые/быстрые модели пишут, Codex ревьюит, **в `main` мержит оркестратор** — ты не путаешься в ветках.

Если интересен маркетинг + ИИ-автоматизация без воды — загляни в Telegram:  
**[Помогающий маркетолог →](https://t.me/pomogay_marketing)**

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

## Visual guide — how the factory works

### 1. The conveyor (hero)

<p align="center">
  <img src="docs/images/01-hero-conveyor.jpg" alt="Conveyor of coding agents" width="90%" />
</p>

Tasks move like tickets on a factory line — not as infinite chat noise.

### 2. Lanes: PM routes work

<p align="center">
  <img src="docs/images/02-lanes-routing.jpg" alt="Claude PM routes AGY Grok Codex lanes into main" width="90%" />
</p>

| Station | Who | Job |
|---------|-----|-----|
| **PM** | Claude Code (`dev-orchestrator`) | Plan, contracts, accept evidence, **merge main** |
| **FAST** | AGY (optional) | Low-risk / UI volume |
| **WRITE** | Grok (optional) | Main implementation |
| **REVIEW** | Codex (optional) | Gate for high-risk / ship |
| **ONBOARD** | Codex `gpt-5.6-sol` + xhigh | CLAUDE.md + primary docs |

### 3. You relax — PM merges to `main`

<p align="center">
  <img src="docs/images/03-auto-merge-main.jpg" alt="Orchestrator auto-merges worktrees to main" width="90%" />
</p>

Worktrees isolate parallel work. When the run is green, **the orchestrator** runs `wt-merge-main`. Human never merges.

### 4. File contracts & ownership

<p align="center">
  <img src="docs/images/04-file-contracts.jpg" alt="File-based YAML contracts owns_paths never_touch" width="90%" />
</p>

Each task owns paths. Parallel agents don’t “helpfully” edit each other’s files.

---

## How it works

```text
You  →  Claude Code (dev-orchestrator PM)
              │
              ├─ fast write  → AGY (Gemini)     [optional]
              ├─ main write  → Grok 4.5         [optional]
              ├─ review      → Codex (GPT)      [optional]
              ├─ onboard     → Codex sol xhigh  [optional]
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
| [Codex CLI](https://openai.com/codex/) | Optional review / onboard / emergency write |
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
# first time on a repo — fill CLAUDE.md + docs via Codex:
# /project-onboard   (dispatches codex-onboarder)
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

Strategy / SEO cocoons → `docs/plans/`. **Implementation** → `.agents/runs/`.

See [docs/FILE-CONTRACT.md](docs/FILE-CONTRACT.md) and [docs/SOLO-ORCHESTRATION.md](docs/SOLO-ORCHESTRATION.md).

---

## CLI tools (`~/.agents/bin`)

| Command | Purpose |
|---------|---------|
| `agents-doctor` | Detect CLIs → routing profile |
| `project-onboard` | Shell scaffold (prefer Codex onboarder) |
| `resume-project` | Cold-start brief |
| `run-board` | Live `.agents/runs/BOARD.md` |
| `wt-create` / `wt-merge-main` | Worktree + **PM merge to main** |
| `lane-heartbeat` / `lane-stall-check` | Stall detection |
| `check-owns-paths` | Ownership gate after write |
| `project-memory-init` / `night-audit` | PROGRESS / LESSONS / audit |

---

## Hooks (safety + session ledger)

- Block force-push, `--no-verify`, destructive SQL  
- Flag `any`, `$queryRawUnsafe`, secrets  
- Session ledger → `.agents/session-log/`  

Docs: [docs/HOOKS.md](docs/HOOKS.md)

---

## Repository layout

```text
claude-lane-stack/
  install.sh
  bin/
  agents/claude|agy|grok|codex/
  skills/
  hooks/
  profiles/
  docs/ + docs/images/
  templates/
  examples/
```

---

## Comparison (honest)

| | Claude Lane Stack | Raw multi-Claude tmux | Heavy swarms |
|--|-------------------|------------------------|--------------|
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

MIT — [LICENSE](LICENSE). PRs: [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Related searches

Claude Code multi-agent · multi-agent coding orchestration 2026 · orchestrate Codex and Claude · Grok coding agent workflow · Antigravity AGY agent · file-based agent task queue · solo developer AI pair programming · agent worktree auto merge · coding agent harness

---

<p align="center">
  <img src="https://avatars.githubusercontent.com/u/17155104?v=4" width="64" height="64" alt="VKirill" style="border-radius:50%" />
  <br/>
  <strong>Built by <a href="https://github.com/VKirill">@VKirill</a></strong>
  · <a href="https://t.me/pomogay_marketing">Помогающий маркетолог</a>
  <br/>
  <em>Factory for solo operators — not another chat window.</em>
</p>
