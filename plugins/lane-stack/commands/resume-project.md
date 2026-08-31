---
description: Run resume-project now — Now / Blocked / Next. Not a cheat sheet.
argument-hint: "[path|--compact|info]"
---

If `$ARGUMENTS` is exactly `info`: load skill `resume-project` and print **only** its info card, then stop.

Otherwise **run the CLI now**. Do not explain the skill. Do not print the cheat sheet.

```bash
export PATH="$HOME/.agents/bin:$PATH"
if [ -n "$ARGUMENTS" ]; then
  resume-project $ARGUMENTS
else
  resume-project "$(pwd)" --compact
fi
```

Then in Russian, short, **from HANDOFF** (not raw BOARD):

- **Now**
- **Blocked** + `next_act` (`fix_contract` → do not re-dispatch writer)
- **Next** — typed acts only
- Profile: `main_write` + workspace

If a run is done but unmerged: plan `wt-merge-main` (you merge — never ask the human).
