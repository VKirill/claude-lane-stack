---
name: seo-project-life
description: "Карта жизни SEO-проекта: где лежат паспорт, доска, фазы, модули, CLI. Не пишет код и не запускает 18 модулей подряд. Use when: где seo, паспорт SEO, BOARD SEO, seo-resume, harness пуст, seo-module, playbook, ANAMNESIS, .agents/seo. SKIP: код сайта (→dev-orchestrator / project-life); один DrMax-промпт (→thin skill / originals)."
argument-hint: "[info]"
---

# SEO project life — where things live

> **Inside a Lane Pilot chat** (`LANE_PILOT_AGENT_TYPE` set / tools `lane_pilot_*` present) skip the `seo-*` CLI (`seo-init`, `seo-resume`, `seo-dispatch`, `seo-services`), `seodoc` and the `seo-system` catalog: work from the code, the docs and your skills, and keep artifacts in `.agents/seo/<slug>/` if it exists. Site-code fixes: describe them in your final message (files and acceptance) under a block «для PM»; the PM dispatches the writer. The loop below is the terminal SEO harness.

## Info

If `$ARGUMENTS` is exactly `info`, print `references/info.md` verbatim (Russian), then stop.

## Two layers

| Layer | Path | What it is |
|-------|------|------------|
| Project life | `<repo>/.agents/seo/<slug>/` | This client's state. Disk is SoT. |
| Capability catalog | `~/.agents/seo-system/` | 18 modules + playbooks. Not per-project. |
| CLI | `~/.agents/bin/seo-*` | `seo-resume`, `seo-module`, `seo-dispatch`, … |
| Settings | `seodoc` | Providers, OpenRouter models, stage agents |
| Originals | thin DrMax skills (`ORIGINAL.md` / `originals/`) | Open 1:1, never rewrite |

If `~/.agents/seo-system/modules` is missing: the catalog is not installed.
Do not invent playbooks. Tell the human to rerun lane-stack `./install.sh`
(or seo-orchestration `./install.sh`). Then `seo-module list`.

## Folder map (project)

```text
<repo>/.agents/seo/
  BOARD.md HANDOFF.md HANDOFF.json
  <slug>/
    PROJECT.md STATUS.md BOARD.md ANAMNESIS.md
    passport/ discovery/ strategy/ technical/
    content/ offpage/ measurement/ evidence/
    prompts-used/log.tsv
    runs/<run>/{PLAN.md,STATUS.md,tasks/,artifacts/}
```

Full tree: `seo-drmax-orchestrator/references/seo-project-layout.md`.

`STATUS.phase` is one of: `passport|discovery|strategy|technical|content|offpage|measure`.

## Catalog (host, not the project)

```text
~/.agents/seo-system/
  registry.yaml
  modules/<id>/{module.yaml,MODULE.md,scenarios/*.yaml}
  playbooks/*.yaml
```

```bash
seo-module list
seo-module scenario <mod> <scen>    # then open listed originals
seo-module playbook live-site-start
```

Playbooks only chain modules. They do not hold client facts.

## Decision guide

| X | Goes to |
|---|---------|
| «где мы / что дальше» | `seo-resume` + `STATUS.md` (`phase` / `next`) |
| facts vs guesses | `ANAMNESIS.md` + `passport/` |
| SERP / freq export | `evidence/` (dated) — else mark hypothesis |
| one DrMax system | `seo-module scenario` → original 1:1 → artifact under the phase folder |
| bulk / cheap pass | `seo-dispatch --stage …` (executor from `seo-routing resolve`) |
| site code fix | `.agents/runs/` + `dev-orchestrator` (Lane Pilot: final message to the PM) — not `.agents/seo/` |
| code todos / plans | skill `project-life` — different tree |
| API keys | `seodoc` / `~/secrets/` — never STATUS or task YAML |

## Session loop

```text
seo-resume
→ work STATUS.next (module scenario, not a vibe pipeline)
→ write the artifact
→ seo-prompt-log if an original ran
→ seo-board && seo-handoff-write
```

## Anti-patterns

- ❌ Invent a full OT→DO pipeline without scope
- ❌ Strategy without passport (unless user skips + gaps logged)
- ❌ Chat summary as the DrMax original
- ❌ Rewrite / merge originals
- ❌ Treat `seo-system/modules` as the client project
- ❌ Write product code from an SEO session
