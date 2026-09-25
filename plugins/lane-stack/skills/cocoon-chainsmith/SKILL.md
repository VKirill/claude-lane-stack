---
name: cocoon-chainsmith
description: "DrMax COCOON CHAINSMITH v3 — fills 9 YAML vars and emits a verified CP-Navigator command sequence for Cocoon Engine X4. Does not run research. Use when: Chainsmith, связка команд, пошаговый план кокона, сгенерируй команды X4, маршрут /исследование. SKIP: executing the cocoon (→drmax-cocoon-engine-x4 / cocoon-pilot); one-query intent (→drmax-latent-intent); live URL experiment (→drmax-signalforge)."
---

# COCOON CHAINSMITH v3

Official DrMax meta-prompt. It **plans** the X4 command chain. It does not
run Reddit Mapper, TGA, GIST, or any live research.

## When

- Need a ready, checked sequence of CP-Navigator commands for a real task
- Minimal intake: the nine YAML variables in [ORIGINAL.md](ORIGINAL.md)
- Replaces local adaptations such as the removed `drmax-research-playbook`

## Protocol

1. Attach / open the four Cocoon Engine X4 skills **before** generating:
   `cocoon-pilot` (CP-Navigator), `reddit-mapper`, `topical-graph-architect`,
   `gist-content-logic` — or the bundled `drmax-cocoon-engine-x4`.
   Without them the generator cannot verify commands.
2. Apply **1:1**: [ORIGINAL.md](ORIGINAL.md)
3. Fill only the nine variables (`GEO`, `LANGUAGE`, `SITE_THEME`, `SITE_URL`,
   `TASK_TYPE`, `TASK_DESCRIPTION`, `MODE`, `DEPTH`, `BRANCHING`). Extra
   constraints go in `TASK_DESCRIPTION`, not as new fields.
4. If `GEO`, `LANGUAGE`, `SITE_THEME`, or `TASK_TYPE` are missing and cannot
   be taken from the current brief, ask once — then generate.
5. Output the command chain. Do **not** execute it unless the user then asks
   to run X4. Hand off execution to `drmax-cocoon-engine-x4` / `cocoon-pilot`.

## Place in pipeline

```
brief → Chainsmith (this skill) → X4 execution → optional Humanization
```

Do not mix this planning pass with a live-URL SignalForge job.

## Related

- `drmax-cocoon-engine-x4` / `cocoon-pilot` — execute the generated commands
- `drmax-latent-intent` — one query, no chain
- `drmax-signalforge` — one published URL, not a new cocoon
