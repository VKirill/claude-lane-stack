orchestrator-lanes — раны (только сессия dev-orchestrator)

Когда
- Человек сказал «делай / реализуй / в работу / запускай ран».
- До этого — project-life, план в .agents/plans/. Ран не открывать.

Как открыть шпаргалку
- /lane-stack:orchestrator-lanes info
- каталог всех процессов: /lane-stack:info

Старт рана
1) cwd = проект. Сессия = dev-orchestrator.
2) Score один раз (0–2 micro … 11+ спроси).
3) run-init → заполнить PLAN/SPEC/tasks по lane-contract (ТЗ в objective, не проза в interfaces).
4) run-validate --phase pre-dispatch.
5) Один Agent(run-supervisor) на ран.
6) lane из adoc (.agents/routing.profile.yaml), не хардкод kimi.

UI
- Нужны полные docs/DESIGN.md и apps/<app>/docs/DESIGN.md.
- Нет файла → сначала design-lead, потом run-init.
- Task read_first: оба DESIGN.md как пути файлов. Не в owns_paths, если исход не токены.
- YAML задач: ТЗ = objective + acceptance. Не роман в interfaces. Окна строк — context_selectors.

Нельзя
- run-init на фразе «планируем / не запускай»
- Claude Plan mode / ~/.claude/plans/
- второй run-supervisor на тот же ран
- просить человека мержить main
