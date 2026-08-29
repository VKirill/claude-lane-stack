---
name: docs-maintain
description: Keep living docs/ honest after code changes. Use when: info, справка, lane-stack:docs-maintain info, nightly docs, docs-maintain, обновить документацию, актуализировать ARCHITECTURE.
argument-hint: "[info]"
---

# Docs maintain

## Info (print and stop)

If `$ARGUMENTS` is `info`, or the user says `info` / `справка` / `как запускать` this skill:
print the block below **verbatim** (Russian), then **stop**. Do not start docs-maintain.

```text
docs-maintain — живые docs/. Не фичи.

Когда
- «обнови документацию / nightly docs / INIT docs».
- После дневных коммитов. Не wiki/, не TODO/, не docs/plans/.

Как открыть шпаргалку
- /lane-stack:docs-maintain info
- каталог: /lane-stack:info

Запуск
- adoc → Документация → Enabled → Apply
  (паспорт тонкий → project-onboard, потом wiki)
- docs-init-chain /path/to/repo
- docs-maintain-project /path/to/repo
- docs-maintain-project /path/to/repo lint
- docs-maintain-all --if-hour
- агент: сначала project-onboarder, потом docs-maintainer

Как работает
1) Паспорт тонкий — отдельный агент project-onboarder. Wiki не стартует раньше.
2) docs-web: шапки / stubs / web.yaml / INDEX. Без LLM.
3) docs-stale: owns ∪ цитаты ∪ stub/thin. Luna wiki INIT/night. Не коммитит.
   Отчёт: .agents/session-log/DOCS-YYYY-MM-DD.md
   Daylog: .agents/session-log/DOCS-DAY-YYYY-MM-DD.md
```

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
- Archive (`wiki/`, `TODO/`, `docs/plans/`) is never written.
- No feature code. No commit.

## Cron

```bash
0 * * * * $HOME/.agents/bin/docs-maintain-all --if-hour >>$HOME/.agents/logs/docs-maintain.log 2>&1
```
