resume-project — холодный старт («где мы»)

Когда
- Новая сессия оркестратора на живом репо.
- «где мы / продолж / resume / handoff».
- Не для туду и не для нового онбординга.

Как открыть шпаргалку
- /lane-stack:resume-project info
- каталог: /lane-stack:info

Запуск
- /lane-stack:resume-project
- /resume-project
- CLI: ~/.agents/bin/resume-project "$(pwd)" --compact

Что ответить (из HANDOFF, коротко по-русски)
- Now
- Blocked + next_act (fix_contract → не респавнить writer)
- Next — только типизированные акты
- Profile: main_write + workspace

Нельзя
- просить человека мержить
- кодить как PM
- слепой retry при next_act=fix_contract
- вываливать сырой BOARD в чат
