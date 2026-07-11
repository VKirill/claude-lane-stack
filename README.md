# Claude Lane Stack

<p align="center">
  <img src="docs/images/01-hero-conveyor.jpg" alt="Claude Lane Stack — multi-agent coding conveyor" width="100%" />
</p>

**A small AI coding factory for one person.**  
You talk to one project manager (Claude Code). It assigns optional workers (AGY / Grok / Codex), checks the work, and **puts finished code on the `main` branch** — you don’t juggle five chats or merge branches yourself.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/PM-Claude%20Code-black)](https://docs.anthropic.com/en/docs/claude-code)
[![Beginner guide](https://img.shields.io/badge/Start%20here-Beginner%20guide-brightgreen)](docs/BEGINNER.md)
[![Telegram](https://img.shields.io/badge/Telegram-Помогающий%20маркетолог-2CA5E0?logo=telegram)](https://t.me/pomogay_marketing)

| Language | |
|----------|--|
| English | **This file** |
| [Русский](README.ru.md) | + [Гайд новичка](docs/BEGINNER.ru.md) |
| [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [Español](README.es.md) · [Deutsch](README.de.md) · [Français](README.fr.md) · [한국어](README.ko.md) · [Português](README.pt-BR.md) | |

**New to “orchestration”?** Start here → **[Beginner guide (plain language)](docs/BEGINNER.md)** · [RU](docs/BEGINNER.ru.md)

---

## Author

<p align="center">
  <a href="https://github.com/VKirill"><img src="https://avatars.githubusercontent.com/u/17155104?v=4" width="120" height="120" alt="VKirill" style="border-radius:50%" /></a>
</p>

<p align="center">
  <strong>Кирилл Вечкасов</strong> · <a href="https://github.com/VKirill">@VKirill</a><br/>
  Telegram: <a href="https://t.me/pomogay_marketing"><strong>Помогающий маркетолог</strong></a>
</p>

I build **working conveyors**, not “another chat with an LLM”.  
One human · Claude as PM · other models on the line · **merge to `main` is the PM’s job**.

→ [t.me/pomogay_marketing](https://t.me/pomogay_marketing)

---

## If you only remember three steps

```bash
# 1) Install the stack once (on your machine)
git clone https://github.com/VKirill/claude-lane-stack.git
cd claude-lane-stack && ./install.sh
export PATH="$HOME/.agents/bin:$PATH"   # or open a new terminal

# 2) In YOUR app folder — see which AI tools you have
cd /path/to/your-project
agents-doctor --apply .

# 3) Start the project manager and talk normally
claude --agent dev-orchestrator
# first time in this project:  /project-onboard
# later, after a break:        /resume-project
```

| Step | Meaning in plain words |
|------|-------------------------|
| `./install.sh` | Puts the “factory kit” (agents + commands) on your computer |
| `agents-doctor --apply .` | Checks Claude / AGY / Grok / Codex and writes “who can work here” |
| `claude --agent dev-orchestrator` | Opens the **only chat you need** — the PM |
| `/project-onboard` | First-time passport of the repo (CLAUDE.md, short docs) — **Codex does this** |
| `/resume-project` | “What were we doing?” after sleep / new chat — **not** part of first install |

Full walkthrough: [docs/BEGINNER.md](docs/BEGINNER.md).

---

## What is this? (30 seconds)

| Role | Who | You do |
|------|-----|--------|
| Owner | **You** | Say *what* you want in normal language |
| Project manager | **Claude Code** agent `dev-orchestrator` | Plans, assigns, checks, merges to `main` |
| Workers (optional) | AGY, Grok, Codex | Write or review code when installed |
| Job cards | Files under `.agents/runs/` | Created by the PM — you can look, rarely edit |
| Official code | Git branch **`main`** | End of a successful job |

<p align="center">
  <img src="docs/images/02-lanes-routing.jpg" alt="PM routes workers into main" width="90%" />
</p>

---

## Visual tour

| Picture | Meaning |
|---------|---------|
| ![](docs/images/01-hero-conveyor.jpg) | Work moves on a **conveyor**, not in endless chat noise |
| ![](docs/images/02-lanes-routing.jpg) | PM routes **fast / write / review** lanes into `main` |
| ![](docs/images/03-auto-merge-main.jpg) | You don’t merge — the **orchestrator** does |
| ![](docs/images/04-file-contracts.jpg) | Each task has a **card** (which files it may touch) |

---

## Commands cheat-sheet (beginner)

### Install once

| Command | What it is | When |
|---------|------------|------|
| `git clone …` | Download this repository | First time |
| `./install.sh` | Install agents & tools into `~/.agents` | First time |
| `export PATH="$HOME/.agents/bin:$PATH"` | Make tools visible in the terminal | Each new terminal (or add to `~/.bashrc`) |

### Once per project

| Command | What it is | When |
|---------|------------|------|
| `cd your-project` | Enter **your** app | Before anything else |
| `agents-doctor --apply .` | Detect available CLIs → write routing profile | First visit / after installing a new CLI |
| `/project-onboard` (in Claude) | Fill CLAUDE.md + starter docs via **Codex** | Empty / new project |
| `claude --agent dev-orchestrator` | Start the PM | Every work session |

### Day to day

| You type | What it is | When |
|----------|------------|------|
| *«Add dark mode to settings»* (normal language) | A work request to the PM | Features & fixes |
| `/resume-project` or `resume-project .` | Short status: now / blocked / next | **After a break** or new chat window |
| *«It’s stuck»* | Ask PM to check silent workers | Long silence |

### Usually only the PM types these

| Command | What it is |
|---------|------------|
| `run-board` | Refresh the job scoreboard |
| `wt-create` / `wt-merge-main` | Isolated copy + **merge into `main`** |
| `check-owns-paths` | Did the worker stay in its file list? |
| `lane-stall-check` | Who went silent? |

Details & FAQ → [docs/BEGINNER.md](docs/BEGINNER.md).

---

## Footnotes for first-timers

1. **You don’t need AGY + Grok + Codex all at once.** Only **Claude Code** is required. Others are optional “workers”.  
2. **`/resume-project` is not step 1 of install.** It’s for the *next* session, when the chat forgot yesterday.  
3. **Strategy docs** (SEO cocoons, long plans) live in `docs/plans/`. **Coding jobs** live in `.agents/runs/`. Say *«implement it»* to promote a plan into a run.  
4. **If the PM asks you to merge a branch — something’s wrong.** Merging to `main` is the PM’s job (`wt-merge-main`).  
5. **Closing the terminal doesn’t delete the project.** Code stays on disk; only chat memory is gone → `/resume-project`.

---

## For people who want more depth

| Topic | Doc |
|-------|-----|
| Solo rules (you never merge) | [docs/SOLO-ORCHESTRATION.md](docs/SOLO-ORCHESTRATION.md) |
| Task YAML layout | [docs/FILE-CONTRACT.md](docs/FILE-CONTRACT.md) |
| Who writes / reviews | [docs/ROUTING.md](docs/ROUTING.md) |
| Profiles if CLIs differ | [profiles/README.md](profiles/README.md) |
| Safety hooks | [docs/HOOKS.md](docs/HOOKS.md) |

### Capability profiles (short)

| Profile | You have | Workers |
|---------|----------|---------|
| `full` | AGY + Grok + Codex | Fast + main write + review |
| `claude-codex` | Codex | Write + review via Codex |
| `claude-only` | Claude only | Claude subagents (slower, still OK) |

```bash
agents-doctor          # show detection
agents-doctor --apply .  # save profile into the project
```

### Layout (for the curious)

```text
.agents/runs/<job>/     # factory floor — tasks, reports, merge notes
docs/plans/             # strategy / long plans (not the factory floor)
CLAUDE.md               # short always-on project rules
AGENTS.md               # “read CLAUDE.md” for other tools
```

---

## Security

No secrets in task files. Prefer review for auth/payments/schema. See [SECURITY.md](SECURITY.md).

## License

MIT — [LICENSE](LICENSE).

---

<p align="center">
  <img src="https://avatars.githubusercontent.com/u/17155104?v=4" width="64" height="64" alt="VKirill" style="border-radius:50%" /><br/>
  <a href="https://github.com/VKirill">@VKirill</a> ·
  <a href="https://t.me/pomogay_marketing">Помогающий маркетолог</a><br/>
  <em>A factory for solo operators — not another chat window.</em>
</p>
