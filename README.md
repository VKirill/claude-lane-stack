<div align="center">

<img src="docs/images/01-hero-conveyor.jpg" alt="Claude Lane Stack — one human, one AI PM, durable writer lanes, auto-merge to main" width="100%" />

# Claude Lane Stack

### A small AI coding factory for one person · **v1.14.13**

You talk to **one** AI project manager. It plans work, runs durable AI writers
(Codex / Qwen / Grok / Kimi / AGY — whatever you installed), checks results,
**merges to `main`**, and runs independent review at night.

No five chat windows. No hand-merging branches. Everything lives as **files + git**.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/VKirill/claude-lane-stack?color=orange&label=Release)](https://github.com/VKirill/claude-lane-stack/releases/tag/v1.14.13)
[![Claude Code](https://img.shields.io/badge/PM-Claude%20Code-black)](https://code.claude.com/docs)
[![Telegram](https://img.shields.io/badge/Telegram-Помогающий%20маркетолог-2CA5E0?logo=telegram)](https://t.me/pomogay_marketing)

**Languages:** [English](README.md) · [Русский](README.ru.md)  
**Beginner walkthrough:** [EN](docs/BEGINNER.md) · [RU](docs/BEGINNER.ru.md)

</div>

---

## Why bother?

| Usual AI coding | Claude Lane Stack |
|-----------------|-------------------|
| Five chats, re-explain context every time | **One PM** holds the plan |
| Models overwrite each other’s files | Each task has **owned paths** |
| Nobody reviews the AI | **Night shift** (Codex review → fix → re-review) |
| You merge branches at midnight | **PM merges `main`** after checks |
| “What were we doing?” next morning | **`resume-project`** → Now / Blocked / Next |
| Long jobs die after ~2 minutes in Claude Bash | **Detached processes** (survive when you close the chat) |

---

## 60-second mental model

<div align="center">
<img src="docs/images/02-how-it-works.jpg" alt="You → PM → run-supervisor → writer process → main" width="100%" />
</div>

```text
You (chat)  →  PM (dev-orchestrator)
                    │
                    ├─ plan-critique (optional LLM plan check)
                    ├─ task YAML cards in .agents/runs/<slug>/
                    │
                    ▼
              run-supervisor  (watches one run)
                    │
                    ▼
              run-controller  (durable process)
                    │
                    ▼
         writer process (codex / qwen / grok / …)
                    │
                    ▼
         owns check → L1 tests → acceptance.json
                    │
                    ▼
              PM merges → main  →  (night) Codex review
```

**You never start “Qwen the coder” by hand for normal work.**  
You talk to the PM. The PM starts the **conveyor**. The writer is a **background process**, not a random Claude subagent named after a model brand.

---

## Day vs night

<div align="center">
<img src="docs/images/03-day-night.jpg" alt="Daytime conveyor and night Codex review" width="100%" />
</div>

| | **Day** | **Night** |
|--|---------|-----------|
| Goal | Ship features fast | Independent quality |
| Who writes product code | Writer process from **adoc** profile | Repair writer after review findings |
| Who “watches” | **`run-supervisor`** | `night-shift` / `night-shift-all` |
| LLM review of every commit? | **No** (by design) | **Yes** — Codex Sol, typed findings |
| Done means | `acceptance.json` + merge to `main` | Finding fixed + re-review |

---

## Who is who (roles, not brand names)

| Role | What it is | What it does |
|------|------------|--------------|
| **You** | Human | Say *what* you want |
| **`dev-orchestrator`** | Claude Code agent (PM) | Plan, dispatch, merge, talk to you |
| **`run-supervisor`** | Claude agent (watch only) | Starts/watches `run-controller` until accepted/blocked |
| **`run-controller`** | OS process | DAG, retries, owns/verify/accept |
| **Writer process** | Codex / Qwen / Grok / Kimi / AGY CLI | Implements the task card |
| **`lane-supervisor`** | Claude agent (one action) | Manual `lane-ctl` status/retry/verify/… |
| **`emergency-writer`** | Claude → Codex shell-out | Only after a **terminal** block |
| **`night-reviewer` / night-shift** | Codex Sol | Night review + findings |
| **`project-onboarder`** | Codex | First-time project passport |
| **`docs-maintainer`** | Codex | Docs refresh |

Built-in Claude helpers the PM may also use: **Explore**, **Plan**, **general-purpose** (research / side tasks — **not** a substitute for the daytime product conveyor).

Deprecated aliases (still work): `codex-implementer` → `emergency-writer`, `codex-reviewer` → `night-reviewer`, etc. See [`agents/claude/README.md`](agents/claude/README.md).

---

## Task card = the contract

<div align="center">
<img src="docs/images/04-task-contract.jpg" alt="Task YAML owns_paths verification contract" width="100%" />
</div>

Every unit of work is a YAML file under `.agents/runs/<slug>/tasks/`:

- **`owns_paths`** — files this task may change (no stepping on siblings)
- **`verification[]`** — focused L1 checks the controller runs
- **`lane:`** — must match adoc `main_write` (e.g. `codex`, `qwen`)
- **Receipts** — report → owns-check → verification → **`acceptance.json`**

No acceptance → not done. Chat green ≠ shipped.

---

## Quick start

### 1) Install once (on the machine)

```bash
git clone https://github.com/VKirill/claude-lane-stack.git
cd claude-lane-stack
git checkout v1.14.13   # or: main
./install.sh
export PATH="$HOME/.agents/bin:$PATH"
```

Needs: **Claude Code**, Git, Python 3 (+ PyYAML/jsonschema), Node, rsync, `flock`.  
Optional writers: Codex, Qwen, Grok, Kimi, AGY. On Linux, writers need **bubblewrap**.

### 2) Prepare *your* project once

```bash
cd /path/to/your-project
agents-doctor --apply .    # or: adoc
```

This writes `.agents/routing.profile.yaml` (who writes, model, workspace mode, plan critique…).

### 3) Start the PM

**Recommended** (host launcher if you have `cc`):

```bash
cd /path/to/your-project
cc          # menu → pick 1 = dev-orchestrator
```

Or raw Claude Code:

```bash
claude --agent dev-orchestrator --name lane-pm-myproject
```

Then in chat:

| You say / run | When |
|---------------|------|
| `/project-onboard` or “onboard this repo” | First time |
| `/resume-project` or “where were we?” | After a break |
| “Add dark mode to settings” | Normal feature work |

The PM will: plan → (optional plan-critique) → task cards → **one** `run-supervisor` → wait for terminal digest → merge `main` when green.

---

## What you configure in `adoc` (simple)

| Setting | Meaning |
|---------|---------|
| **Writer** (`main_write`) | `codex` / `qwen` / `grok` / `kimi` / `agy` — the **process** that codes |
| **Model / effort** | e.g. Codex luna + max |
| **Fast mode** | Codex only — `service_tier: fast` (speed credits) |
| **Workspace** | `in_place` / `worktree` / `auto` |
| **Plan critique** | Off / structural / or LLM (qwen/codex/…) before dispatch |

Changing adoc mid-session updates YAML; a **long-lived** PM may need a nudge to re-read profile.

---

## Commands you’ll actually use

| Command | Role |
|---------|------|
| `agents-doctor` / `adoc` | Pick writers + profile |
| `resume-project .` | Now / Blocked / Next |
| `run-init` / `run-validate` / `run-board` | Runs (usually the PM does this) |
| `run-controller start\|watch\|status` | Durable lifecycle (PM uses via `run-supervisor`) |
| `lane-ctl …` | Typed lane control plane |
| `night-shift` / `night-shift-all` | Night review/repair |
| `plan-critique --run-dir …` | Plan quality gate |

Deep dives: [LANE-EXEC](docs/LANE-EXEC.md) · [ROUTING](docs/ROUTING.md) · [SOLO-ORCHESTRATION](docs/SOLO-ORCHESTRATION.md) · [PLATFORM-CAPABILITIES](docs/PLATFORM-CAPABILITIES.md) · [FILE-CONTRACT](docs/FILE-CONTRACT.md)

---

## FAQ (slippers edition)

**Do I need all of Codex + Qwen + Grok?**  
No. Claude Code alone works (`claude-only` profile). Add writers as you like; `agents-doctor` adapts.

**Why not let Claude just edit the code?**  
You can for tiny notes. For real features the stack keeps **ownership, tests, and receipts** so parallel work doesn’t trash `main`.

**What is `general-purpose`?**  
A **built-in** Claude Code subagent for multi-step side tasks ([docs](https://code.claude.com/docs/en/sub-agents#general-purpose)). The PM may use it for research. Product features still go through the conveyor.

**Foreground Bash dies at ~2 minutes?**  
Yes — that’s Claude Code. Writers run **detached** (`lane-bg` / systemd). Don’t keep long jobs in the PM’s foreground shell.

**Who merges?**  
The PM. You never merge. If it asks you to merge, the PM is wrong — fix the skill.

**Language?**  
Chat: any language (RU is fine). Files the agents write: **English**.

---

## Docs map

| Doc | For |
|-----|-----|
| [BEGINNER.md](docs/BEGINNER.md) | Zero jargon tour |
| [SOLO-ORCHESTRATION.md](docs/SOLO-ORCHESTRATION.md) | Day/night rules |
| [ROUTING.md](docs/ROUTING.md) | Models & profiles |
| [LANE-EXEC.md](docs/LANE-EXEC.md) | Process survival |
| [PLATFORM-CAPABILITIES.md](docs/PLATFORM-CAPABILITIES.md) | Claude Code + Codex features we use |
| [agents/claude/README.md](agents/claude/README.md) | Role agent names |
| [CHANGELOG.md](CHANGELOG.md) | What changed |

---

## License

[MIT](LICENSE) · Author: [VKirill](https://github.com/VKirill) · Channel: [Помогающий маркетолог](https://t.me/pomogay_marketing)
