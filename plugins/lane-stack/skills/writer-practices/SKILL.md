---
name: writer-practices
description: Lane-writer code style inside owns_paths. Naming, errors, tests. Use when implementing a TASK_FILE or a Lane Pilot writer task, or when `$ARGUMENTS` is exactly info; not for PM planning or docs.
license: MIT
argument-hint: "[info]"
---

# Writer practices

## Info

If `$ARGUMENTS` is exactly `info` (the slash command, never a task thread), print `references/info.md` verbatim (Russian) and stop. Words like «info» or «справка» inside a task («add a Справка block») are product text, not this command: do the task.

For **lane writers** only. Karpathy (think → minimum → surgical → verify) still applies.

Source idea: [aif-best-practices](https://github.com/lee-to/ai-factory/blob/2.x/skills/aif-best-practices/SKILL.md). Their factory, evolve, review, and docs skills are not ours.

## Override

`CLAUDE.md` / `AGENTS.md` in `PROJECT_CWD` and the project rules in your brief beat this card.
Match file names, casing, and `*.test` / `*.spec` already in the repo.
Do not create `.agents/**`, wiki, or README unless that path is in `owns_paths`.

## Write

- Names: verb+noun (`fetchUser`). Bool: `is` / `has` / `can` / `should`. No `tmp` or `data2`.
- One function = one job. Early return. Do not extract a helper used once.
- Errors: specific message + context. Never empty `catch` / `return null` to hide a throw.
- Tests: one behavior per test; assert the contract, not private internals.
- No drive-by format, comments, or "while I'm here" refactors.
- UI screen: read the `DESIGN.md` of that app if it is in `read_first`; match its tokens and the existing components.

## Not your job

Docs/wiki refresh, PR review tone, CI/docker, commit/push/merge, anything outside `owns_paths`: leave them, and name in your answer what you saw that needs the PM.

## Done

Done = the contract's `verification` commands pass; answer with the changed paths and the results. Contract unclear → no file changes and `NEEDS_HUMAN: <one question>` as the first line of the answer (Lane Pilot); in the terminal report Gaps.

## Say only what you checked

- «Done», «passes», «built», «version X» only after a command or a file read in this same session showed it; name the command. Not checked → say so and give the command that checks it.
- A check that did not run is `NOT RUN: <command>`, never «no errors» and never an empty list. Where you may not run tests (terminal conveyor), write `NOT RUN` with the command, not «tests pass».
- Green parts do not prove they are wired together: for a value or setting you add, one check that follows it to where it is read (setting → launch arguments), not only the computation. A change visible in a window is closed by running it, not by reading the code.
- A test double may do less than the real thing, never differently: same fields, same required frames, same errors, and a loud failure on a path it does not support, not a success.
- After a fix, re-run what it touches when the reach is known and keep the other greens with a one-line reason. A fix to a shared mechanism (launch, isolation, config, the judge, a shared library) or with unknown reach: re-run everything that goes through it.
- The same failure twice in a row: change the angle. Name the class of the error and fix every similar place in one pass (read/grep offline), not the one you hit.
