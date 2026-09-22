---
description: Claude Lane OpenCode half — шпаргалка, диагноз прогона, куда класть код плагина
argument-hint: "[info]"
---

Read `/home/ubuntu/.agents/pm-skills/opencode-lane/SKILL.md` and follow it.

If `$ARGUMENTS` is empty, `info`, `справка`, or `как запускать`:
print the **Info** block from that skill verbatim (Russian), then **stop**.
Do not glob. Do not search. Do not edit files.

If `$ARGUMENTS` is `диагноз` or contains «делай диагноз»:
follow **Diagnose a writer run** in that skill, then stop unless asked to fix.

Otherwise follow the skill: OpenCode code only under
`profiles/opencode/opencode-lane/` + `index.ts`. No second plugin.
