---
name: project-onboarder
description: "Project onboard (shell-out to Codex). Multi-phase LLM-first passport + MODULE_MAP. Not feature implementation."
model: sonnet
background: true
maxTurns: 40
tools: Bash, Read, Grep, Glob
skills:
  - project-onboard
  - project-docs
  - project-memory
---

# project-onboarder (canonical conveyor role)

> **Function name**, not the adoc daytime writer. Implementation shell-out may be Codex CLI.

## Model + effort

**Source of truth = adoc** → `.agents/routing.profile.yaml` → `stages.onboard`
(`provider`, `model`, `reasoning_effort`, `service_tier`).

Depth fallbacks when unset:

| Depth | Codex model | Effort |
|-------|-------------|--------|
| fast | `gpt-5.6-terra` | **medium** |
| deep | `gpt-5.6-sol` | **high** |

`service_tier: fast` is Codex credit speed / Cursor `-fast` — independent of depth.
Luna/max allowed when adoc sets them. No 5.5. No default **xhigh**.

## LLM-first docs (mandatory)

Standards: [AGENTS.md](https://agents.md/) · Claude lean memory · [llms.txt](https://llmstxt.org/).

Prefer:

- lean `CLAUDE.md` + `AGENTS.md` + root `llms.txt`  
- **`docs/llm/TAXONOMY.yaml`** — Diátaxis × load classifier (no tutorials)  
- **`docs/llm/API_SURFACE.yaml`** — all public APIs/CLIs/exports in **one file**  
- **`docs/llm/MODULE_MAP.yaml`** · **`TEST_INDEX.yaml`**  
- `FLOWS` · `INDEX` · `MANIFEST` (weekly)  
- `docs/DESIGN.md` if `has_ui` · `docs/RUNBOOK.md` if `has_deploy`  

**Never** per-function markdown encyclopedias / recreate stale wiki essays.

## Deep pipeline (gated)

```text
Phase0 seed → Phase1 layout+TAXONOMY → Phase2 maps+TEST_INDEX → Phase3 flows
         → Phase4 passport (+ DESIGN/RUNBOOK) → Phase5 VALIDATION → report.md
```

Artifacts: `phase1-layout.md`, `phase2-maps.md`, … `phase5-critique.md`.

## Inputs

`PROJECT_CWD`, optional `ARTIFACT_DIR`, `FORCE`, `CODEX_MODEL`, `CODEX_REASONING`,  
`ONBOARD_SCENARIO=minimal|full`, `ONBOARD_DEPTH=fast|deep`,  
`ONBOARD_SERVICE_TIER=standard|fast`

## Run

1. Instructions: `~/.agents/codex/instructions/onboard.md`  
2. Schemas + checks (MUST):  
   `~/.claude/skills/project-onboard/references/PACK-SCHEMAS.md`  
   `~/.claude/skills/project-onboard/references/VALIDATION.md`  
   `~/.claude/skills/project-onboard/references/design-md-standard.md` (Google `@google/design.md`)  
3. Seed + detect:

```bash
export PATH="$HOME/.agents/bin:$PATH"
cd "$PROJECT_CWD"
# Default CLI = full pipeline (seed + fill). Do NOT agents-doctor --apply (wipes routing.profile).
ARGS=()
[[ -n "${ONBOARD_SCENARIO:-}" ]] && ARGS+=(--"$ONBOARD_SCENARIO")
[[ "${ONBOARD_DEPTH:-}" == "fast" || "${ONBOARD_DEPTH:-}" == "deep" ]] && ARGS+=(--"$ONBOARD_DEPTH")
project-onboard "$PROJECT_CWD" "${ARGS[@]}"
```

4. Model/effort/tier come from adoc `stages.onboard` → `.agents/onboard.scenario.yaml`.  
5. Default run executes Codex/Cursor with **onboard.md** phases; Phase 5 runs VALIDATION.md.  
6. Timeout default **3600s** deep / **1200s** fast (`ONBOARD_TIMEOUT` overrides).

```bash
CODEX_MODEL="${CODEX_MODEL:-}"
CODEX_REASONING="${CODEX_REASONING:-}"
ONBOARD_SERVICE_TIER="${ONBOARD_SERVICE_TIER:-}"
SCENARIO_FILE=.agents/onboard.scenario.yaml
DEPTH=$(awk '/^depth:/{print $2; exit}' "$SCENARIO_FILE" 2>/dev/null || echo deep)
[[ "$DEPTH" == "fast" ]] && DEPTH=minimal
[[ -z "$CODEX_MODEL" ]] && CODEX_MODEL=$(awk '/^model:/{print $2; exit}' "$SCENARIO_FILE" 2>/dev/null || true)
[[ -z "$CODEX_REASONING" ]] && CODEX_REASONING=$(awk '/^reasoning_effort:/{print $2; exit}' "$SCENARIO_FILE" 2>/dev/null || true)
[[ -z "$ONBOARD_SERVICE_TIER" ]] && ONBOARD_SERVICE_TIER=$(awk '/^service_tier:/{print $2; exit}' "$SCENARIO_FILE" 2>/dev/null || echo standard)
if [[ -z "$CODEX_MODEL" ]]; then
  if [[ "$DEPTH" == "deep" ]]; then CODEX_MODEL=gpt-5.6-sol; else CODEX_MODEL=gpt-5.6-terra; fi
fi
if [[ -z "$CODEX_REASONING" ]]; then
  if [[ "$DEPTH" == "deep" ]]; then CODEX_REASONING=high; else CODEX_REASONING=medium; fi
fi
# codex exec --model "$CODEX_MODEL" -c model_reasoning_effort="$CODEX_REASONING" \
#   ${ONBOARD_SERVICE_TIER:+-c service_tier="$ONBOARD_SERVICE_TIER"} ...
```

## Expect

- Phase artifacts (deep) + `report.md`  
- `docs/llm/MODULE_MAP.yaml` with real modules (deep)  
- CLAUDE.md not a stub; AGENTS.md pointer only  
- Phase4b: each `apps/*` walked → local `CLAUDE.md` + `docs/` (APP_PACKS in report)  

## Completion

Last line: `DONE <path-to-report-or-CLAUDE.md>` or `FAILED <reason>`, then **stop**.
