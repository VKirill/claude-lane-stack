---
title: Claude Lane Stack gotchas
type: gotchas
created: 2026-10-19
updated: 2026-10-19
status: active
confidence: medium
tags: [gotchas, operations, contracts]
sources:
  - bin/run-controller
  - bin/run-validate
  - schemas/run-controller-v1.schema.json
  - board/server/server.mjs
  - board/server/lib/parsers.mjs
  - board/web/js/api.js
  - plugins/lane-stack/winnow/sidecar/src/winnow/serve.py
  - plugins/lane-stack/winnow/sidecar/src/winnow/extract.py
  - bin/lane_memory.py
---
# Claude Lane Stack gotchas

TL;DR: Most operational surprises come from treating file-backed lifecycle evidence as mutable status, assuming optional integrations block work, or expecting the local board to accept writes.

## Critical

### An accepted task needs valid receipts

**Problem:** A task’s terminal status is validated from acceptance, ownership, and verification evidence; a report alone does not pass the acceptance checks (`bin/run-validate:348-421`).

**Risk:** A manually edited task label can disagree with the validated lifecycle projection (`board/server/lib/parsers.mjs:44-53`).

**Workaround:** Inspect the task’s acceptance and outcome artifacts and rerun the relevant validation phase (`bin/run-validate:348-421`, `bin/run-controller:560-594`).

### Lane Board is read-only

**Problem:** The API routes serve reads and refresh events. Unknown API paths return 404, and non-GET/HEAD requests return 405 (`board/server/server.mjs:216-227`).

**Risk:** A client cannot mutate run state through the board HTTP API (`board/server/server.mjs:121-198`).

**Workaround:** Use the run controller to change lifecycle state; use the board to inspect the resulting projection (`bin/run-controller:734-840`, `board/server/server.mjs:126-198`).

## High

### Partial task failure uses a run stage outside the receipt schema

**Problem:** `recompute_run_stage` returns `degraded` when one task is blocked while other tasks remain, but the JSON schema permits only `running`, `accepted`, `blocked`, and `failed` (`bin/run-controller:327-339`, `schemas/run-controller-v1.schema.json:11-24`).

**Risk:** JSON-Schema consumers reject this persisted runtime stage; the controller’s own structural reader checks only the receipt version and task-state object shape (`bin/run-controller:405-406`, `bin/run-controller:277-290`).

**Workaround:** Check the controller receipt’s schema version and task details before relying on an external schema validator for the top-level stage (`bin/run-controller:277-290`, `schemas/run-controller-v1.schema.json:11-24`).

### Winnow fail-open paths preserve original tool output

**Problem:** If the judge runtime is unavailable, Winnow notifies once and returns without rewriting the tool output. Exceptions during an event are logged and contained (`plugins/lane-stack/winnow/sidecar/src/winnow/serve.py:103-120`). Unsupported tool response shapes also return no extracted text (`plugins/lane-stack/winnow/sidecar/src/winnow/extract.py:30-82`).

**Risk:** A configured Winnow hook can be active while a particular response is unchanged (`plugins/lane-stack/winnow/sidecar/src/winnow/serve.py:101-120`).

**Workaround:** Check `winnow doctor` when the notice appears; the hook explicitly recommends this recovery path (`plugins/lane-stack/winnow/sidecar/src/winnow/serve.py:103-110`).

## Medium

### Project memory search index is derived state

**Problem:** The lexical SQLite index is deleted and rebuilt from the live owner-audience records when the corpus hash changes (`bin/lane_memory.py:461-498`).

**Risk:** Edits made only inside the generated SQLite index are discarded during rebuild (`bin/lane_memory.py:468-497`).

**Workaround:** Edit memory source records; let search rebuild the index when it detects a stale hash (`bin/lane_memory.py:501-510`).

### A malformed Lane Board path does not fall through to the SPA

**Problem:** Paths under `/api/` that do not match a route return JSON 404; non-API static requests fall back to `index.html` only when the static file is absent (`board/server/server.mjs:53-73`, `board/server/server.mjs:216-227`).

**Risk:** A frontend typo under `/api/` appears as a route failure rather than loading the app shell (`board/server/server.mjs:216-223`).

**Workaround:** Compare the client path against the registered endpoints and the API helper (`board/server/server.mjs:121-198`, `board/web/js/api.js:29-48`).

<!-- lane-pilot:backlinks -->
## Referenced by

- [Beginner guide](BEGINNER.ru.md)
- [Claude Lane Stack architecture](architecture.md)
- [Claude Lane Stack overview](overview.md)
