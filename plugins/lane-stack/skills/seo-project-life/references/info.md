seo-project-life — карта SEO-проекта. Не код.

Два слоя (не путать)
1) Жизнь проекта  →  <repo>/.agents/seo/<slug>/
2) Каталог умений →  ~/.agents/seo-system/modules/   (CLI: seo-module)

Цепочка
passport → discovery → strategy → technical → content → offpage → measure

Как открыть
- /lane-stack:seo-project-life info
- агент: cc s  /  claude --agent seo-specialist
- настройки API/моделей: seodoc

Фразы → действие
- «где мы / продолж»     → seo-resume .
- «пустой harness»       → seo-init <slug> --domain …
- «живой сайт с нуля»    → seo-module playbook live-site-start
- «сайта ещё нет»        → seo-module playbook greenfield-start
- «одна статья»          → seo-module playbook one-article
- «какой модуль»         → seo-module list  затем  seo-module scenario <mod> <scen>
- «после работы»         → seo-board . && seo-handoff-write .

Куда писать
- факты проекта     STATUS.md / ANAMNESIS.md / passport/
- исследование      discovery/
- стратегия/кокон   strategy/
- техника           technical/   (код сайта → .agents/runs/ + dev-orchestrator; Lane Pilot: отчёт PM)
- черновики/GIST    content/
- ссылки/бренд      offpage/
- цифры/SERP        measurement/  evidence/serp/
- прогон промпта    prompts-used/log.tsv

На диск — English keys. В чат — русский. Секреты не писать.
