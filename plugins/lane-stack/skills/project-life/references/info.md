project-life — туду, план, память. Не ран.

Цепочка
idea → todo → plan → run → merge
                 память: PROGRESS · уроки→хаб · decisions

Как открыть шпаргалку
- /lane-stack:project-life info
- каталог: /lane-stack:info

Фразы → действие
- «запиши / туду / потом / не теряй»     → .agents/todos/ + INDEX
- «покажи туду»                         → прочитай INDEX, ответь по-русски
- «закрой / сделано / не надо»          → status done/dropped
- «планируем / не запускай / обсудим»   → .agents/plans/items/<slug>/, ран НЕ открывать
- «архитектор / новое приложение / сервис» → skill app-architect, artifacts/ в том же плане
- «делай / реализуй / в работу»         → выход в ран (Lane Pilot: lane_pilot_dispatch_writer; терминал: orchestrator-lanes)
- «где мы / продолж»                    → это resume-project, не этот скилл

План без рана
1) .agents/plans/items/<YYYY-MM-DD-slug>/  status: draft
2) Решения в PLAN.md + History. Чат не хранилище.
3) UI: в Links должен быть docs/DESIGN.md (или spawn design-lead).
4) Запрещено до «делай»: run-init, run-supervisor, Claude Plan mode, ~/.claude/plans/

Файлы
- .agents/todos/   .agents/plans/   .agents/PROGRESS.md   (lessons: `lane-memory lesson`, on the hub)
- .agents/decisions/ = черновики решений; docs/decisions.md публикует ночной проход документации
- .agents/plans/ = длинная стратегия, не очередь задач
- docs/ = только документация кода (её ведёт ночной проход: Lane Pilot или docs-maintain); вход — PROJECT.md → docs/index.md

На диск — English. В чат — русский. Секреты не писать.
