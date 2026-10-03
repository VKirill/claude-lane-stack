---
name: docs-maintain
description: Keep living docs/ honest after code changes. Use when: nightly docs, docs-maintain, обновить документацию, актуализировать ARCHITECTURE; `$ARGUMENTS` exactly info prints the card.
argument-hint: "[info]"
---

# Docs maintain

> **Inside a Lane Pilot chat** (`LANE_PILOT_AGENT_TYPE` set / the nightly docs prompt) you are the nightly docs pass: write only the paths the prompt names, do not commit (Lane Pilot checks the pages, builds `index.md` and backlinks, and commits), and finish with the short list of the pages you wrote. Method and page contract come from `docs-methodology`. Report files under `.agents/session-log/`, `docs-init-chain`, `docs-maintain-project`, cron and the model line below are the terminal harness.

## Info

If `$ARGUMENTS` is exactly `info`, print `references/info.md` verbatim (Russian), then stop. Do not start docs-maintain.

## Who

**Codex** `gpt-5.6-luna` + `max` + `fast` when `stages.docs.enabled` (adoc). Off by default.

```bash
docs-maintain-project /path/to/repo
docs-maintain-project /path/to/repo lint
docs-maintain-all --if-hour
```

## Markers (project is Lane Stack)

- `CLAUDE.md` contains `Claude Lane Stack`, or
- `.agents/routing.profile.yaml`, or
- `.agents/runs/` exists

## Rules

- First enable: `docs-init-chain` = project-onboard then wiki. Wiki runner refuses a thin passport.
- Night: yesterday git ∩ owns + leftover stubs. Empty → no LLM.
- Archive (`wiki/`, `TODO/`, `.agents/`, legacy `docs/plans/`) is never written. Decision drafts in `.agents/decisions/` are published into `docs/decisions.md`.
- Docs only: feature code goes to a writer lane. The runner commits nothing; the night shift or the owner commits.

## Cron

```bash
0 * * * * $HOME/.agents/bin/docs-maintain-all --if-hour >>$HOME/.agents/logs/docs-maintain.log 2>&1
```
