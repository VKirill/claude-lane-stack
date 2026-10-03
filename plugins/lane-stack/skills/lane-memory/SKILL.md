---
name: lane-memory
description: "One project fact memory on the BB hub (Lane Pilot), the same from every machine; lessons become hub rules. Use when user says память, lane-memory, corpus, CORE, урок, почему бот забыл, or an agent needs durable non-code facts; `$ARGUMENTS` exactly info prints the card. Not PROGRESS dumps."
argument-hint: "[info]"
---

# Lane memory

Facts that **cannot be derived** from git or the code documentation (docs/).
Laws from the SMA 5.6.1 drawing.

**Where it lives.** One memory per project on the BB hub (Lane Pilot's database), whatever machine the session
runs on: `lane-memory write`, `search`, `context` and CORE go through `bb plugin rpc call lane-pilot
session_memory_*`. Without a connection a write waits in `.cls/memory-outbox/` (`lane-memory flush` sends it).
`.agents/memory/*.md` files are not written any more; `sensitive` records stay local in `.cls/local-memory`.
`LANE_MEMORY_HUB=off` keeps the old local corpus.

**Lessons.** A correction or a landmine is a rule, not a file line:
`lane-memory lesson "<one imperative rule>" --for pm|writer|both [--always] --evidence "<run/test/date>"` (inside a Lane Pilot PM chat the tool `lane_pilot_lesson` does the same: rule, audience `pm`, `writer` or `both` — required, `always` optional).
`--for pm` — planning, task contracts, reviewing reports, merging, deploying: writers never get it. `--for writer` —
how code is edited and checked inside one task. `--always` only for a rule that holds for every writer task whatever
it changes (how to run or read any command); otherwise System One gives it to the tasks it fits. The hub merges
repeats, keeps at most 12 rules in force on trial, retires unused ones and lets at most 30 wait. Never append to
`.agents/LESSONS.md`.

> **Inside a Lane Pilot chat** (`LANE_PILOT_AGENT_TYPE` set / tools `lane_pilot_*` present) the hub is already on: read with `lane_pilot_memory_context` or `lane-memory search|context`, write a lesson with `lane_pilot_lesson`. Do not create `.agents/memory/` files or drafts there, and do not call agentmemory tools (`memory_save`, `memory_smart_search`): that would start a second memory.

> **Memory-maintainer stage:** when the host gives you an accepted task and asks for a JSON array of memory candidates, answer with that array only; do not run `lane-memory`, do not edit files.

## Info

If `$ARGUMENTS` is exactly `info`, print `references/info.md` verbatim (Russian) and stop.

## Work

On cold start CORE is already in `resume-project` (Lane Pilot: in the session brief). For a task, run `lane-memory context . "<task>"` and Read the named sources. A recalled claim
about the tree is a prompt to `lane-memory verify . <id>`, not proof.

Write a fact only through the CLI door, `lane-memory write`; the author sets `memory_type` and `truth_mode`, one `claim`, tags from `TAGS.md`, English text. Keep the draft file outside `.agents/memory/` (for example `.cls/drafts/<id>.md`, template in `references/draft-template.md`) and run:

```bash
lane-memory write --apply .cls/drafts/<id>.md --confirm .agents/memory/<id>.md --yes
```

With the hub on, `--confirm` only names the destination the CLI checks; the record goes to the hub and nothing is written to `.agents/memory/`. If the hub is unreachable the write waits in `.cls/memory-outbox/` (`lane-memory flush`); do not invent a local corpus.
