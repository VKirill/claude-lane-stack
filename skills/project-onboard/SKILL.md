---
name: project-onboard
description: Primary project onboarding for Claude Lane Stack. Dual scenario (minimal|full) and dual depth (fast|deep forensic). Creates lean CLAUDE.md + pointer AGENTS.md, PROGRESS/LESSONS, .agents layout. Use when: /project-onboard, онбординг, init project, bootstrap CLAUDE.md, «подготовь проект», deep onboard.
---

# Project onboard (Claude Lane Stack)

## Who runs it

| Role | Agent |
|------|--------|
| **Default writer** | **Codex** via `codex-onboarder` |
| **fast** | `gpt-5.6-terra` + high |
| **deep** (default on full) | `gpt-5.6-sol` + high |
| PM / slash | `/project-onboard` or natural language |
| Fallback | shell `project-onboard` only (seeds; no deep fill) |

Do **not** use AGY or Grok. Do **not** have Fable hand-write the full CLAUDE — dispatch `codex-onboarder`.

## Dual axes

### 1) Scenario — *what* to seed

| | **minimal** | **full** |
|--|-------------|----------|
| When | score &lt; 5 | score ≥ 5 or multi-package |
| Seeds | spine | + GOTCHAS GLOSSARY TESTING deployment nested CLAUDE SECURITY… |

### 2) Depth — *how hard* to analyze

| | **fast** | **deep** (Recommended on full) |
|--|----------|--------------------------------|
| Default | minimal scenario | full scenario |
| Explore | top dirs + manifests | entrypoints, top modules, flows, wiki↔code, run tests |
| CLAUDE | real but shallow OK | evidence-heavy Never/Always + state warnings |
| Report | DEPTH: fast | MODULES_READ ≥8, FLOWS_TRACED, WIKI_MISMATCHES, VERIFY |

```bash
project-onboard .                 # auto scenario + depth
project-onboard . --deep          # force forensic
project-onboard . --fast          # passport only
project-onboard . --full --deep
ONBOARD_DEPTH=deep project-onboard .
```

Auto-written: `.agents/onboard.scenario.yaml` (`scenario` + **`depth`**)  
and `.agents/runs/_onboard/artifacts/001/deep-scan.md` (tree, entrypoints, large files, git status).

## MUST (PM)

1. Spawn:

```text
Agent → codex-onboarder
PROJECT_CWD: /abs/repo
ARTIFACT_DIR: /abs/repo/.agents/runs/_onboard/artifacts/001
ONBOARD_DEPTH: deep    # omit to use auto from scenario.yaml
```

2. After agent finishes, reply in **Russian**: scenario, **depth**, files, verify result, wiki mismatches, gaps, next step.

3. If report says `DEPTH: deep` but `MODULES_READ` thin or only stubs filled → treat as **partial**, re-dispatch with explicit deep.

## Goal

Cold-start passport that agents can trust. Deep mode is **forensic**: code first, wiki second, no fiction.

## Where things go

| Kind | Path |
|------|------|
| Execution | `.agents/runs/<slug>/` |
| Ideas | `.agents/todos/` |
| Scenario/depth | `.agents/onboard.scenario.yaml` |
| Deep evidence | `.agents/runs/_onboard/artifacts/001/deep-scan.md` |
| Report | `…/report.md` |
| Living | `PROGRESS.md`, `LESSONS.md` |
| Durable docs | `docs/` |

## CLAUDE.md

- ≤150–200 lines body (before gitnexus footer).  
- EN rules; pointers to docs.  
- Lane Stack + karpathy.

## AGENTS.md

Pointer only — do not duplicate CLAUDE.

## After checklist

- [ ] scenario + depth in yaml  
- [ ] deep-scan.md exists  
- [ ] CLAUDE real (not “Edit me”)  
- [ ] report STATUS + DEPTH  
- [ ] deep: MODULES_READ / FLOWS / WIKI_MISMATCHES / VERIFY filled  
- [ ] agents-doctor / routing if available  
