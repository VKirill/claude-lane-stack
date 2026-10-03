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
- UI-экран: read_first DESIGN.md этой поверхности + web-design + design-taste + impeccable-ui.

Важнее этого файла
- CLAUDE.md / AGENTS.md в PROJECT_CWD и правила проекта в брифе
- Каталог и *.test / *.spec как уже в репо

Не твоя работа
- wiki/README, review, CI/docker, commit/push/merge, всё вне owns_paths
