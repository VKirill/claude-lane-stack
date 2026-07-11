# Beginner guide — Claude Lane Stack

**You do not need to be a multi-agent expert.**  
This page explains the system like a small factory: you talk to one manager, the manager assigns workers, finished work lands on the main branch for you.

Русская версия: [BEGINNER.ru.md](BEGINNER.ru.md)

---

## 1. What is “orchestration” in plain words?

| Everyday life | In this project |
|---------------|-----------------|
| You are the **owner of a shop** | You — the human |
| You hire a **project manager** | Claude Code agent `dev-orchestrator` |
| PM hires **builders, designers, inspectors** | Other AI tools: AGY, Grok, Codex |
| Work is written on **task cards**, not shouted across the room | Files in `.agents/runs/` |
| Finished goods go to the **main warehouse** | Git branch **`main`** |

**Orchestration** = the PM organizes who does what, checks the result, and puts the finished code into `main`.  
You do **not** run five chats and merge branches by hand.

---

## 2. Words you will see (glossary)

| Word | Simple meaning | When you care |
|------|----------------|---------------|
| **Agent** | An AI that can read/write code with tools | Always — they do the work |
| **PM / orchestrator** | The “boss” agent (`dev-orchestrator`) | You talk mostly to this one |
| **Lane** | A type of worker (fast write / main write / review) | When setup chooses AGY vs Grok vs Codex |
| **Claude Code** | Anthropic’s terminal coding app | **Required** — installs the PM |
| **AGY** | Google Antigravity CLI (fast/cheap writes) | Optional worker |
| **Grok** | xAI CLI (heavier implementation) | Optional worker |
| **Codex** | OpenAI CLI (review + project onboard) | Optional worker / onboard |
| **Task / contract** | A small YAML file: what to do, which files, how to check | PM creates these; workers read them |
| **`.agents/runs/`** | Folder of active jobs (the real “factory floor”) | After you ask to build something |
| **`docs/plans/`** | Long strategy notes (SEO, product), **not** the factory floor | Research first, then “implement” |
| **`main`** | The main git branch = “official” code | End of every successful job |
| **Worktree** | A separate copy of the repo for parallel work | PM uses this so agents don’t fight |
| **Merge** | Combining finished work into `main` | **PM does this**, not you |
| **Onboard** | First-time setup of project instructions | Once per repository |
| **Cold start / resume** | Continue after a break | Next day / new chat |

---

## 3. Commands — what they mean and when to run them

Run commands in a **terminal**, from your project folder (unless noted).

### A. One-time setup (new computer)

| Command | What it does | When |
|---------|--------------|------|
| `git clone https://github.com/VKirill/claude-lane-stack.git` | Downloads this stack | First time |
| `cd claude-lane-stack && ./install.sh` | Installs agents, skills, tools into your home folder | First time |
| `export PATH="$HOME/.agents/bin:$PATH"` | Makes tools like `agents-doctor` available | Every new terminal, or add to `~/.bashrc` once |

### B. One-time setup (each project / repo)

| Command | What it does | When |
|---------|--------------|------|
| `cd /path/to/your-project` | Go into **your** app’s folder | Always before project commands |
| `agents-doctor --apply .` | Checks which AI CLIs you have (Claude/AGY/Grok/Codex) and writes a **routing profile** | Once per project, or after installing a new CLI |
| `/project-onboard` inside Claude | Asks **Codex** to write `CLAUDE.md`, short docs, memory files | First time on a project (or when docs are empty) |
| `claude --agent dev-orchestrator` | Starts the **PM** chat for this folder | Every time you want the factory |

### C. Everyday work

| What you type | What happens | When |
|---------------|--------------|------|
| Plain language request to the PM, e.g. *«Add a login button on the settings page»* | PM plans, creates tasks, sends workers, checks, merges to `main` | Normal feature/bug work |
| `/resume-project` **or** `resume-project .` | Short summary: what was in progress, what is blocked, what to do next | **After a break**, new chat, next morning — *not* required on the very first install |
| «Проверь stall» / ask PM to check stalls | Finds workers that went silent | If nothing happens for a long time |

### D. Tools you rarely type yourself (PM uses them)

