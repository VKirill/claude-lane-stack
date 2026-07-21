<div align="center">

<img src="docs/images/01-hero-conveyor.jpg" alt="Claude Lane Stack — a multi-agent AI coding conveyor: one human, one AI project manager, worker lanes, auto-merge to main" width="100%" />

# 🏭 Claude Lane Stack

### A small AI coding factory for one person · **v1.6.0**

**Multi-agent orchestration for Claude Code** — you talk to one AI project
manager, it runs durable AGY or Grok work through acceptance, **merges finished code to
`main`**, and sends independent review/fixes through the night shift. No five
chats. No manual merges.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/VKirill/claude-lane-stack?color=orange&label=Release)](https://github.com/VKirill/claude-lane-stack/releases/tag/v1.6.0)
[![Claude Code](https://img.shields.io/badge/PM-Claude%20Code-black)](https://docs.anthropic.com/en/docs/claude-code)
[![Beginner guide](https://img.shields.io/badge/Start%20here-Beginner%20guide-brightgreen)](docs/BEGINNER.md)
[![Telegram](https://img.shields.io/badge/Telegram-Помогающий%20маркетолог-2CA5E0?logo=telegram)](https://t.me/pomogay_marketing)

🌍 **README:** [Русский](README.ru.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [Español](README.es.md) · [Deutsch](README.de.md) · [Français](README.fr.md) · [한국어](README.ko.md) · [Português](README.pt-BR.md) 
🐣 **Beginner guide:** [EN](docs/BEGINNER.md) · [RU](docs/BEGINNER.ru.md) · [中文](docs/BEGINNER.zh-CN.md) · [日本語](docs/BEGINNER.ja.md) · [ES](docs/BEGINNER.es.md) · [DE](docs/BEGINNER.de.md) · [FR](docs/BEGINNER.fr.md) · [KO](docs/BEGINNER.ko.md) · [PT](docs/BEGINNER.pt-BR.md)

</div>

---

## 📌 Table of contents

- [Why this exists](#-why-this-exists) · [Who it's for](#-who-its-for) · [How it works](#-how-it-works)
- [Quick start](#-quick-start-3-commands) · [Onboard 2.0](#-onboard-20--scenario--depth) · [Lanes that finish](#-lanes-that-finish--background-survival) · [Progressive accept](#-progressive-accept--no-join-wait)
- [Task cards](#-task-cards-how-workers-stay-in-their-lane) · [You never merge](#-you-never-merge--the-pm-does)
- [Cheat sheet](#-commands-cheat-sheet) · [Profiles](#-capability-profiles) · [FAQ](#-faq) · [Docs](#-documentation-map)

---

## 💡 Why this exists

Working with AI coding tools usually looks like this: five chat windows, copy-pasted snippets, branches you merge by hand at midnight, and no one checking anyone's work.

**Claude Lane Stack turns that into a conveyor:**

| 😩 Five chats | 🏭 Lane Stack |
|---------------|---------------|
| You re-explain context to every model | One PM holds context, workers get **task cards** |
| Models overwrite each other's files | Each card lists **owned paths** — workers stay in their lane |
| Nobody reviews the AI's code | A typed **night review/fix loop** (Codex → AGY/Grok → re-review) |
| You merge branches manually | The PM merges to **`main`** after checks pass |
| Next morning: "what were we doing?" | `/resume-project` — Now / Blocked / Next in seconds |
| Onboard is a thin CLAUDE stub | **Deep forensic passport** on mature repos |
| Long writer runs die at ~2 min | **`run-controller` + user-systemd** — the whole lifecycle survives host cleanup |
| You cannot tell if work is alive | One visible **`run-supervisor`** + exact Board runtime stages |
| Parallel tasks wait for the slowest | **Progressive accept** — detached AGY/Grok + separate provider/verify pools |

No task database. No required cloud service. **Plain files + plain git** — everything is inspectable in your repo.

---

## 👥 Who it's for

- 🧑‍💻 **Solo developers** who want an agentic coding workflow — parallel AI agents without chat chaos
- 🚀 **Indie hackers** who'd rather describe features than babysit branches
- 🧠 **Vibe-coders** — you know *what* you want; the factory handles *how*
- 🏢 **A one-person agency** running several client repos with the same discipline

> [!TIP]
> Never heard the word "orchestration"? Start with the **[Beginner guide](docs/BEGINNER.md)** — it explains everything as a small factory, zero jargon.

---

## 🧩 How it works

<div align="center">
<img src="docs/images/02-lanes-routing.jpg" alt="Three worker lanes — fast write, heavy write, review — merging into the main branch under the PM's control" width="90%" />
</div>

You talk to **one agent** — `dev-orchestrator`, the project manager. It routes work across lanes:

```mermaid
flowchart LR
    subgraph you ["🧑 You"]
        A["Plain language:<br/>«add dark mode»"]
    end
    subgraph pm ["🤖 PM — dev-orchestrator"]
        B["Plan → task cards<br/>.agents/runs/"]
    end
    subgraph lanes ["👷 Worker lanes (optional)"]
        D["🔧 AGY / Grok — heavy writes"]
        E["🌙 Codex — night review"]
    end
    A --> B
    B --> D
    D -->|exact checks| F[("📦 main")]
    F -.-> E
    E -.->|typed findings / writer fixes| B
```

| Role | Who | What they do |
|------|-----|--------------|
| 👑 Owner | **You** | Say *what* you want (chat may be any language) |
| 🤖 Project manager | Claude Code agent `dev-orchestrator` | Plans, dispatches, verifies, **merges** |
| 🔧 Write lane | AGY 3.6 or Grok *(optional)* | Implement task cards (detached via `lane-bg`) |
| 🔍 Review / write / onboard | Codex *(optional)* | Night review/re-review, emergency write, **project passport** |
| 🗂️ Task cards | YAML in `.agents/runs/` | Factory floor — fully inspectable |
| 📦 Official code | Git branch **`main`** | Where every successful job ends |

**Language policy:** durable files (contracts, CLAUDE, reports, docs) are **English**. Chat with the human may be **Russian** (or your language) — the PM translates. See [docs/LANGUAGE.md](docs/LANGUAGE.md).

**Models (Codex):** GPT-**5.6** only — **Sol** (review / deep / high-risk), **Terra** (scoped write / docs), **Luna** (trivia only). No 5.5. See [docs/ROUTING.md](docs/ROUTING.md).

> [!NOTE]
> **Only Claude Code is required.** Missing workers are fine — `agents-doctor` detects what's installed and the PM adapts, down to pure `claude-only` mode.
> Linux AGY/Grok writer lanes additionally require `bubblewrap` (`sudo apt install
> bubblewrap` on Ubuntu) for the read-only `.agents` boundary.

---

## 🚀 Quick start (3 commands)

```bash
# 1️⃣  Install the stack — once per computer
git clone https://github.com/VKirill/claude-lane-stack.git
cd claude-lane-stack && git checkout v1.6.0 # or: main
./install.sh
export PATH="$HOME/.agents/bin:$PATH" # or open a new terminal

# 2️⃣  In YOUR project — detect available workers, once per repo
cd /path/to/your-project
agents-doctor --apply .

# 3️⃣  Start the PM and talk normally
claude --agent dev-orchestrator
```

Then in chat:

| Command | When |
|---------|------|
| **`/project-onboard`** | First time on a repo — passport + docs (auto **minimal/full** + **fast/deep**) |
| **`/project-onboard deep`** | Force forensic analysis |
| **`/resume-project`** | Cold start after a break — Now / Blocked / Next |

> [!IMPORTANT]
> `/resume-project` is a *"welcome back"* command — **not** an installation step.

📖 Walkthrough: **[docs/BEGINNER.md](docs/BEGINNER.md)** · Release notes: **[v1.6.0](https://github.com/VKirill/claude-lane-stack/releases/tag/v1.6.0)**

---

## 🧭 Onboard 2.0 — scenario + depth

First-time setup is not a thin stub. **`project-onboard` + Codex** build a real passport.

### Axis 1 — Scenario (*what* to seed)

| | 🟢 **minimal** | 🟣 **full** |
|--|----------------|-------------|
| When | score &lt; 5 (small / greenfield) | score ≥ 5 or multi-package monorepo |
| Seeds | CLAUDE · AGENTS · ARCHITECTURE · memory · plans | + GOTCHAS · GLOSSARY · TESTING · deployment · nested `apps/*/CLAUDE.md` · SECURITY when domain-heavy |

### Axis 2 — Depth (*how hard* Codex digs)

| | ⚡ **fast** | 🔬 **deep** (default on full) |
|--|------------|--------------------------------|
| Explore | top dirs + manifests | entrypoints, top modules, 3–7 flows, wiki↔code, run tests |
| Model | `gpt-5.6-terra` high | `gpt-5.6-sol` high |
| Report | passport filled | MODULES_READ · FLOWS · WIKI_MISMATCHES · VERIFY |

```bash
project-onboard . # auto scenario + depth
project-onboard . --deep # force forensic
project-onboard . --minimal --fast
```

Writes:

- `.agents/onboard.scenario.yaml` — `scenario` + `depth` + score 
- `.agents/runs/_onboard/artifacts/001/deep-scan.md` — evidence pack for Codex 
- Prefer **pointers** to existing wiki (`gotchas.md`) over UPPERCASE duplicates 

Full guide: [docs/ONBOARD-SCENARIOS.md](docs/ONBOARD-SCENARIOS.md)

---

## 🏃 Lanes that finish — background survival

Claude Code **kills foreground Bash around ~2 minutes**. That is a **host** limit, not `lane-exec`.

Long AGY/Grok jobs start through the typed control plane. AGY 3.6 is the
default; choose Grok explicitly with `--provider grok`:

```bash
RUN_DIR="$(run-init "$(pwd)" "$SLUG" --score 7)"
run-validate --run-dir "$RUN_DIR" --phase pre-dispatch
run-controller start --run-dir "$RUN_DIR" --project-cwd "$PROJECT_CWD" --provider agy
run-controller watch --run-dir "$RUN_DIR" --timeout 240
run-controller status --run-dir "$RUN_DIR" --json
```

| Tool | Role |
|------|------|
| **`run-controller`** | durable DAG dispatch, persisted AGY/Grok retry, typed Codex fallback, progressive owns/verify/accept |
| **`lane-ctl`** | typed start/status/events/tail/retry/fallback/cancel/verify/accept control plane |
| **`lane-bg`** | low-level transient user-systemd service; explicit nohup fallback |
| **`lane-exec`** | activity-aware idle + absolute max **on the detached process** |
| **`lane-session`** | resumes AGY/Grok context and runs one-shot Codex fallback; provider default 5/max 10 |

One read-only `run-supervisor` visibly watches the durable controller until the
run is accepted or blocked. `lane-supervisor` remains a one-action diagnostic
profile. Verification has a separate default 2/max 10 pool. Details:
[docs/LANE-EXEC.md](docs/LANE-EXEC.md)

AGY and Grok no longer relearn the repository on every task in a run. The first
task creates a conversation; later related tasks resume it. A busy conversation
is never shared concurrently—parallel tasks lease another slot (five by default,
configurable from one to ten).
Sessions rotate after seven successful tasks by default, on failure, or when the
worktree/model changes. Codex review stays independent and does not reuse writer
context.
For a sanitized model/catalog/quota/auth/transport availability failure, the
controller records a 30-second retry deadline, replays the exact selected
request once, then may use one fixed `gpt-5.6-sol` + `high` writer attempt. It
still requires the same report digest, ownership, verification, and acceptance
receipts; this is recovery, not silent model substitution or daytime review.

### Typed night shift

The unattended path is a receipt-driven review and repair loop:

```bash
night-shift /path/to/project          # one repository
night-shift-all --jobs 2              # active repositories, bounded 1–10
```

Codex uses the installed `night-review` profile: `gpt-5.6-sol`, `xhigh`,
read-only, approval `never`. It reviews bounded diff chunks and stores every
concrete or systemic issue under `.agents/findings/<fingerprint>.json`; daily
REVIEW, OPEN, and TODO files are projections. The selected AGY/Grok repair
writer runs without subagents in an isolated worktree. If two primary attempts
end in a classified model/catalog/quota/auth/transport availability failure,
the runner may use the same single fixed Codex Sol high recovery attempt as the
daytime controller. A finding closes only after registered verification,
ownership checks, a fresh Codex xhigh re-review, and `acceptance.json`.

Night merge/push is disabled unless the project opts in:

```yaml
# .agents/night-shift.yaml
auto_merge: false
verification_executables: [] # optional project-specific executable basenames
```

Unsafe generated shell commands become `needs_human`; they are never executed.
Schema-v2 verification is also enforced by `lane-ctl` itself: the allowlist is
snapshotted at start and the parsed argv runs directly without a shell.

---

## ⚡ Durable progressive accept — visible, no join-wait

Multi-task runs no longer wait for the **slowest** concurrent lane before accepting finished ones.

1. Source-read-only **`run-supervisor`** starts one durable controller and stays visible through bounded watches.
2. The detached controller releases `lane-bg → lane-exec → lane-session → provider` tasks from the DAG.
3. Complete report → ownership check → independent verification → acceptance; AGY/Grok retries once, then only eligible availability failures may use one Codex Sol high fallback.
4. `acceptance.json` is written immediately; the next ready task fills the free slot (provider default 5/max 10).

Claude uses one visible supervisor per **run**, not one agent per provider. The
deterministic controller survives if that Claude task or session exits. There is
no daytime LLM review; the typed night shift remains separate. See
[docs/LANE-EXEC.md](docs/LANE-EXEC.md) · [skills/orchestrator-lanes](skills/orchestrator-lanes/SKILL.md).

## 📋 Task cards: how workers stay in their lane

<div align="center">
<img src="docs/images/04-file-contracts.jpg" alt="Each worker cell has a job card — a YAML contract listing goal, owned files and verification commands" width="90%" />
</div>

Every job is a small **YAML contract** in `.agents/runs/` — created by the PM, obeyed by workers (**English**):

```yaml
schema_version: 2
id: "001"
title: Add dark mode
risk: low
lane: agy              # default writer; grok remains supported
project_cwd: /absolute/path/to/worktree
read_first: [AGENTS.md]
interfaces: ["ThemeToggle(settings)"]
invariants: ["Existing light theme remains the default"]
out_of_scope: ["Server-side account preferences"]
expected_outputs: ["Persistent accessible theme toggle"]
objective: Dark theme toggle on the settings page
owns_paths: # 🔒 the ONLY files this worker may touch
  - src/settings/**
  - src/theme.css
never_touch:
  - .env*
depends_on: []
acceptance:
  - Theme choice persists across reloads
verify: tests
verification:
  - command: npm test
    cwd: /absolute/path/to/worktree
    timeout_sec: 600
```

- 🔒 `owns_paths` — parallel workers **can't collide**: `check-owns-paths` fails the task if a worker strays 
- ✅ `verify` — merge is blocked until checks pass 
- 📜 Cards stay in git history — audit trail of what every agent did 

Details: [docs/FILE-CONTRACT.md](docs/FILE-CONTRACT.md)

---

## 📦 You never merge — the PM does

<div align="center">
<img src="docs/images/03-auto-merge-main.jpg" alt="The PM robot places verified code into the main vault while the developer relaxes with coffee" width="90%" />
</div>

The end of every successful job is the same: **verified code lands on `main`**,
merged by the orchestrator via `wt-merge-main` after exact acceptance checks.
Independent review and repair run at night. Workers build in isolated **git worktrees**.

> [!WARNING]
> If an agent ever asks *you* to resolve branches — that's a bug in the flow. Tell the PM: *«merging is your job»*.

Rules: [docs/SOLO-ORCHESTRATION.md](docs/SOLO-ORCHESTRATION.md)

---

## 🧾 Commands cheat-sheet

### You type these

| Command / phrase | What it is | When |
|------------------|------------|------|
| `./install.sh` | Install kit into `~/.agents` | Once per computer |
| `agents-doctor --apply .` | Detect CLIs → routing profile | Once per project |
| `claude --agent dev-orchestrator` | **The only chat you need** | Every session |
| `/project-onboard` | Passport via Codex (scenario + depth auto) | First time on a repo |
| `/project-onboard deep` | Force forensic onboard | Mature / messy repos |
| *«Add dark mode…»* | Work request — any language | Features & fixes |
| `/resume-project` | Now / Blocked / Next | After a break |
| *«It's stuck»* | PM checks silent workers | Long silence |

<details>
<summary>🤖 <b>Usually only the PM / implementers type these</b></summary>

| Command | What it is |
|---------|------------|
| `run-board` | Job scoreboard |
| `run-init` / `run-validate` / `run-finalize` | Versioned run contract lifecycle |
| **`run-controller start/watch/status`** | Durable daytime lifecycle + exact live status |
| `lane-session status --run-dir .agents/runs/<slug>` | Inspect that run's AGY/Grok session pool |
| `wt-create` / `wt-merge-main` | Worktree + **merge into `main`** |
| `check-owns-paths` | Did the worker stay in its file list? |
| **`lane-ctl`** | Typed detached lifecycle control + verify + acceptance receipt |
| `lane-bg` / `lane-exec` / `lane-session` | Low-level process lifetime, activity timeouts, and warm provider pool |
| `lane-heartbeat` / `lane-stall-check` | Alive? Silent? |
| `project-onboard` | Shell seed + deep-scan (Codex fills) |
| `docs-maintain-project` | Nightly/daily docs honesty |
| `project-memory-init` | PROGRESS / LESSONS |
| `night-audit` | Housekeeping |
| `night-review` | Typed read-only review + canonical findings |
| `night-shift` / `night-shift-all` | Resumable review → AGY/Grok repair → re-review |

</details>

---

## 🚦 Capability profiles

`agents-doctor` detects both writer CLIs. It prefers AGY when both are healthy;
use `--writer-provider grok` to select Grok for a project.

| Profile | You have | Write lane | Review lane |
|---------|----------|------------|-------------|
| `full` | AGY and/or Grok + Codex | AGY default; Grok selectable | Codex Sol |
| `claude-agy` | AGY | AGY | Claude |
| `claude-grok` | Grok | Grok | Claude |
| `claude-codex` | Codex | Codex Terra/Sol | Codex Sol |
| `claude-only` | Claude Code only | Claude subagents | Claude subagents |

```bash
agents-doctor # report
agents-doctor --apply . # save into project
```

More: [profiles/README.md](profiles/README.md) · [docs/ROUTING.md](docs/ROUTING.md)

---

## 🧱 What's in the box

```text
claude-lane-stack/
├── agents/ # claude PM + agy/grok/codex lanes (implementers, onboard, review)
├── bin/ # agents-doctor, project-onboard, lane-ctl, lane-bg, lane-exec, lane-session,
│ # wt-*, run-board, docs-maintain-*, …
├── skills/ # orchestration, contracts, memory, onboard,, …
├── profiles/ # full → claude-only
├── hooks/ # shell guard, code-quality, session ledger
├── templates/ # ARCHITECTURE, GOTCHAS, TESTING, deployment, README anamnesis, …
├── docs/ # beginner + deep dives (table below)
└── install.sh # → ~/.agents
```

Inside **your** project after onboard:

```text
your-app/
├── CLAUDE.md # always-on rules (≤200 lines body)
├── AGENTS.md # pointer → CLAUDE.md
├── PROGRESS.md / LESSONS.md # living memory
├── .agents/
│ ├── onboard.scenario.yaml # scenario + depth + score
│ ├── routing.profile.yaml # agents-doctor
│ └── runs/ # 🏭 factory floor
└── docs/ # architecture, gotchas, deployment, plans/…
```

---

## ❓ FAQ

<details>
<summary><b>Do I need AGY, Grok, and Codex all installed?</b></summary>

No — **only Claude Code is required**. Everything else is optional. `agents-doctor` adapts down to `claude-only`.

</details>

<details>
<summary><b>How is this different from plain Claude Code?</b></summary>

Plain Claude is one worker in one chat. Lane Stack adds **management**: task
cards with ownership, durable parallel AGY/Grok lanes, a visible run supervisor,
nightly independent review/fix, auto-merge to `main`, deep onboard, and
cold-start recovery.

</details>

<details>
<summary><b>My run dies after ~2 minutes — is that lane-exec?</b></summary>

Usually **no**. Claude kills **foreground Bash** and may reap ordinary nohup descendants. Current runs start through **`lane-ctl`**, while `lane-bg` uses a transient user-systemd service. See [docs/LANE-EXEC.md](docs/LANE-EXEC.md). After upgrading, start a **fresh** dev-orchestrator session.

</details>

<details>
<summary><b>minimal vs full vs deep — which do I pick?</b></summary>

Usually nothing — **auto**. Toy repo → minimal + fast. Mature monorepo → full + deep. Override with `/project-onboard deep` or `project-onboard . --full --deep`.

</details>

<details>
<summary><b>Does it need a database or cloud service?</b></summary>

No. State is **files in your repo** (`.agents/runs/`) + git.

</details>

<details>
<summary><b>Will it work on my existing project?</b></summary>

Yes. `agents-doctor --apply .` then `/project-onboard`. Existing wiki pages are **linked**, not blindly duplicated (`gotchas.md` wins over `GOTCHAS.md`).

</details>

<details>
<summary><b>Is my code safe?</b></summary>

Each CLI talks only to its own vendor. No extra servers. Don't put secrets in task YAML; use the review lane for auth/pay. [SECURITY.md](SECURITY.md).

</details>

---

## 📚 Documentation map

| Topic | Doc |
|-------|------|
| 🐣 Plain-language walkthrough | [docs/BEGINNER.md](docs/BEGINNER.md) |
| 🧭 Onboard scenarios + depth | [docs/ONBOARD-SCENARIOS.md](docs/ONBOARD-SCENARIOS.md) |
| ⏱️ Lane timeouts + background | [docs/LANE-EXEC.md](docs/LANE-EXEC.md) |
| 🌐 Language policy (EN files / RU chat) | [docs/LANGUAGE.md](docs/LANGUAGE.md) |
| 🔀 Who writes / who reviews (Sol/Terra) | [docs/ROUTING.md](docs/ROUTING.md) |
| ⚖️ Comparison with alternatives | [docs/COMPARISON.md](docs/COMPARISON.md) |
| 🧑‍✈️ Solo rules — you never merge | [docs/SOLO-ORCHESTRATION.md](docs/SOLO-ORCHESTRATION.md) |
| 🗂️ Task card YAML | [docs/FILE-CONTRACT.md](docs/FILE-CONTRACT.md) |
| 🛡️ Safety hooks | [docs/HOOKS.md](docs/HOOKS.md) |
| 🧠 Project memory | [docs/PROJECT-MEMORY.md](docs/PROJECT-MEMORY.md) |
| 📝 Ideas backlog | [docs/TODOS.md](docs/TODOS.md) |<!-- guardian: allow — link to existing docs/TODOS.md file, not a new TODO marker -->
| 🔌 MCP (lean / hybrid) | [docs/MCP-LEAN.md](docs/MCP-LEAN.md) · [docs/MCP-HYBRID.md](docs/MCP-HYBRID.md) |
| 📰 Changelog | [CHANGELOG.md](CHANGELOG.md) |
| 🚀 Release v1.6.0 | [GitHub Releases](https://github.com/VKirill/claude-lane-stack/releases/tag/v1.6.0) |
| 🤝 Contributing | [CONTRIBUTING.md](CONTRIBUTING.md) |
| 🔐 Security | [SECURITY.md](SECURITY.md) |

---

## 📜 License

MIT — [LICENSE](LICENSE). Use it, fork it, build your own factory.

---

<div align="center">

<a href="https://github.com/VKirill"><img src="https://avatars.githubusercontent.com/u/17155104?v=4" width="88" height="88" alt="Кирилл Вечкасов" style="border-radius:50%" /></a>

**Кирилл Вечкасов** · [@VKirill](https://github.com/VKirill) · Telegram: [Помогающий маркетолог](https://t.me/pomogay_marketing)

*I build working conveyors, not another chat with an LLM.*

⭐ **If the conveyor idea clicks — star the repo.** It helps solo builders find it.

</div>
