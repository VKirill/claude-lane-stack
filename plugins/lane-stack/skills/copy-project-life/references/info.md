copy-project-life — файлы копирайта. Не SEO и не код.

Диск (шаблоны из references/)
<repo>/.agents/copy/
  INDEX.md                  доска статусов
  ANAMNESIS.md
  audience.md
  buyer-personas/p1.md
  voice.md
  pages/<slug>.md
  research/inbox/           сырой ресёрч (дата-slug)
  research/used/            уже подняли в audience/pages
  research/dead/            шум

status: unknown → draft → fillable → approved → locked
locked = не переписывать. on_site (страницы) ≠ status.

Первый полный анализ (нет .agents/copy/ или пустой product)
1 скопировать шаблоны
2 опрос пачками по 2–3 вопроса — references/first-interview.md
   оффер → ЦА → персона/доказательства
3 ответы сразу в файлы; «не знаю» = unknown
4 потом audience → headlines → ux
Без оффера H1 не писать.

Цепочка (повторный заход)
1 ANAMNESIS   → site-copy-audience
2 audience + персоны → site-copy-audience
3 pages/<slug> заголовки → site-copy-headlines
4 pages/<slug> UI      → site-copy-ux
5 серый HTML           → page-prototype
6 русский текст        → ru-text на ходу; вычитка ru-check; балл ru-score

Агент
- copy-lead  /  LANE_PM_AGENT=copy-lead lane-pm
- claude --agent copy-lead
- стиль /config → copywriter (только в этой сессии; не делать дефолтом проекта)
- профессий в модели нет — шляпы в craft.md

Нельзя
- писать H1 без audience.md
- выдумывать цитаты
- дублировать DESIGN.md в voice.md
- трогать locked
- писать весь ресёрч в один web.md
