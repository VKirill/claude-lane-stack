---
name: seo-project-life
description: "Карта жизни SEO-проекта: где лежат паспорт, доска, фазы, модули, CLI. Не пишет код и не запускает 18 модулей подряд. Use when: seo info, где seo, паспорт SEO, BOARD SEO, seo-resume, harness пуст, seo-module, playbook, ANAMNESIS, .agents/seo. SKIP: код сайта (→dev-orchestrator / project-life); один DrMax-промпт (→thin skill / originals)."
argument-hint: "[info]"
---

# SEO project life — where things live

## Info (print and stop)

If `$ARGUMENTS` is `info`, or the user says `info` / `справка` / `где seo` this skill:
print the block below **verbatim** (Russian), then **stop**.

```text
seo-project-life — карта SEO-проекта. Не код.

Два слоя (не путать)
1) Жизнь проекта  →  <repo>/.agents/seo/<slug>/
2) Каталог умений →  ~/.agents/seo-system/modules/   (CLI: seo-module)

Цепочка
passport → discovery → strategy → technical → content → offpage → measure

Как открыть
- /lane-stack:seo-project-life info
- агент: cc s  /  claude --agent seo-specialist
- настройки API/моделей: seodoc

Фразы → действие
- «где мы / продолж»     → seo-resume .
- «пустой harness»       → seo-init <slug> --domain …
- «живой сайт с нуля»    → seo-module playbook live-site-start
- «сайта ещё нет»        → seo-module playbook greenfield-start
- «одна статья»          → seo-module playbook one-article
- «какой модуль»         → seo-module list  затем  seo-module scenario <mod> <scen>
- «после работы»         → seo-board . && seo-handoff-write .

Куда писать
- факты проекта     STATUS.md / ANAMNESIS.md / passport/
- исследование      discovery/
- стратегия/кокон   strategy/
- техника           technical/   (код сайта → .agents/runs/ + dev-orchestrator)
- черновики/GIST    content/
- ссылки/бренд      offpage/
- цифры/SERP        measurement/  evidence/serp/
- прогон промпта    prompts-used/log.tsv

На диск — English keys. В чат — русский. Секреты не писать.
```

## Two layers

| Layer | Path | What it is |
|-------|------|------------|
| Project life | `<repo>/.agents/seo/<slug>/` | This client's state. Disk is SoT. |
| Capability catalog | `~/.agents/seo-system/` | 18 modules + playbooks. Not per-project. |
| CLI | `~/.agents/bin/seo-*` | `seo-resume`, `seo-module`, `seo-dispatch`, … |
| Settings | `seodoc` | Providers, OpenRouter models, stage agents |
| Originals | skill `seo-prompt-engineering-2026` | Open 1:1, never rewrite |

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
| site code fix | `.agents/runs/` + `dev-orchestrator` — not `.agents/seo/` |
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
