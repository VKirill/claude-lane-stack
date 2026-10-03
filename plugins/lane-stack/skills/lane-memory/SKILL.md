---
name: lane-memory
description: "One project fact memory on the BB hub (Lane Pilot), the same from every machine; lessons become hub rules. Opt-in via adoc stages.memory.enabled. Use when user says память, lane-memory, corpus, CORE, урок, почему бот забыл, or an agent needs durable non-code facts. Not PROGRESS dumps."
argument-hint: "[info]"
---

# Lane memory

Facts that **cannot be derived** from git or the code documentation (docs/).
Laws from the SMA 5.6.1 drawing. Off until adoc turns it on.

**Where it lives.** One memory per project on the BB hub (Lane Pilot's database), whatever machine the session
runs on: `lane-memory write`, `search`, `context` and CORE go through `bb plugin rpc call lane-pilot
session_memory_*`. Without a connection a write waits in `.cls/memory-outbox/` (`lane-memory flush` sends it).
`.agents/memory/*.md` files are not written any more; `sensitive` records stay local in `.cls/local-memory`.
`LANE_MEMORY_HUB=off` keeps the old local corpus.

**Lessons.** A correction or a landmine is a rule, not a file line:
`lane-memory lesson "<one imperative rule>" --for pm|writer|both [--always] --evidence "<run/test/date>"`.
`--for pm` — planning, task contracts, reviewing reports, merging, deploying: writers never get it. `--for writer` —
how code is edited and checked inside one task. `--always` only for a rule that holds for every writer task whatever
it changes (how to run or read any command); otherwise System One gives it to the tasks it fits. The hub merges
repeats, keeps at most 12 rules in force on trial, retires unused ones and lets at most 30 wait. Never append to
`.agents/LESSONS.md`.

## Info (print and stop)

If `$ARGUMENTS` is `info`, or the user says `info` / `справка` this skill:
print the block below **verbatim** (Russian), then **stop**.

```text
lane-memory — факты проекта, которые нельзя вывести из кода

Зачем
- Правила «всегда так» сидят в ядре и грузятся каждую сессию (не поиск).
- Остальное — по запросу: lane-memory context / search.
- Пишет только команда lane-memory write (одна дверь). Ночной агент не чинит сам.

adoc уже пишет эти крутилки. Включить — Enabled (или enabled: true).
stages:
  memory:
    enabled: false
    maintain: true
    inject: true
    provider: codex
    model: gpt-5.6-terra
    reasoning_effort: high
    audience: subagent
    personal_bot: ""
    search_engine: auto
    core_budget: 3072
    note_budget: 8000
    index_budget: 65536
    context_budget: 2500

Раскладка
.agents/memory/         корпус в git (был .claude/memory)
.cls/local-memory/      только эта машина, не git (был .sma/local-memory)
.cls/index/             SQLite FTS, производный (был .sma/index)

Потом: lane-memory init .
Черновик-шаблон (любой проект): drafts/_TEMPLATE.md
  или skill references/draft-template.md
Фон: memory-maintain-project . "24 hours ago"

Спросить корпус
lane-memory context . "почему сводку не по шаблону"
lane-memory search . "handoff"
lane-memory core .
lane-memory explain . --task "подготовь поставку"

Записать факт (черновик → дверь)
lane-memory write --apply .agents/memory/drafts/<id>.md --confirm .agents/memory/<id>.md --yes

Не класть сюда
структуру репо, git-историю, PROGRESS, YAML рана — у них свои файлы.
```

## Work

If `lane-memory enabled .` exits 1: do not invent a corpus. Tell the owner
to set `stages.memory.enabled: true`.

If enabled: on cold start, CORE is already in `resume-project`. For a task,
run `lane-memory context . "<task>"` and Read named files. Recalled claim
about the tree is a prompt to `lane-memory verify . <id>`, not proof.

Write only through the CLI door. Author sets `memory_type` and `truth_mode`.
One `claim`. Tags from `TAGS.md`. English files.
