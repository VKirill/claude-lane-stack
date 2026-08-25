<div align="center">

<img src="docs/images/00-banner.jpg" alt="Claude Lane Stack" width="100%" />

<br/>

# Claude Lane Stack

### A small AI coding factory for one person

**One human. One AI project manager. Real CLI coding agents on a durable conveyor.**  
Talk to Claude Code — it runs Codex / Qwen / Grok / Kimi / AGY, checks work, **merges to `main`**, reviews at night.

<p>
  <a href="https://github.com/VKirill/claude-lane-stack/releases/tag/v1.16.0"><img src="https://img.shields.io/badge/version-v1.16.0-orange?style=for-the-badge" alt="version" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue?style=for-the-badge" alt="license" /></a>
  <a href="https://code.claude.com/docs"><img src="https://img.shields.io/badge/PM-Claude%20Code-111?style=for-the-badge" alt="Claude Code" /></a>
  <a href="https://github.com/openai/codex"><img src="https://img.shields.io/badge/Review-Codex%20CLI-412991?style=for-the-badge" alt="Codex" /></a>
  <a href="https://t.me/pomogay_marketing"><img src="https://img.shields.io/badge/Telegram-channel-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram" /></a>
</p>

<p>
  <a href="README.ru.md"><strong>🇷🇺 Русский</strong></a>
  &nbsp;·&nbsp;
  <a href="docs/BEGINNER.md"><strong>🐣 Beginner guide</strong></a>
  &nbsp;·&nbsp;
  <a href="CHANGELOG.md"><strong>Changelog</strong></a>
  &nbsp;·&nbsp;
  <a href="https://github.com/VKirill/claude-lane-stack/stargazers"><strong>★ Star</strong></a>
</p>

</div>

---

<br/>

<div align="center">
<img src="docs/images/06-feature-cards.jpg" alt="Factory · ownership · night review · merge to main" width="100%" />
</div>

<br/>

| | | | |
|:--:|:--:|:--:|:--:|
| **🏭 Factory, not five chats** | **🛡️ Owned paths** | **🌙 Night review** | **📦 Auto-merge to main** |
| One PM holds context | Writers stay in their lane | Independent Codex Sol rail | You never merge by hand |

---

## ✨ Why this exists

Working with AI coding tools usually means: five windows, copy-paste, midnight merges, and zero review discipline.

**Claude Lane Stack turns that into a conveyor** — plain **files + git**, no mandatory cloud DB.

| 😩 Typical AI coding | ✨ Lane Stack |
|----------------------|----------------|
| Re-explain context every chat | **One PM** holds the plan |
| Models overwrite each other | **`owns_paths`** on every task |
| Nobody reviews the AI | **Typed night shift** (review → fix → re-review) |
| You merge branches | **PM merges `main`** after checks |
| “What were we doing?” | **`resume-project`** → Now / Blocked / Next |
| Jobs die at ~2 min Bash | **Detached processes** (survive chat close) |

> [!TIP]
> New here? Start with the **[Beginner guide](docs/BEGINNER.md)** — zero jargon, factory metaphors.

---

## 🔌 CLI agents we plug into

<div align="center">
<img src="docs/images/05-cli-constellation.jpg" alt="Claude Code control plane with Codex Qwen Grok Kimi AGY writers" width="100%" />
</div>

<br/>

This is **not** “one model does everything.”  
The stack is a **control plane** that runs **real CLI coding agents** as durable processes.

