---
title: Claude Lane Stack overview
type: overview
created: 2026-10-19
updated: 2026-10-19
status: active
confidence: low
tags: [overview, orchestration, cli-agents]
sources:
  - bin/run-controller
  - bin/run-init
  - bin/lane-ctl
  - bin/pipeline_stages.py
  - plugins/lane-stack/.claude-plugin/plugin.json
  - schemas/run-v2.schema.json
  - schemas/task-v2.schema.json
  - board/server/server.mjs
  - board/web/js/api.js
  - hooks/session_ledger.py
  - install.sh
  - bin/lane_memory.py
  - bin/lane_memory_hub.py
---
# Claude Lane Stack overview

TL;DR: Claude Lane Stack coordinates CLI coding agents through task contracts, verification receipts, and Git workspaces; optional stages add critique, review, memory, docs, and browser QA (`bin/run-controller:117-159`, `bin/pipeline_stages.py:193-202`).

## What it is

The repository combines a Claude Code plugin, host CLI tools, agent profiles, and JSON-schema contracts. The plugin manifest registers skills, agents, hooks, and commands (`plugins/lane-stack/.claude-plugin/plugin.json:1-19`). The installer deploys the host tools and plugin assets into the user environment (`install.sh:1-30`).

A run is described by a run contract and task contracts. The controller validates the run contract before supervising tasks, and terminal task state is represented by outcome and acceptance artifacts (`bin/run-controller:117-159`, `schemas/run-v2.schema.json:1-71`, `schemas/task-v2.schema.json:1-125`).

## Stack

- Claude Code plugin for commands, agents, skills, and hooks (`plugins/lane-stack/.claude-plugin/plugin.json:1-19`).
- Host automation in Python and shell under `bin/` and `hooks/` (`bin/run-controller:1-30`, `hooks/session_ledger.py:1-27`).
- Lane Board server in Node.js with browser JavaScript views (`board/server/server.mjs:1-16`, `board/web/js/api.js:1-10`).
- JSON Schema contracts for run, task, and receipt data (`schemas/run-v2.schema.json:1-30`, `schemas/task-v2.schema.json:1-30`).

## Main capabilities

- Create and validate run and task contracts before dispatch (`bin/run-init:185-270`, `bin/run-validate:410-450`).
- Dispatch provider sessions and verify owned paths through the controller and lane tools (`bin/run-controller:1310-1367`, `bin/run-controller:1131-1151`, `bin/lane-ctl:1900-2060`).
- Configure optional critique, night review, specialist, onboarding, memory, docs, and browser QA stages (`bin/pipeline_stages.py:193-300`).
- Read run, task, todo, and review state through the local Lane Board (`board/server/server.mjs:106-198`).
- Index and retrieve project memory through the memory CLI and hub (`bin/lane_memory.py:634-680`, `bin/lane_memory_hub.py:168-184`).

## Quick start

Install the host tools, add `~/.agents/bin` to `PATH`, prepare a project, then start the PM (`install.sh:1-30`, `bin/project-onboard:1-20`).

```sh
./install.sh
export PATH="$HOME/.agents/bin:$PATH"
cd /path/to/project
project-onboard .
lane-pm
```

## Where to look next

- System boundaries and execution paths: [architecture](architecture.md).
- Persistent contracts and receipts: [data model](data-model.md).
- Operational pitfalls: [gotchas](gotchas.md).
- Agent hooks: [HOOKS.md](HOOKS.md).
- Provider selection and pipeline defaults: [ROUTING.md](ROUTING.md).

<!-- lane-pilot:backlinks -->
## Referenced by

- [Beginner guide](BEGINNER.ru.md)
- [Claude Lane Stack architecture](architecture.md)
