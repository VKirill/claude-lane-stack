---
name: lane-memory
description: "SMA-style project fact corpus under .agents/memory/. Opt-in via adoc stages.memory.enabled. Use when user says память, lane-memory, corpus, CORE, почему бот забыл, or an agent needs durable non-code facts. Not PROGRESS/LESSONS dumps."
argument-hint: "[info]"
---

# Lane memory

File corpus for facts that **cannot be derived** from git or MODULE_MAP.
Laws from the SMA 5.6.1 drawing. Off until adoc turns it on.

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
