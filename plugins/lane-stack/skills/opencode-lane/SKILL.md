---
name: opencode-lane
description: Claude Lane OpenCode half. How to add OpenCode behavior, diagnose a writer run, and what stays in lane-ctl. Use when user says opencode-lane, делай диагноз, OpenCode plugin, sticky contract, winnow on OpenCode, Jev effort, writer session plugin, or any new OpenCode feature in claude-lane-stack. SKIP: product task YAML (lane-contract); run DAG (orchestrator-lanes); third-party OpenCode plugins (agentmemory, gemini-auth, open-cursor).
argument-hint: "[info]"
---

# opencode-lane

## Info (print and stop)

If `$ARGUMENTS` is `info`, or the user says `info` / `справка` / `как запускать` this skill:
print the block below **verbatim** (Russian), then **stop**. Do not edit the plugin.

```text
opencode-lane — OpenCode-половина Claude Lane

Роли
- Claude Code = PM: run-init, run-supervisor, lane-ctl owns/verify/accept.
- OpenCode = писатели (Grok и любой другой model через lane-session).
- Этот плагин = единственное НАШЕ нововведение внутри OpenCode-сессии.

Куда класть код
- Вход: profiles/opencode/opencode-lane.ts (только re-export).
- Код:  profiles/opencode/opencode-lane/<mod>.ts + проводка в index.ts.
- Живое: ~/.config/opencode/plugins/opencode-lane.ts + plugins/opencode-lane/.
- Не второй plugin-файл. Не новое имя в opencode.json.

Конвейер
- lane-session без --pure (плагин должен грузиться).
- Env: LANE_TASK_FILE, LANE_PROMPT_FILE, LANE_STACK_ROOT, TYPESAFE_API_KEY.
- Выкл Jev extra: LANE_OPENCODE_JEV=0. Выкл effort: LANE_JEV_EFFORT=0.
- Fail-open: Jev/winnow упал → сессия как без плагина, строка в jsonl.

Нельзя
- owns / verify / accept / retry — не сюда (lane-ctl, lane-session).
- Глотать чужие плагины (agentmemory-capture, gemini-auth, open-cursor).
- Второй планировщик на Jev. Jev = System One, не coding LLM.

Как открыть шпаргалку
- Claude Code: /lane-stack:opencode-lane info
- OpenCode TUI: /opencode-lane  (файл ~/.config/opencode/commands/opencode-lane.md)
- Не /lane-stack:… в палитре OpenCode — это namespace Claude-плагина, там его нет.

Диагноз прогона
- Сказать «делай диагноз».
- Лог: сосед LANE_PROMPT_FILE → opencode-lane.jsonl
  иначе ~/.config/opencode/opencode-lane.jsonl
```

Canonical files: `profiles/opencode/opencode-lane.ts`,
`profiles/opencode/opencode-lane/index.ts`, `bin/lane-session`
(`attach_lane_contract_env`, opencode argv). Skills **lane-contract**
(YAML) and **orchestrator-lanes** (DAG) stay separate.

Load **typesafe-ai** when adding a Jev question. Keep known rules in code;
Jev only supplies a typed judgment.

---

## Split (do not blur)

| Layer | Owner | Lives in |
|-------|--------|----------|
| Task YAML, owns, acceptance | PM | `.agents/runs/` + **lane-contract** |
| Dispatch, retry, session id | Controller | `bin/lane-session`, `lane-ctl` |
| L1 verify / accept | Controller | `lane-ctl` — never the plugin |
| Sticky YAML after compact | Plugin | `sticky.ts` |
| Winnow large tool output | Plugin | `index.ts` → sidecar `:47311` |
| Effort route | Plugin | `chat.params` + `jev-route-core.ts` |
| Compact old tool results | Plugin | `fast-jev` `compact.ts` |
| Diagnose a failed tool | Plugin | `diagnose.ts` (hint only) |
| Write-skill hint | Plugin | `skill-hint.ts` |
| Acceptance vs last tool | Plugin | `evidence.ts` |
| Failure telemetry | Plugin | `log.ts` → `opencode-lane.jsonl` |

A judgment that **changes accept/retry/merge** belongs in `lane-ctl`,
not here. The plugin may only append a `[opencode-lane …]` note and a
jsonl row. The writer still decides; the controller still gates.

---

## Add an OpenCode change

1. One module under `profiles/opencode/opencode-lane/`. One hook concern.
2. Wire it in `index.ts`. Re-export from `opencode-lane.ts` only if tests
   or agents import the symbol.
3. Fail-open: catch, `laneLog({ mod, ok: false, err })`, keep the session.
4. Brand every user-visible string `[opencode-lane <mod>]`.
5. `install.sh` already copies `opencode-lane.ts` + the folder. Do not add
   a second `plugin` list entry.
6. Copy live: `~/.config/opencode/plugins/opencode-lane.ts` and
   `plugins/opencode-lane/*.ts`. A checkout-only fix is not shipped.
