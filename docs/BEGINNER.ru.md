---
title: Beginner guide
type: overview
created: 2026-07-11
updated: 2026-10-19
status: active
confidence: medium
tags: [beginner, quickstart, onboarding]
sources:
  - install.sh
  - bin/project-onboard
  - bin/lane-pm
  - bin/run-controller
  - bin/pipeline_stages.py
  - schemas/task-v2.schema.json
---
# Beginner guide

TL;DR: Install the host tools, prepare a project, and start `lane-pm`; the PM turns requested work into scoped tasks that provider CLIs execute and verify (`install.sh:465-480`, `bin/project-onboard:40-55`, `bin/lane-pm:1-45`).

## What the stack does

Claude Lane Stack coordinates coding work through task contracts and Git. A task identifies its objective, owned paths, prohibited paths, and verification requirements (`schemas/task-v2.schema.json:1-125`). The run controller supervises provider attempts and records task outcomes (`bin/run-controller:734-808`, `bin/run-controller:1310-1367`, `bin/run-controller:566-594`).

## Install and prepare a project

1. From the repository checkout, install the host commands:

   ```sh
   ./install.sh
   ```

2. Add the installed command directory to the current shell and enter your project:

   ```sh
   export PATH="$HOME/.agents/bin:$PATH"
   cd /path/to/your/project
   ```

3. Create or refresh the project passport:

   ```sh
   project-onboard .
   ```

The installer reports the PATH entry and `lane-pm` launch command (`install.sh:465-480`, `install.sh:560-567`). The onboarding CLI accepts a project path (`bin/project-onboard:40-55`).

## Start work

```sh
lane-pm
```

Describe the requested result to the PM. It coordinates task contracts and the configured provider stages (`bin/lane-pm:1-45`, `bin/pipeline_stages.py:193-300`).

Before dispatch, read the task’s objective, `owns_paths`, `never_touch`, and verification fields (`schemas/task-v2.schema.json:70-125`). A provider’s report is not itself the acceptance receipt; acceptance validation checks the task and evidence (`bin/run-validate:348-421`).

## Where to look next

- [Overview](overview.md) — product boundaries and first steps.
- [Architecture](architecture.md) — runtime components and the Lane Board read path.
- [Data model](data-model.md) — contracts, receipts, memory and usage data.
- [Gotchas](gotchas.md) — common failure modes.
- [Provider routing](ROUTING.md) — stage defaults and Jev routes.
- [Hooks](HOOKS.md) — CLI hook behavior.

<!-- lane-pilot:backlinks -->
## Referenced by

- [docs/BEGINNER.de.md](BEGINNER.de.md)
- [docs/BEGINNER.es.md](BEGINNER.es.md)
- [docs/BEGINNER.fr.md](BEGINNER.fr.md)
- [docs/BEGINNER.ja.md](BEGINNER.ja.md)
- [docs/BEGINNER.ko.md](BEGINNER.ko.md)
- [docs/BEGINNER.md](BEGINNER.md)
- [docs/BEGINNER.pt-BR.md](BEGINNER.pt-BR.md)
- [docs/BEGINNER.zh-CN.md](BEGINNER.zh-CN.md)
