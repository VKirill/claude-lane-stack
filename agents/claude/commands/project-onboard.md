---
description: Onboard project — dual scenario + deep forensic by default on mature repos (Codex)
---

Онбординг репозитория делает **codex-onboarder** (не Grok). Fable не пишет CLAUDE.md руками.

## Args

`$ARGUMENTS` may include path and flags:

- path to repo (default: cwd)
- `deep` / `fast` — depth override
- `full` / `minimal` — scenario override

Examples: `/project-onboard` · `/project-onboard deep` · `/project-onboard /path/to/repo fast`

## Steps

1. `PROJECT_CWD` = path from args or cwd (absolute). 
2. Parse depth/scenario from `$ARGUMENTS` → `ONBOARD_DEPTH`, `ONBOARD_SCENARIO` if present. 
3. Spawn **Agent → codex-onboarder**:

```text
PROJECT_CWD: <abs>
ARTIFACT_DIR: <abs>/.agents/runs/_onboard/artifacts/001
FORCE: 0
ONBOARD_DEPTH: deep|fast # if user asked; else omit (auto: full→deep, minimal→fast)
ONBOARD_SCENARIO: full|minimal # only if user asked
```

4. Wait for finish. Read:
   - `.agents/onboard.scenario.yaml`
   - `ARTIFACT_DIR/report.md`
   - skim `CLAUDE.md` (must not be “Edit me”)

5. Reply in **Russian**:
   - scenario + **depth** + score
   - files created/updated
   - verify result (if deep)
   - wiki mismatches
   - gaps / next step

6. If depth was deep but report is thin (no MODULES_READ / still stub CLAUDE) → say **partial** and offer re-run `--deep`.

Do **not** implement product features in this command.

If `codex` CLI missing: run `project-onboard` shell seed only, warn that deep fill needs Codex/agent write path.