7. One smallest test in `tests/test_jev_route.py` (string wire or a node
   `--experimental-strip-types` check). No extra harness.

OpenCode hooks this plugin uses:

- `chat.message` — remember prompt, skill-hint
- `chat.params` — Jev effort
- `tool.execute.after` — winnow, diagnose
- `experimental.chat.messages.transform` — evidence, compact, sticky

If OpenCode grows a new hook, handle it in `index.ts`, not a sibling plugin.

---

## Diagnose a writer run

User said **«делай диагноз»** — do this, then stop unless they said «чини».

1. Read the jsonl (newest last):

```bash
f="${LANE_PROMPT_FILE%/*}/opencode-lane.jsonl"
[ -f "$f" ] || f="$HOME/.config/opencode/opencode-lane.jsonl"
tail -n 40 "$f"
```

2. Classify rows by `mod`: `jev` `route` `winnow` `compact` `sticky`
   `diagnose` `skill-hint` `evidence` `budget`. `ok: false` is the failing
   module. `budget` rows with `dup: true` are repeated tool results.
3. Confirm the conveyor actually loaded us:
   - argv has no `--pure`
   - `~/.config/opencode/opencode.json` `plugin` contains
     `./plugins/opencode-lane.ts`
   - `LANE_TASK_FILE` was in the process env (sticky empty without it)
4. Report: module, last `err`, whether the session continued (fail-open).
   Do not patch until asked.

---

## Current gaps (2026-09-22)

Do-now (can pay, bounded):

1. Conveyor dropped `--pure`, so **every** `opencode.json` plugin loads
   (`agentmemory-capture`, `gemini-auth`, `open-cursor`). Need a lane-only
   config or an allowlist so only `opencode-lane` runs in writer sessions.
2. `attach_lane_contract_env` does not pass `LANE_OPENCODE_JEV`;
   `LANE_STACK_ROOT` only if already in the parent env.
3. `evidenceNotes` / `skillHint` run **once** per session. Early empty
   tool output skips evidence forever.
4. Diagnose notes are not consumed by `lane-ctl` retry (controller backlog).
5. `experimental.chat.messages.transform` may omit `sessionID` → notes
   keyed as `""`.
6. This host: GitNexus MCP Ladybug v41 vs index v42 — `impact` fails;
   CLI still works.

Later (TypeSafe skill, keep the idea, do not reject). **Not new plugins.**
Each item is a module under `profiles/opencode/opencode-lane/` or a
`lane-ctl` / `lane-session` change. Jev judges; code owns the rest.

Token sinks (measure before cutting): unfamiliar-repo search, debug without
repro, large refactor/review, browser/DOM dumps, multi-agent re-reads.

| Idea | Where | Status |
|------|--------|--------|
| **budget log** (insights) | `budget.ts` jsonl `mod:budget` | **now** — chars, fingerprint, dup count |
| Repeat-loop hint | `budget.ts` `repeatHint` on bash ×3 | **now** — hint only, never deny |
| Rerank before Read | GitNexus/`rg` shortlist + Jev Score per candidate ([rerank](https://docs.typesafe.ai/cookbooks/rerank_typesafe.md)) | next after jsonl shows wasteful reads |
| Re-read only if needed | hash + range; Jev only for “is the old span enough?”. Never replace a missing source with “you already saw this”. | after budget data |
| Structured tool stubs | extend winnow/fast-jev for test/API/page | later |
| Claude↔OpenCode min pack | sticky + `lane-session` handoff; Jev picks extra candidates; artifacts stay linked | later (`lane-ctl` owns retry) |
| Resume after crash | `lane-session` lease already resumes; add freshness check of files/env | later, not the plugin |
| Independent accept | Gemini `lane-reviewer` + existing L1; Jev evidence already | later in `lane-ctl`, not a plugin |
| Replay bench | sequential fixtures, no prod side effects | later, not OpenCode |

Cache trap: shrinking context can cost more if it busts the prompt cache.
Net = cost_without − cost_with − Jev − extra retries from lost context.
Compare equal-quality tasks; subscription ≠ API invoice.

Do **not**: mutation-testing harness, model-stats auto-router, merging
agentmemory into this plugin, Jev as a coding agent, separate
`lane-budget` / `lane-insights` / `lane-resume` plugins.

---

## TypeSafe rules for new judgments

- Choice = one of a set. Noul = yes/no (no separate confidence). Score =
  degree. One narrow question per id. Independent questions in one request.
- Thresholds are ours (`diagnose` conf ≥ 0.5, `skill-hint` ≥ 0.55,
  `evidence` supports ≥ 0.8). Re-evaluate on real jsonl, not cookbook
  demos.
- Extra Jev is off with `LANE_OPENCODE_JEV=0`. Effort router is separate
  (`LANE_JEV_EFFORT=0`).

---

## NEVER

- A second OpenCode plugin branded as ours.
- Accept / merge / retry policy inside the plugin.
- Swallowing third-party plugins.
- Inventing API keys or reading `opencode.json` secrets into chat.
- Docs/README besides this skill unless the user asked.
