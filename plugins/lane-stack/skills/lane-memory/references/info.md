lane-memory — факты проекта, которые нельзя вывести из кода

Зачем
- Правила «всегда так» сидят в ядре и грузятся каждую сессию (не поиск).
- Остальное — по запросу: lane-memory context / search.
- Пишет только команда lane-memory write (одна дверь). Ночной агент не чинит сам.

Раскладка
- Один корпус на хабе BB (Lane Pilot): write | search | context | core идут через session_memory_*.
- .cls/memory-outbox/ — буфер, если нет связи с хабом (lane-memory flush).
- .cls/local-memory/ — только эта машина, не git; сюда идут записи sensitive.
- .cls/index/ — SQLite FTS, производный.
- .agents/memory/ — старый локальный корпус; пишется только при LANE_MEMORY_HUB=off.

Спросить корпус
lane-memory context . "почему сводку не по шаблону"
lane-memory search . "handoff"
lane-memory core .
lane-memory explain . --task "подготовь поставку"

Записать факт
черновик вне .agents/memory (references/draft-template.md) →
lane-memory write --apply .cls/drafts/<id>.md --confirm .agents/memory/<id>.md --yes

Урок = правило для хаба
lane-memory lesson "<правило>" --for pm|writer|both [--always]
(в чате Lane Pilot PM: инструмент lane_pilot_lesson)

Не класть сюда
структуру репо, git-историю, PROGRESS, YAML рана — у них свои файлы.
