---
name: writer-practices
description: Lane-writer code style inside owns_paths. Naming, errors, tests. Use when user says info, справка, lane-stack:writer-practices info, or when implementing a TASK_FILE, not for PM planning or docs.
license: MIT
argument-hint: "[info]"
---

# Writer practices

## Info (print and stop)

If `$ARGUMENTS` is `info`, or the user says `info` / `справка` / `как запускать` this skill:
print the block below **verbatim** (Russian), then **stop**. Do not edit product code.

```text
writer-practices — стиль кода внутри owns_paths. Для writer, не PM.

Когда
- Идёт TASK_FILE, пишется продукт.
- Не для плана, не для docs-maintain, не для DESIGN.md.

Как открыть шпаргалку
- /lane-stack:writer-practices info
- каталог: /lane-stack:info

Правила
- Имена: verb+noun (fetchUser). Bool: is/has/can/should. Не tmp, не data2.
- Одна функция = одна работа. Early return. Хелпер на один вызов не выделять.
- Ошибки: сообщение + контекст. Пустой catch / return null — нельзя.
- Тест: одно поведение, контракт, не private internals.
- Нет drive-by format и «раз уж я здесь».

Важнее этого файла
- CLAUDE.md / AGENTS.md / .agents/LESSONS.md в PROJECT_CWD
- Каталог и *.test / *.spec как уже в репо

Не твоя работа
- wiki/README, review, CI/docker, commit/push/merge, всё вне owns_paths
```

For **lane writers** only. Karpathy (think → minimum → surgical → verify) still applies.

Source idea: [aif-best-practices](https://github.com/lee-to/ai-factory/blob/2.x/skills/aif-best-practices/SKILL.md). Their factory, evolve, review, and docs skills are not ours.

## Override

`CLAUDE.md` / `AGENTS.md` / `.agents/LESSONS.md` in `PROJECT_CWD` beat this card.
Match file names, casing, and `*.test` / `*.spec` already in the repo.
Do not create `.agents/**`, wiki, or README unless that path is in `owns_paths`.

## Write

- Names: verb+noun (`fetchUser`). Bool: `is` / `has` / `can` / `should`. No `tmp` or `data2`.
- One function = one job. Early return. Do not extract a helper used once.
- Errors: specific message + context. Never empty `catch` / `return null` to hide a throw.
- Tests: one behavior per test; assert the contract, not private internals.
- No drive-by format, comments, or "while I'm here" refactors.

## Not your job

Docs/wiki refresh, PR review tone, CI/docker, commit/push/merge, anything outside `owns_paths`.
