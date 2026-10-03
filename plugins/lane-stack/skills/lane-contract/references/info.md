lane-contract — контракт задачи (YAML в .agents/runs/)

Когда
- Оркестратор заполняет tasks после «делай».
- Проверка owns_paths / verification / acceptance.

Как открыть шпаргалку
- /lane-stack:lane-contract info
- каталог: /lane-stack:info
- раны целиком: /lane-stack:orchestrator-lanes info

PM до dispatch
1) run-init → PLAN/SPEC/tasks
2) owns_paths + never_touch + acceptance (поведение, не «всё зелёное»)
3) read_first = существующие файлы; окна строк = context_selectors; interfaces = сигнатуры или []
4) Одна задача = один product outcome. depends_on только compile/data.
5) Parallel только при disjoint owns.
6) run-validate --phase pre-dispatch
7) Один run-supervisor. lane = adoc main_write.

Писатель
- Только owns_paths. Не `.agents` (`run-validate` rejects it — sandbox remounts `.agents` read-only). Не merge/push main.
- Не гоняй тесты/typecheck — это L1 контроллера. Пиши тесты в owns, не запускай. Вне owns сломалось → Gaps.

Тиры
- L0 writer: код, тесты не запускать  · L1 lane-ctl verify  · L2 PM/CI

Нельзя
- timeout_sec в плане выдумывать (дефолт 900)
- verification[].command на файл, которого нет в cwd/worktree
- node_modules / кэши в owns
- мутировать YAML после первого старта
