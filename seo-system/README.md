# SEO system — modular hierarchy

```text
~/.agents/seo-system/
  registry.yaml           # index of all modules + playbooks + phases
  schemas/
    module.schema.yaml    # contract for new modules
    module.template/      # copy-paste starter
  modules/<id>/
    module.yaml           # machine manifest
    MODULE.md             # human/agent protocol
    scenarios/*.yaml      # work scenarios for this module only
  playbooks/*.yaml        # cross-module chains (OT→DO)
  scripts/                # optional helpers
```

## Rules

1. **One concern = one module directory.** No mega-files.
2. **Every module has scenarios.** Agents run `seo-module scenario <mod> <scen>`.
3. **Playbooks only chain modules** — they do not embed business logic.
4. **Add a module without rewriting the core:**
   - `cp -r schemas/module.template modules/my-mod`
   - fill `module.yaml` + `MODULE.md` + `scenarios/`
   - append `my-mod` to `registry.yaml` → `modules:`
   - `seo-module validate my-mod`
5. **CLI binaries** stay in `~/.agents/bin`; modules *declare* them, not own them.
6. **Project artifacts** always under `.agents/seo/<slug>/` (declared in `artifacts.writes`).

## CLI

```bash
export PATH="$HOME/.agents/bin:$PATH"
seo-module list
seo-module show passport-onboard --full
seo-module scenario content-gist creation
seo-module playbook live-site-start
seo-module playbook list
seo-module provides
seo-module validate
```

## Active modules

| ID | Phase |
|---|---|
| core-harness | core |
| services-data | data |
| routing-agents | core |
| proxy-fetch | data |
| html-markdown | technical |
| passport-onboard | passport |
| site-scan | technical |
| discovery-research | discovery |
| intent-semantics | discovery |
| clustering-serp | discovery |
| strategy-evidence | strategy |
| technical-seo | technical |
| content-gist | content |
| content-quality | content |
| brand-entity | offpage |
| offpage-links | offpage |
| measurement-analytics | measure |
| worker-dispatch | core |

## Agent contract

On any SEO task:

1. `seo-module list` or registry phase map → pick module  
2. `seo-module scenario <mod> <scen>` → steps  
3. Read `MODULE.md` + open DrMax originals listed in `module.yaml`  
4. Write only declared artifacts  
5. `seo-prompt-log` when originals run  

## Docs

- Methodology: `~/.agents/docs/seo/METHODOLOGY-END-TO-END.md`
- Harness ops: `~/.agents/docs/seo/SOLO-SEO-ORCHESTRATION.md`
- Data TUI: `~/.agents/docs/seo/SEO-SERVICES-TUI.md`