| Command | Meaning | Who runs it |
|---------|---------|-------------|
| `run-board` | Updates the scoreboard of jobs | PM or you if curious |
| `wt-create` | Creates an isolated work folder for a feature | PM |
| `wt-merge-main` | Merges finished work into `main` | **PM only** |
| `check-owns-paths` | Checks a worker didn’t edit “someone else’s” files | PM after a worker |
| `lane-heartbeat` / `lane-stall-check` | “Is the worker still alive?” | PM / scripts |
| `project-memory-init` | Creates PROGRESS/LESSONS folders | Onboard / once |

> **Tip:** If you only remember three things:  
> 1) `./install.sh` once  
> 2) `agents-doctor --apply .` in your project  
> 3) `claude --agent dev-orchestrator` and talk in normal language  

---

## 4. Newbie path (step by step)

### Day 0 — Install (30–60 min)

1. Install **Claude Code** (and optionally Codex / AGY / Grok — not all required).  
2. Clone and install the stack:

```bash
git clone https://github.com/VKirill/claude-lane-stack.git
cd claude-lane-stack
./install.sh
```

3. Open a **new** terminal so `PATH` updates, or run:

```bash
export PATH="$HOME/.agents/bin:$PATH"
```

4. Go to **your** project (not necessarily this repo):

```bash
cd ~/projects/my-app
agents-doctor --apply .
```

Read the printed **Profile** (e.g. `full` or `claude-only`). That only means “which workers are available”.

5. Start PM and onboard once:

```bash
claude --agent dev-orchestrator
```

In the chat: `/project-onboard` or *«проведи онбординг проекта»*.  
Wait until CLAUDE.md / short docs exist. **You still don’t merge anything.**

### Day 1 — First real task

1. Same folder, same command:

```bash
claude --agent dev-orchestrator
```

2. Say one **small** concrete goal, for example:  
   *«Add a README section with install steps»* or *«Fix the typo on the pricing page»*.

3. Let the PM work. You may see task files under `.agents/runs/`. That’s normal.

4. When the PM says done, check `main` / the app. You should **not** be asked to `git merge`.

### Day 2 — After sleep / new chat

Context in the chat was forgotten. That is normal.

```bash
cd ~/projects/my-app
claude --agent dev-orchestrator
```

Then either:

- type **`/resume-project`**, or  
- in terminal: `resume-project .`

You get a short **Now / Blocked / Next**. Continue in plain language.

> **Footnote:** “Cold start” only means “start again without old chat memory”.  
> `/resume-project` is the **cheat sheet** for that moment — not a daily ritual and **not** step 1 of install.

---

## 5. What to say to the PM (examples)

| You say | PM should |
|---------|-----------|
| «Сделай онбординг» / `/project-onboard` | Run Codex onboarder, fill CLAUDE.md |
| «Добавь тёмную тему в настройки» | Create a run, dispatch write lane, verify, merge |
| «Только план, без кода» | Write plan under docs or run PLAN — no merge |
| «Продолжи» / `/resume-project` | Read board + PROGRESS, propose next step |
| «Застряло» | Stall-check, re-dispatch worker |

Avoid: managing branches yourself, running five Claude windows for the same feature, editing worker files mid-run without telling the PM.

---

## 6. Minimal mental model

```text
You → talk to PM (Claude)
         PM → optional workers (AGY / Grok / Codex)
         PM → puts result on main
You → open the app / pull main / enjoy
```

If something is unclear, open [SOLO-ORCHESTRATION.md](SOLO-ORCHESTRATION.md) or ask in the PM chat: *«объясни что ты сейчас делаешь простыми словами»*.

---

## 7. FAQ for first-timers

**Q: Do I need all of AGY + Grok + Codex?**  
A: No. Only Claude is required. Doctor adapts.

**Q: Where is my work saved?**  
A: In git (`main` after success) and in `.agents/runs/` (task history).

**Q: Why is there a COCOON / plan in `docs/plans` but no code?**  
A: That is a **strategy** document. Say *«реализуй»* so the PM creates a **run** under `.agents/runs/`.

**Q: I closed the terminal. Did I lose everything?**  
A: Code on disk and git remains. Chat memory is gone → use `/resume-project`.

**Q: Can I edit code myself in parallel?**  
A: Yes, carefully. Prefer telling the PM what you changed so tasks don’t collide.
