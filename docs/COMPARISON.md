# ⚖️ Claude Lane Stack vs other multi-agent orchestrators for Claude Code

Choosing a multi-agent orchestration tool for Claude Code in 2026 means picking between very different philosophies: tmux farms, database-backed swarm platforms, plugin packs — and this repo's approach, a file-based factory for one person.

This page compares Claude Lane Stack with the most-cited alternatives, as honestly as we can.

> [!NOTE]
> Facts below were collected from each project's own README in **July 2026** and may drift as projects evolve. Spotted an error? [Open an issue](https://github.com/VKirill/claude-lane-stack/issues) — we'll fix it.

---

## 🎯 TL;DR — which one fits you

| You want | Look at |
|----------|---------|
| One PM chat, workers from several vendors, **finished code lands on `main` without you touching git** | **Claude Lane Stack** (this repo) |
| A full issue→PR→CI→merge pipeline with TDD enforcement across Claude/Gemini/Codex | metaswarm |
| A huge community plugin with tmux teams and many execution modes | oh-my-claudecode |
| An enterprise-grade swarm platform with vector memory and agent federation | Ruflo (ex claude-flow) |
| 20+ parallel Claude instances grinding a codebase in tmux | claude_code_agent_farm |
| A Rust CLI that turns tasks into PR-ready diffs with consensus voting | ccswarm |
| A Claude-only plugin with dozens of prebuilt specialist agents | claude-mpm |

---

## 📊 Side-by-side

| | **Claude Lane Stack** | metaswarm | oh-my-claudecode | Ruflo (ex claude-flow) | claude_code_agent_farm | ccswarm | claude-mpm |
|---|---|---|---|---|---|---|---|
| **Orchestrates** | Claude Code (PM) + AGY / Grok / Codex lanes | Claude Code + Gemini CLI + Codex CLI | Claude, Codex, Gemini, Antigravity, Grok, Cursor (tmux panes) | Claude, GPT/Codex, Gemini, Cohere, Ollama | Claude Code only | Claude Code / Codex | Claude only |
| **Task / state storage** | Plain YAML file contracts in `.agents/runs/` — no DB, no required MCP | BEADS git-native task database (`bd` CLI) | Files under `.omc/` | Vector DB (AgentDB/HNSW) + MCP server | State files + lock files + tmux | NDJSON audit trail + worktrees | Resume logs + MCP server |
| **Merges to `main` for you** | ✅ Yes — orchestrator merges via `wt-merge-main` after review + checks | ✅ Yes — PR Shepherd watches CI and merges | ❌ No — git stays manual | Not a stated feature | Partial — commits to a branch, no merge/PR | Partial — auto-commit + PR, merge is yours | ❌ No |
| **Parallel-safety mechanism** | `owns_paths` file ownership per task card + git worktrees | Task DB coordination | tmux pane separation | Swarm coordination via MCP | Lock files + heartbeats | Git worktree isolation + consensus voting | Session management |
| **Independent review gate** | ✅ Separate review lane (Codex), different vendor than the writer | ✅ Parallel review gates | Mode-dependent | Mode-dependent | ❌ | ✅ Quality gates + Sangha voting | ❌ |
| **Adapts to missing tools** | ✅ `agents-doctor` writes one of 5 profiles, down to `claude-only` | ❌ Expects its CLI set | Partially | Partially | n/a (Claude only) | Partially | n/a (Claude only) |
| **Install** | `git clone` + `./install.sh` | Plugin marketplace / `npx` | Plugin / npm | `npx` / plugin / npm | Clone + Python `setup.sh` | Rust `cargo install` | Plugin / pip / brew |
| **License** | MIT | MIT | MIT | MIT | MIT (+ rider) | MIT | Elastic License 2.0 |

---

## 🏭 What Lane Stack optimizes for

Most tools in this niche optimize for **scale** — more agents, more panes, more throughput. Lane Stack optimizes for **one person not having to think about logistics**:

1. **The human never touches git.** The end state of every job is verified code on `main`, merged by the orchestrator. Among the tools above, only metaswarm goes equally far — via a CI/PR pipeline; Lane Stack does it locally with worktrees.
2. **Everything is a readable file.** Task cards, reports, merge notes — plain YAML and markdown inside your repo. No task database to learn, no MCP server to keep alive, nothing hidden. `git log` is the audit trail.
3. **Writers and reviewers are different vendors.** A task written by AGY or Grok is gated by Codex review — cross-vendor scrutiny catches what self-review misses.
4. **It shrinks gracefully.** `agents-doctor` detects what's installed and writes a matching profile. Nothing but Claude Code? `claude-only` mode still runs the whole conveyor — slower, but the same discipline.
5. **A beginner can actually start.** [Plain-language guide](BEGINNER.md) in 9 languages, no orchestration vocabulary required.

## 🤝 When to pick something else

- You want **maximum community and plugins** — oh-my-claudecode has by far the largest ecosystem.
- You need an **enterprise swarm platform** (vector memory, federation, trust boundaries) — that's Ruflo's territory.
- Your workflow is **GitHub-PR-centric with CI enforcement** — metaswarm's PR Shepherd is built exactly for that.
- You want to **brute-force a large refactor** with 20+ parallel Claude instances — claude_code_agent_farm.
- You live in **Rust** and want replayable audit trails — ccswarm.

No tool above is a bad choice; they solve different jobs. Lane Stack's job: *a solo developer ships real projects by talking to one manager.*

---

<div align="center">

⬅️ Back to [README](../README.md) · New here? Start with the [Beginner guide](BEGINNER.md)

</div>
