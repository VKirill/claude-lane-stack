project-onboard — первичная карта репо (CLAUDE.md + LLM-pack)

Когда
- Нет CLAUDE.md / пустой или чужой репо.
- Уже живой UI без DESIGN.md → design-lead (project-design), не повторный onboard.

Как открыть шпаргалку
- /lane-stack:project-onboard info
- каталог: /lane-stack:info

Запуск
- /project-onboard
- /project-onboard deep
- /project-onboard /path/to/repo fast
- CLI: project-onboard .
- агент: project-onboarder (Codex, не Grok)

Флаги
- deep / fast — глубина
- full / minimal — scenario
- --seed-only — только заглушки, без модели

После
- RU-саммари: поверхности, модули, тесты, DESIGN?, RUNBOOK?
- has_ui → docs/DESIGN.md (Google)
- docs включены + паспорт тонкий → сначала этот скилл / project-onboarder, потом docs-maintainer
- weekly refresh: docs-maintainer, не этот скилл
