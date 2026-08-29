# Solo SEO orchestration (seo-specialist harness)

Parallel to [SOLO-ORCHESTRATION.md](../SOLO-ORCHESTRATION.md) for **code**, this document is the control plane for **SEO**.

**Related:** skill `seo-drmax-orchestrator` · agent `seo-specialist` · CLI `seo-*` in `~/.agents/bin`

## Launch

```bash
cc          # menu → press s
ccs         # alias: claude --agent seo-specialist
claude --agent seo-specialist
```

Agent **boots** with `seo-resume` (handoff + board + focus STATUS). Chat language: Russian. Files: English-friendly paths; client prose RU/EN as needed.

## Modular architecture (mandatory)

All capabilities live as **independent modules**:

```text
~/.agents/seo-system/
  registry.yaml
  modules/<id>/{module.yaml,MODULE.md,scenarios/*.yaml}
  playbooks/*.yaml
```

```bash
seo-module list
seo-module scenario <module> <scenario>
seo-module playbook live-site-start
seo-module validate
```

**Add a module:** copy `schemas/module.template` → `modules/<id>/`, fill files, append id to `registry.yaml`, run `seo-module validate <id>`.  
See `~/.agents/seo-system/README.md`.

## Non-negotiables

1. **Disk is truth.** Chat is disposable. State lives under `.agents/seo/`.
2. **Passport before strategy.** No full strategy without Collector→Validator (or logged gaps + explicit user skip).
3. **Originals 1:1.** Never rewrite DrMax prompts; open files under `seo-prompt-engineering-2026/references/originals/`.
4. **Newest version for new work.** LinguaForensic 3.9.4, GIST 3.3, Humanization 1.6.1, CVD 2.3, Latent Intent 2.2, Forensic v3.
5. **Evidence over vibe.** SERP/freq/traffic require tools + date/region; else mark hypothesis.
6. **Provenance.** Every prompt run → `seo-prompt-log` (or row in `prompts-used/log.tsv`).
7. **Delegation contract.** Workers get original path + inputs + output path via `seo-dispatch`; never «сделай по DrMax» alone.
8. **Code fixes ≠ SEO research.** Research stays in `.agents/seo/`; site code changes go to `.agents/runs/` + `dev-orchestrator`.
9. **Handoff after meaningful work.** `seo-board && seo-handoff-write` before ending a session.

## CLI map

| Command | Role |
|---|---|
| `seo-init <slug> --domain d` | Create project tree + STATUS |
| `seo-resume [repo] [-p slug]` | Cold start brief |
| `seo-board [repo]` | Regenerate BOARD.md |
| `seo-handoff-write [repo]` | HANDOFF.json + HANDOFF.md |
| `seo-run-init <slug> <run> --title … --phase …` | Durable run |
| `seo-task <slug> <run> list\|add\|set-status\|accept` | Task lifecycle |
| `seo-dispatch <slug> <run> <id> --original … --output …` | Worker package |
| `seo-prompt-log <slug> --system … --path …` | Provenance TSV |
| `seo-services` / `sseo` | **TUI** connect xmlstock, xmlriver, mutagen, DataForSEO, Yandex, GSC… |
| `seo-services status\|test\|export` | CLI for same registry |
| `seo-onboard live\|greenfield` | Passport **ANAMNESIS** + first scan (live) or brief shell |
| `seo-scan <slug> --url\|--page\|--rescan` | Versioned site/page analysis artifacts |

Providers: [SEO-SERVICES-TUI.md](SEO-SERVICES-TUI.md) · Methodology OT→DO: [METHODOLOGY-END-TO-END.md](METHODOLOGY-END-TO-END.md)

## Layout

```text
.agents/seo/
  BOARD.md HANDOFF.md HANDOFF.json README.md
  <slug>/
    PROJECT.md STATUS.md BOARD.md
    passport/ discovery/ strategy/ technical/
    content/ offpage/ measurement/ evidence/
    prompts-used/log.tsv
    runs/<run>/
      run.yaml PLAN.md STATUS.md
      tasks/*.yaml
      artifacts/<task_id>/{state,report,outcome,acceptance,dispatch}.…
```

## Phase machine

```text
passport → discovery → strategy → technical → content → offpage → measure
```

Activation matrix:  
`~/.agents/skills/seo-drmax-orchestrator/references/activation-matrix.md`

## Worker routing (summary)

| Work | Executor |
|---|---|
| Strategy, prioritization | Claude (seo-specialist) |
| Heavy single DrMax system | Claude subagent + original |
| Bulk latent-intent / CVD | qwen / deepseek / kimi via dispatch |
| Drafts from GIST plan | grok / qwen |
| Mutagen / xmlstock / GSC / GA4 | main agent Bash+curl |
| Site implementation | dev-orchestrator |

## Session loop

```text
seo-resume
→ read focus STATUS + active run PLAN
→ seo-task … set-status running
→ execute (self or seo-dispatch + worker)
→ write artifact under .agents/seo/<slug>/…
→ seo-prompt-log …
→ seo-task … accept
→ update STATUS next/phase
→ seo-board && seo-handoff-write
```

## End-state of a healthy session

- `STATUS.md` has honest `next` and `phase`
- At least one artifact path on disk
- HANDOFF regenerated
- Open tasks reflected on BOARD
- No invented metrics left unmarked as hypotheses