| CLI | Required? | Role |
|-----|-----------|------|
| **[Claude Code](https://code.claude.com/docs)** | **Yes** | PM (`dev-orchestrator`), watchers, chat with you |
| **[OpenAI Codex CLI](https://github.com/openai/codex)** | Optional | Day writer · **night Sol review** · onboard · docs · emergency |
| **Qwen Code** | Optional | Daytime durable **writer** |
| **Grok** (xAI CLI) | Optional | Daytime durable **writer** |
| **Kimi** CLI | Optional | Daytime durable **writer** (often full-profile default) |
| **AGY** (Gemini-oriented) | Optional | Daytime durable **writer** |

```text
  You ──chat──►  Claude Code · dev-orchestrator          ← always
                        │
              run-supervisor + run-controller
          ┌─────┬─────┬─────┬─────┐
          ▼     ▼     ▼     ▼     ▼
       Codex  Qwen  Grok  Kimi   AGY
          │     │     │     │     │
          └─────┴─────┴─────┴─────┘
                        │
              owns → L1 verify → acceptance → main
```

- **Mix and match** — install what you pay for; `agents-doctor` / `adoc` builds the profile  
- **One protocol** — owns, verify, `acceptance.json`, progressive accept  
- **Switch writer** — change `main_write` in adoc (e.g. `codex` → `qwen`)  
- **Codex for night quality** when available  

<details>
<summary><strong>Profiles (examples)</strong></summary>

| Profile | Writers | Review |
|---------|---------|--------|
| `claude-only` | Claude only | light |
| `claude-codex` | Codex process | Codex Sol night |
| `claude-qwen` / `grok` / `kimi` / `agy` | that CLI | as configured |
| `full` | multi-writer ready | Codex night |

</details>

---

## 🧠 How it works (60 seconds)

<div align="center">
<img src="docs/images/02-how-it-works.jpg" alt="Flow: You → PM → supervisor → writer → main" width="100%" />
</div>

<br/>

```text
You (chat)  →  PM (dev-orchestrator)
                  │  plan-critique · task YAML in .agents/runs/
                  ▼
            run-supervisor   ← Claude watches one run
                  │
                  ▼
            run-controller   ← durable OS process
                  │
                  ▼
         writer CLI process  ← codex / qwen / grok / …
                  │
                  ▼
         owns → L1 tests → acceptance.json
                  │
                  ▼
            PM merges → main → (night) Codex review
```

**You don’t hand-launch “Qwen the coder” for normal work.**  
You talk to the PM. The PM starts the **conveyor**. The writer is a **background process**, not a random brand-named subagent.

---

## ☀️ Day vs 🌙 night

<div align="center">
<img src="docs/images/03-day-night.jpg" alt="Daytime conveyor and night Codex review" width="100%" />
</div>

<br/>

| | **Day** | **Night** |
|--|---------|-----------|
| Goal | Ship fast | Independent quality |
| Product code | Writer from **adoc** | Repair after findings |
| Watch | **`run-supervisor`** | `night-shift` |
| LLM review every commit? | **No** | **Yes** — Codex Sol |
| Done | `acceptance.json` + **main** | Finding fixed + re-review |

---

## 🎭 Who is who

| Role | Kind | Does |
|------|------|------|
| **You** | Human | Say *what* you want |
| **`dev-orchestrator`** | Claude agent (PM) | Plan · dispatch · merge · chat |
| **`run-supervisor`** | Claude (watch) | One run until accepted/blocked |
| **`run-controller`** | OS process | DAG · retry · owns/verify/accept |
| **Writer process** | CLI (Codex/Qwen/…) | Implements the task card |
| **`lane-supervisor`** | Claude (1 action) | Typed `lane-ctl` recovery |
| **`emergency-writer`** | Claude → Codex | After **terminal** block only |
| **`night-reviewer` / night-shift** | Codex Sol | Night review + findings |
| **`project-onboarder`** | Codex | Project passport |
| **`docs-maintainer`** | Codex | Docs refresh |

Built-ins Claude may also use: **Explore**, **Plan**, **general-purpose** (research / side tasks — **not** the daytime product conveyor).  
Aliases: `codex-implementer` → `emergency-writer`, etc. → [`agents/claude/README.md`](agents/claude/README.md)

---

## 📋 Task card = contract

<div align="center">
<img src="docs/images/04-task-contract.jpg" alt="Task YAML owns_paths verification" width="100%" />
</div>

<br/>

Every unit of work lives under `.agents/runs/<slug>/tasks/*.yaml`:

| Field | Meaning |
|-------|---------|
| `owns_paths` | Files this task may touch |
| `verification[]` | Focused L1 checks |
| `lane:` | Matches adoc `main_write` |
| Receipts | report → owns → verify → **`acceptance.json`** |

> [!IMPORTANT]
> No `acceptance.json` → **not done**. Chat green ≠ shipped.

---

## 🚀 Quick start

### ① Install once

This repo **is a Claude Code plugin marketplace**. `./install.sh` installs the host runtime (`~/.agents`) **and** the Claude plugin.

```bash
git clone https://github.com/VKirill/claude-lane-stack.git
cd claude-lane-stack && git checkout v1.16.0   # or: main
./install.sh
export PATH="$HOME/.agents/bin:$PATH"
```

After install, Claude Code has **`lane-stack@claude-lane-stack`**. Skills are `/lane-stack:<name>` (example: `/lane-stack:orchestrator-lanes`). Marketplace checkout: `~/.claude/plugins/marketplaces/claude-lane-stack`.

Plugin-only (runtime already on the machine):

```bash
claude plugin marketplace add VKirill/claude-lane-stack
claude plugin install lane-stack@claude-lane-stack -y
```

From a local clone: `claude plugin marketplace add .` then the same `install` line. Reload with `/reload-plugins`.

**Needs:** Claude Code · Git · Python 3 (+ PyYAML/jsonschema) · Node · rsync · `flock`  
**Optional:** Codex · Qwen · Grok · Kimi · AGY · Linux: `bubblewrap`

### ② Prepare your project once

```bash
cd /path/to/your-project
agents-doctor --apply .     # or: adoc
```

### ③ Start the PM

```bash
# if you use the host launcher:
cc                          # menu → 1 = dev-orchestrator

# or raw:
claude --agent dev-orchestrator --name lane-pm-myproject
```

| In chat | When |
|---------|------|
| `/project-onboard` | First time on a repo |
| `/resume-project` | After a break |
| “Add dark mode to settings” | Normal feature work |

---

## ⚙️ adoc (simple)

| Knob | Meaning |
|------|---------|
| **Writer** `main_write` | `codex` / `qwen` / `grok` / `kimi` / `agy` |
| **Model / effort** | e.g. Codex luna + max |
| **Fast mode** | Codex `service_tier: fast` |
| **Workspace** | `in_place` · `worktree` · `auto` |
| **Plan critique** | off · structural · LLM before dispatch |

---

## 🧰 Commands cheat sheet

| Command | Purpose |
|---------|---------|
| `agents-doctor` / `adoc` | Detect CLIs · write profile |
| `resume-project .` | Now / Blocked / Next |
| `run-init` · `run-validate` · `run-board` | Runs (usually via PM) |
| `run-controller start\|watch\|status` | Durable lifecycle |
| `lane-ctl …` | Typed control plane |
| `night-shift` · `night-shift-all` | Night review/repair |
| `plan-critique --run-dir …` | Plan quality gate |

---

## ❓ FAQ

<details>
<summary><strong>Plugin or <code>~/.agents</code>?</strong></summary>

**Claude-facing** (PM agents, playbook skills, `/project-onboard`) ships as plugin `lane-stack` in marketplace `claude-lane-stack`. **Host runtime** (`bin/`, board, writer profiles) still lives in `~/.agents`. `./install.sh` does both. Do not copy stack agents into `~/.claude/agents` — those copies override the plugin.
</details>

<details>
<summary><strong>Do I need every CLI?</strong></summary>

No. **Claude Code alone** works (`claude-only`). Each extra CLI is a pluggable writer (or Codex review rail).
</details>

<details>
<summary><strong>What is <code>general-purpose</code>?</strong></summary>

A **built-in** Claude Code subagent for multi-step side tasks ([docs](https://code.claude.com/docs/en/sub-agents#general-purpose)). PM may use it for research. Product features still go through the conveyor.
</details>

<details>
<summary><strong>Why ~2 minute Bash death?</strong></summary>

Claude Code host limit. Writers run **detached**. Don’t keep long jobs in the PM foreground.
</details>

<details>
<summary><strong>Who merges?</strong></summary>

The **PM**. You never merge. If it asks you to — the PM is wrong.
</details>

<details>
<summary><strong>Language?</strong></summary>

Chat: any language. Agent-written files: **English** ([LANGUAGE.md](docs/LANGUAGE.md)).
</details>

---

## 📚 Documentation

| Doc | For |
|-----|-----|
| [BEGINNER.md](docs/BEGINNER.md) | Zero-jargon tour |
| [SOLO-ORCHESTRATION.md](docs/SOLO-ORCHESTRATION.md) | Day / night rules |
| [ROUTING.md](docs/ROUTING.md) | Models & profiles |
| [LANE-EXEC.md](docs/LANE-EXEC.md) | Process survival |
| [PLATFORM-CAPABILITIES.md](docs/PLATFORM-CAPABILITIES.md) | Claude Code + Codex features |
| [FILE-CONTRACT.md](docs/FILE-CONTRACT.md) | Layout & receipts |
| [agents/claude/README.md](agents/claude/README.md) | Role agent names |
| [plugins/lane-stack/README.md](plugins/lane-stack/README.md) | Claude plugin layout |
| [CHANGELOG.md](CHANGELOG.md) | Releases |

---

## 🤝 Contributing & community

- [Contributing](CONTRIBUTING.md) · [Code of Conduct](CODE_OF_CONDUCT.md) · [Security](SECURITY.md)
- Issues: use the templates · PRs welcome with tests + docs
- Channel: [Помогающий маркетолог](https://t.me/pomogay_marketing)

---

<div align="center">

**MIT** © [VKirill](https://github.com/VKirill) and contributors

<br/>

<a href="https://github.com/VKirill/claude-lane-stack">
  <img src="docs/images/01-hero-conveyor.jpg" alt="Claude Lane Stack conveyor" width="85%" />
</a>

<br/><br/>

### If this factory helps you — ★ star the repo

It helps others find a calmer way to multi-agent coding.

</div>
