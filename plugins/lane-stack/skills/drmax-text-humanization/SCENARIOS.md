Ниже — набор рабочих заготовок для ситуации, когда GIST Content Logic уже провёл исследование, сформировал decision map, собрал факты и подготовил черновик. В таком pipeline TEXT HUMANIZATION не исследует товар заново и не «додумывает» преимущества: он сохраняет утверждённую логику, доказательность, условия, цифры и ограничения, одновременно адаптируя под нужный формат и голос.  

## Перед запуском Humanization

Даже если исследование и GIST-черновик находятся в том же чате, перед запуском Humanization лучше передать компактный `GIST HUMANIZATION HANDOFF`. Это снижает риск, что при редактировании потеряются условия, ограничения, статус доказательств, критерии выбора или обязательные проверки.

Минимальный блок, который стоит переносить в каждый сценарий:

```text
GIST HUMANIZATION HANDOFF

GLOBAL GIST CONTRACT:
- Job to be done:
- Topic core:
- Primary decision-relevant distinction:
- Main answer, if applicable:
- Decision map:
- Mandatory selection criteria:
- Mandatory limitations, exclusions, and failure modes:
- Mandatory verification methods:
- Mandatory metrics:
- Mandatory next action / CTA:
- Facts, figures, names, dates, terms, and thresholds that must remain unchanged:
- Claims and evidence status:
- Research context:
- Transfer limitations:
- Terms that must not be simplified:
- Elements that may be compressed:
- Elements that may be reordered:
- Allowed factual material for examples, analogies, and mechanisms:

METRIC VISIBILITY:
- User-facing metrics:
- Internal measurement only:
- Metrics prohibited in user-facing copy:

PROTECTED TERMINOLOGY POLICY:
- Terms to preserve:
- Terms to translate:
- Terms requiring first-use explanation:
- Forbidden substitutions:
- Official names and abbreviations:

BLOCK CONTRACTS:
[Добавьте contracts для характеристик, ограничений, гарантий,
сравнений, инструкций, призывов к действию и критичных claims]

TEXT TO HUMANIZE:
[вставить GIST-черновик]
```

Для электрочайника `XYZ` в protected facts обычно попадут: точное название модели, мощность, объём, материал корпуса, тип нагревателя, диапазон температур — если он есть, гарантия, комплектация, напряжение, сведения о защите и любые цифры из документации. Нельзя превращать наличие функции в обещание результата: например, «поддерживает температуру 80 °C» не равно «всегда идеально заваривает зелёный чай». 

> Для потребительских товаров особенно важно разделять: подтверждённые характеристики производителя, выводы независимого исследования, редакторскую интерпретацию и реальный пользовательский/тестовый опыт.

## Сценарии: электрочайник XYZ

### 1. Карточка товара

**Задача.** Сделать коммерческую карточку понятной и удобной для выбора: быстро объяснить, кому подходит чайник, на что влияют его характеристики, что проверить перед покупкой и какое действие сделать дальше.

**Режим.** Обычно `B_STANDARD_PAGE + FORM_ONLY_HUMANIZATION + PUBLISH`. Если в тексте много электротехнических требований, заявлений о безопасности, гарантий или сравнений с конкурентами, используйте `C_HIGH_RISK` и сначала `EDITORIAL_REVIEW`. 

```text
Используй TEXT HUMANIZATION by DrMax v1.6.1 — RUNTIME FINAL.

DOMAIN / NICHE:
Бытовая техника / электрочайники.

TARGET AUDIENCE:
Покупатели, выбирающие электрочайник для дома или офиса.

PAGE TYPE:
product.

LANGUAGE AND REGIONAL NORM:
Russian, Russia.

TARGET TONE:
Практичный, понятный, коммерческий без рекламной гиперболы.

DESIRED AUTHOR VOICE:
Компетентный консультант магазина.

VOICE PROFILE:
- Professional distance: medium
- Terminology density: medium
- Direct address: limited
- First person: prohibited
- Emotional intensity: restrained
- Figurative language: none
- CTA directness: practical
- Sentence complexity: mixed
- Authorial explicitness: framed
- Evidence visibility: visible
- Narrative energy: calm
- Compression: balanced
- Sentence fragmentation: none

CONTENT MODE:
FORM_ONLY_HUMANIZATION

ELABORATION SCOPE:
NONE

OUTPUT MODE:
PUBLISH

ROUTE:
B_STANDARD_PAGE

Особые требования:
- Не добавляй характеристики, которых нет в исходных материалах.
- Не называй чайник «лучшим», «идеальным», «безопасным» или
  «энергоэффективным», если это не подтверждено в handoff.
- Сохрани модель, характеристики, комплектацию, гарантию, ограничения,
  условия использования и таблицы.
- В начале быстро покажи главный сценарий применимости товара.
- Рядом с характеристикой объясняй её практическое значение,
  только если это следует из подтверждённого материала.
- Не превращай карточку в обзор или сравнение с конкурентами.
- Сохрани CTA и обязательные проверки перед заказом.

GIST HUMANIZATION HANDOFF:
[вставить handoff]

TEXT TO HUMANIZE:
[вставить черновик карточки XYZ]
```

**Что стоит передать в GIST contract для карточки.**

```text
- Job to be done:
  Понять, подходит ли XYZ для конкретного сценария дома или офиса.
- Primary decision-relevant distinction:
  [например: модель рассчитана на быстрый нагрев большого объёма /
  на точную настройку температуры / на компактное использование]
- Mandatory selection criteria:
  Объём, мощность, материал, температурные режимы, габариты,
  тип нагревателя, способ очистки.
- Mandatory limitations:
  [например: не использовать при напряжении вне указанного диапазона;
  температурные режимы доступны только для определённых объёмов]
- Mandatory verification methods:
  Сверить характеристики, комплектацию, условия гарантии,
  совместимость с электросетью.
- Mandatory next action / CTA:
  Проверить наличие, выбрать вариант, добавить в корзину.
```

### 2. Обзор от лица редакции журнала

**Задача.** Подготовить независимый по тону редакционный обзор: показать, какой вопрос решает модель, какие trade-offs у неё есть, кому она подходит и кому — нет.

Ключевое правило: редакция не должна имитировать независимое тестирование, если фактическая база состоит только из материалов производителя, карточек конкурентов или desk research. В таком случае допустим голос редакции, но нужно сохранять прозрачный evidence status: «по заявленным характеристикам», «судя по документации», «в сравнении со спецификациями». 

```text
Используй TEXT HUMANIZATION by DrMax v1.6.1 — RUNTIME FINAL.

DOMAIN / NICHE:
Бытовая техника / электрочайники.

TARGET AUDIENCE:
Читатели журнала о технике, выбирающие чайник осознанно.

PAGE TYPE:
review.

LANGUAGE AND REGIONAL NORM:
Russian, Russia.

TARGET TONE:
Редакционный, аналитический, спокойный.

DESIRED AUTHOR VOICE:
Редакция журнала о бытовой технике.

VOICE PROFILE:
- Professional distance: medium
- Terminology density: medium
- Direct address: limited
- First person: editorial “we”
- Emotional intensity: restrained
- Figurative language: limited
- CTA directness: restrained
- Sentence complexity: mixed
- Authorial explicitness: framed
- Evidence visibility: explicit
- Narrative energy: calm
- Compression: balanced
- Sentence fragmentation: none

CONTENT MODE:
FORM_ONLY_HUMANIZATION

ELABORATION SCOPE:
NONE

OUTPUT MODE:
EDITORIAL_REVIEW

ROUTE:
C_HIGH_RISK

Особые требования:
- Пиши от лица редакции только там, где это соответствует источникам.
- Не создавай впечатление лабораторного или бытового теста,
  если в research pack нет подтверждённых тестовых данных.
- Чётко различай: спецификации производителя, результаты тестов,
  редакторскую интерпретацию и пользовательские данные.
- Сохрани trade-offs, ограничения, сценарии непригодности и
  способы проверки перед покупкой.
- Главный вывод дай рано, но не раньше обязательного контекста
  и важных safety-ограничений.
- Не используй рекламные формулы и безусловные рекомендации.

GIST HUMANIZATION HANDOFF:
[вставить полный handoff, источники и block contracts]

TEXT TO HUMANIZE:
[вставить черновик обзора]
```

**Рекомендуемая структура GIST-черновика для такого обзора:**

```text
Сценарий и главный вывод
→ ключевые характеристики и их значение
→ пригодность для конкретных пользователей
→ ограничения и trade-offs
→ доказательность: на чём основаны выводы
→ что проверить перед покупкой
```

### 3. Обзор как производитель

**Задача.** Подготовить брендовый обзор на сайте производителя: внятно объяснить устройство, сценарии применения, заявленные преимущества и ограничения эксплуатации без маскировки рекламы под независимую экспертизу.

Здесь допустимы брендовый голос и `editorial “we”`, если это действительно коммуникация производителя. Но нельзя приписывать бренду несуществующие испытания, отзывы клиентов, «лидерство на рынке» или превосходство над конкурентами без подтверждённой базы. 

```text
Используй TEXT HUMANIZATION by DrMax v1.6.1 — RUNTIME FINAL.

DOMAIN / NICHE:
Бытовая техника / электрочайники.

TARGET AUDIENCE:
Покупатели, изучающие чайник XYZ на сайте производителя.

PAGE TYPE:
product review / branded editorial page.

LANGUAGE AND REGIONAL NORM:
Russian, Russia.

TARGET TONE:
Профессиональный, уверенный, объясняющий.

DESIRED AUTHOR VOICE:
Команда производителя, объясняющая устройство и сценарии выбора.

VOICE PROFILE:
- Professional distance: medium
- Terminology density: medium
- Direct address: limited
- First person: editorial “we”
- Emotional intensity: moderate
- Figurative language: none
- CTA directness: practical
- Sentence complexity: mixed
- Authorial explicitness: framed
- Evidence visibility: visible
- Narrative energy: dynamic
- Compression: balanced
- Sentence fragmentation: none

CONTENT MODE:
CONTROLLED_ELABORATION

ELABORATION SCOPE:
EXPLICIT_ONLY

OUTPUT MODE:
PUBLISH

ROUTE:
B_STANDARD_PAGE

Особые требования:
- Используй «мы» только для действий и сведений, подтверждённых
  материалами производителя.
- Любое преимущество связывай с конкретной характеристикой или
  описанным механизмом из handoff.
- Не создавай видимость независимого обзора.
- Не заявляй «лучший», «уникальный», «революционный», «безопасный»
  или «подходит всем» без подтверждённой и допустимой формулировки.
- Не скрывай ограничения использования, условия гарантии,
  комплектацию и необходимость проверки характеристик.
- Допустимо яснее объяснить одобренные сценарии и механизмы,
  но не добавлять новые факты.
- Заканчивай практичным CTA: проверить характеристики, комплектацию,
  наличие или выбрать вариант.

GIST HUMANIZATION HANDOFF:
[вставить полный handoff]

TEXT TO HUMANIZE:
[вставить черновик брендового обзора]
```

**Какие элементы лучше зафиксировать как `LOCKED`.**

```text
LOCKED-CRITICAL:
- Напряжение, мощность, правила безопасной эксплуатации.
- Условия гарантии.
- Ограничения по уходу и очистке.
- Официальная комплектация.

LOCKED-CORE:
- Главный сценарий использования XYZ.
- Конкретные механизмы заявленных преимуществ.
- Выбор режима / температуры, если он влияет на покупку.
- Следующее действие пользователя.

LOCKED-STABLE:
- Название модели.
- Официальные технологии.
- Наименования режимов.
- Артикул, материалы, габариты.
```

### 4. Обзорщик-тестировщик в личном блоге

**Задача.** Сделать живой личный обзор с наблюдениями, сценариями и выводами тестировщика.

Это единственный из четырёх сценариев, в котором возможны `author “I”`, личные наблюдения и тестовые впечатления. Но они допустимы **только если переданы как одобренные фактические материалы**: журнал тестирования, реальные измерения, фотографии, заметки, видео, конкретный пользовательский опыт. Если таких материалов нет, настройте `First person: prohibited` и не называйте автора тестировщиком. 

```text
Используй TEXT HUMANIZATION by DrMax v1.6.1 — RUNTIME FINAL.

DOMAIN / NICHE:
Бытовая техника / электрочайники.

TARGET AUDIENCE:
Читатели личного блога, которые сравнивают модели перед покупкой.

PAGE TYPE:
personal test review.

LANGUAGE AND REGIONAL NORM:
Russian, Russia.

TARGET TONE:
Практический, наблюдательный, честный.

DESIRED AUTHOR VOICE:
Независимый обзорщик-тестировщик.

VOICE PROFILE:
- Professional distance: low
- Terminology density: medium
- Direct address: limited
- First person: author “I”
- Emotional intensity: moderate
- Figurative language: limited
- CTA directness: practical
- Sentence complexity: mixed
- Authorial explicitness: opinionated
- Evidence visibility: explicit
- Narrative energy: dynamic
- Compression: balanced
- Sentence fragmentation: limited

CONTENT MODE:
CONTROLLED_ELABORATION

ELABORATION SCOPE:
EXPLICIT_ONLY

OUTPUT MODE:
EDITORIAL_REVIEW

ROUTE:
C_HIGH_RISK

Особые требования:
- Используй первое лицо только для реальных тестовых наблюдений,
  переданных в research pack.
- Не выдумывай время кипячения, шум, удобство крышки, запах пластика,
  температуру корпуса, расход энергии, долговечность или личные эмоции.
- Отделяй измеренный факт от личного впечатления и от данных производителя.
- Не превращай единичный опыт в универсальную рекомендацию.
- Сохрани ограничения теста: условия сети, объём воды, длительность,
  метод измерения, число запусков и применимость результата.
- Для каждого итогового вывода сохраняй trade-off или условие применимости.
- Верни Editorial Review, если в черновике есть личные утверждения
  без источника в handoff.

GIST HUMANIZATION HANDOFF:
[полный handoff, включая approved test notes]

APPROVED TEST NOTES:
- Условия теста:
- Метод измерения:
- Количество повторов:
- Наблюдения автора:
- Измеренные показатели:
- Ограничения теста:
- Допустимые субъективные формулировки:

TEXT TO HUMANIZE:
[вставить черновик блога]
```

## Страница категории: электрочайники

Категория — это не набор карточек и не обзор одного товара. Её задача — помочь пользователю сузить выбор: понять, какой тип электрочайника нужен, какие фильтры важны, какие различия влияют на сценарий и что проверить на модели товара.

Для категории обычно подходит `B_STANDARD_PAGE`. Если в тексте есть безопасность, стандарты, сложные технические сравнения, медицинские утверждения о температуре или значимые энергопотребительские claims — используйте `C_HIGH_RISK`. 

```text
Используй TEXT HUMANIZATION by DrMax v1.6.1 — RUNTIME FINAL.

DOMAIN / NICHE:
Бытовая техника / электрочайники.

TARGET AUDIENCE:
Покупатели, выбирающие электрочайник и сравнивающие варианты.

PAGE TYPE:
category.

LANGUAGE AND REGIONAL NORM:
Russian, Russia.

TARGET TONE:
Практичный, объясняющий, навигационный.

DESIRED AUTHOR VOICE:
Экспертный гид интернет-магазина.

VOICE PROFILE:
- Professional distance: medium
- Terminology density: medium
- Direct address: limited
- First person: prohibited
- Emotional intensity: restrained
- Figurative language: none
- CTA directness: practical
- Sentence complexity: mixed
- Authorial explicitness: framed
- Evidence visibility: visible
- Narrative energy: calm
- Compression: dense
- Sentence fragmentation: none

CONTENT MODE:
FORM_ONLY_HUMANIZATION

ELABORATION SCOPE:
NONE

OUTPUT MODE:
PUBLISH

ROUTE:
B_STANDARD_PAGE

Особые требования:
- Сохрани архитектуру выбора:
  сценарий → объём → материал → режимы → уход → проверка → переход к товарам.
- Не превращай категорию в общий SEO-текст или скрытую рекламу.
- Не повторяй одинаковые преимущества в каждом абзаце.
- Объясняй только те различия, которые уже подтверждены в handoff.
- Не заявляй, что один материал или тип чайника «лучше» без сценария,
  условия и trade-off.
- Сохрани фильтры, ограничения, критерии и переход к релевантным товарам.
- Не редактируй названия фильтров, характеристик и таблиц,
  если они защищены contract.

GIST HUMANIZATION HANDOFF:
[вставить полный handoff]

TEXT TO HUMANIZE:
[вставить черновик страницы категории]
```

**Ключевые настройки semantic contract для категории:**

```text
- Job to be done:
  Быстро сузить выбор до подходящего типа электрочайника.

- Primary decision-relevant distinction:
  Выбор определяется сценарием использования, объёмом, материалом,
  температурными режимами и требованиями к уходу, а не только ценой.

- Mandatory selection criteria:
  Объём; мощность; материал корпуса; тип нагревателя; терморегулятор;
  фильтр; конструкция крышки; уход; гарантия.

- Mandatory limitations, exclusions, and failure modes:
  [Только подтверждённые ограничения из research pack.]

- Mandatory verification methods:
  Проверить характеристики выбранной модели, допустимое напряжение,
  объём, комплектацию и условия гарантии.

- Mandatory next action / CTA:
  Выбрать фильтры и перейти к карточкам подходящих моделей.
```

## Другие типичные сценарии

### 1. Услуга: ремонт квартиры

**Цель страницы.** Не «продать ремонт любой ценой», а помочь пользователю понять: подходит ли услуга, что входит в работы, от чего зависит смета, какие ограничения существуют и какой следующий шаг нужен для оценки.

```text
DOMAIN / NICHE: Ремонт квартир.
TARGET AUDIENCE: Владельцы квартир, планирующие ремонт.
PAGE TYPE: service landing page.
LANGUAGE AND REGIONAL NORM: Russian, Russia.
TARGET TONE: Практичный, прозрачный, профессиональный.
DESIRED AUTHOR VOICE: Руководитель ремонтной компании / эксперт по организации работ.

VOICE PROFILE:
- Professional distance: medium
- Terminology density: medium
- Direct address: limited
- First person: editorial “we”
- Emotional intensity: restrained
- Figurative language: none
- CTA directness: practical
- Sentence complexity: mixed
- Authorial explicitness: framed
- Evidence visibility: visible
- Narrative energy: calm
- Compression: balanced
- Sentence fragmentation: none

CONTENT MODE: CONTROLLED_ELABORATION
ELABORATION SCOPE: EXPLICIT_ONLY
OUTPUT MODE: EDITORIAL_REVIEW
ROUTE: C_HIGH_RISK

Особые требования:
- Не обещай точную цену, срок или результат без данных из сметы/договора.
- Не называй ремонт «под ключ» универсальным решением без определения состава работ.
- Сохрани этапы, исключения, допущения сметы, порядок согласований,
  требования к объекту и условия гарантии.
- Не выдумывай кейсы, отзывы, опыт бригад и результаты работ.
- В CTA предлагай действие, которое соответствует contract:
  замер, аудит объекта, расчёт, консультация.
```

**Критичные поля handoff:** тип ремонта; состав работ; порядок замера; что влияет на стоимость; что не включено; сроки и их условия; документы; гарантия; статус разрешений; действия клиента до старта.

### 2. Производство металлических визиток

**Цель страницы.** Объяснить варианты материала и обработки, подготовку макета, ограничения технологии, сроки, тираж, стоимость и оформление заказа.

```text
DOMAIN / NICHE: Изготовление металлических визиток.
TARGET AUDIENCE: Компании, дизайнеры, предприниматели, ищущие премиальную сувенирную продукцию.
PAGE TYPE: service / product landing page.
LANGUAGE AND REGIONAL NORM: Russian, Russia.
TARGET TONE: Точный, визуально-ориентированный, деловой.
DESIRED AUTHOR VOICE: Производственный консультант.

VOICE PROFILE:
- Professional distance: medium
- Terminology density: medium
- Direct address: limited
- First person: editorial “we”
- Emotional intensity: moderate
- Figurative language: limited
- CTA directness: practical
- Sentence complexity: mixed
- Authorial explicitness: framed
- Evidence visibility: visible
- Narrative energy: calm
- Compression: balanced
- Sentence fragmentation: none

CONTENT MODE: CONTROLLED_ELABORATION
ELABORATION SCOPE: EXPLICIT_ONLY
OUTPUT MODE: PUBLISH
ROUTE: B_STANDARD_PAGE

Особые требования:
- Не обещай точность цвета, срок, минимальный тираж или результат обработки,
  если это не подтверждено handoff.
- Сохрани различия материалов, толщин, покрытий и технологий нанесения.
- Рядом с преимуществом показывай технологическое условие или ограничение.
- Не скрывай требования к макету, ограничения на мелкий текст,
  особенности цветопередачи и согласование образца.
- CTA: загрузить макет, запросить расчёт, получить требования к файлу.
```

**Пример main distinction:**

```text
Металлическая визитка выбирается не только по внешнему эффекту:
материал, толщина, тип нанесения и требования к макету определяют,
можно ли реализовать конкретный дизайн без потери читаемости.
```

### 3. Сравнение SaaS-сервисов

**Цель страницы.** Помочь выбрать между системами по сценариям, ограничениям, интеграциям, цене владения и способу проверки до внедрения.

```text
DOMAIN / NICHE: SaaS / CRM.
TARGET AUDIENCE: Руководители продаж и операционные директора B2B-компаний.
PAGE TYPE: comparison.
LANGUAGE AND REGIONAL NORM: Russian, Russia.
TARGET TONE: Аналитический, нейтральный.
DESIRED AUTHOR VOICE: Независимый B2B-аналитик.

VOICE PROFILE:
- Professional distance: high
- Terminology density: high
- Direct address: limited
- First person: prohibited
- Emotional intensity: restrained
- Figurative language: none
- CTA directness: practical
- Sentence complexity: complex
- Authorial explicitness: neutral
- Evidence visibility: explicit
- Narrative energy: calm
- Compression: dense
- Sentence fragmentation: none

CONTENT MODE: FORM_ONLY_HUMANIZATION
ELABORATION SCOPE: NONE
OUTPUT MODE: EDITORIAL_REVIEW
ROUTE: C_HIGH_RISK

Особые требования:
- Не превращай сравнительную таблицу в рекламный текст.
- Не меняй порядок критериев, если он отражает decision logic.
- Сохрани источник каждой характеристики и дату актуальности.
- Не создавай вывод о «лучшем сервисе» без сценария и trade-off.
- Рядом с выводом сохраняй способ проверки:
  демо, тестовый импорт, проверка API, прав доступа и интеграций.
```

### 4. Информационный гайд: выбор ноутбука

**Цель страницы.** Сформировать понятный путь выбора без навязывания конкретной модели и без упрощения технических ограничений.

```text
DOMAIN / NICHE: Потребительская электроника / ноутбуки.
TARGET AUDIENCE: Пользователи, выбирающие ноутбук для работы, учёбы или дома.
PAGE TYPE: guide.
LANGUAGE AND REGIONAL NORM: Russian, Russia.
TARGET TONE: Объясняющий, спокойный, технически точный.
DESIRED AUTHOR VOICE: Независимый технический редактор.

VOICE PROFILE:
- Professional distance: medium
- Terminology density: medium
- Direct address: limited
- First person: prohibited
- Emotional intensity: restrained
- Figurative language: none
- CTA directness: practical
- Sentence complexity: mixed
- Authorial explicitness: framed
- Evidence visibility: visible
- Narrative energy: calm
- Compression: balanced
- Sentence fragmentation: none

CONTENT MODE: FORM_ONLY_HUMANIZATION
ELABORATION SCOPE: NONE
OUTPUT MODE: PUBLISH
ROUTE: B_STANDARD_PAGE

Особые требования:
- Сохрани порядок выбора:
  задача → программные требования → производительность → экран →
  автономность → порты → вес → проверка конфигурации.
- Не выдавай минимальные требования для одной программы
  за рекомендацию для всех задач.
- Не подменяй характеристики общей формулой «мощный ноутбук».
- Сохрани ограничения совместимости, конфигурации и возможности апгрейда.
```

### 5. FAQ: гарантийное обслуживание техники

**Цель страницы.** Быстро снять реальное препятствие пользователя: какие случаи покрывает гарантия, какие документы нужны, куда обращаться и какие есть исключения.

```text
DOMAIN / NICHE: Гарантийное обслуживание бытовой техники.
TARGET AUDIENCE: Владельцы техники, которым нужна сервисная помощь.
PAGE TYPE: FAQ.
LANGUAGE AND REGIONAL NORM: Russian, Russia.
TARGET TONE: Спокойный, точный, сервисный.
DESIRED AUTHOR VOICE: Служба поддержки производителя или магазина.

VOICE PROFILE:
- Professional distance: medium
- Terminology density: low
- Direct address: active
- First person: editorial “we”
- Emotional intensity: restrained
- Figurative language: none
- CTA directness: practical
- Sentence complexity: simple
- Authorial explicitness: neutral
- Evidence visibility: explicit
- Narrative energy: calm
- Compression: dense
- Sentence fragmentation: none

CONTENT MODE: FORM_ONLY_HUMANIZATION
ELABORATION SCOPE: NONE
OUTPUT MODE: PUBLISH
ROUTE: C_HIGH_RISK

Особые требования:
- Не сокращай формулировки, которые влияют на юридический смысл.
- Не превращай исключение из гарантии в скрытую рекомендацию.
- Для каждого ответа сохрани: условие → что происходит →
  требуемый документ/проверка → действие пользователя.
- Не добавляй сроки, основания отказа или условия сервиса,
  если их нет в официальных правилах.
```

### 6. Исследовательская статья: результаты опроса клиентов

**Цель страницы.** Представить результаты исследования без преувеличения выводов и без превращения корреляций в причинность.

```text
DOMAIN / NICHE: Исследование клиентского опыта.
TARGET AUDIENCE: Руководители маркетинга и продукта.
PAGE TYPE: research article.
LANGUAGE AND REGIONAL NORM: Russian, Russia.
TARGET TONE: Исследовательский, сдержанный, ясный.
DESIRED AUTHOR VOICE: Редакция исследовательского центра.

VOICE PROFILE:
- Professional distance: high
- Terminology density: high
- Direct address: no
- First person: editorial “we”
- Emotional intensity: restrained
- Figurative language: none
- CTA directness: restrained
- Sentence complexity: complex
- Authorial explicitness: neutral
- Evidence visibility: explicit
- Narrative energy: calm
- Compression: dense
- Sentence fragmentation: none

CONTENT MODE: FORM_ONLY_HUMANIZATION
ELABORATION SCOPE: NONE
OUTPUT MODE: EDITORIAL_REVIEW
ROUTE: C_HIGH_RISK

Особые требования:
- Сохрани методологию, размер и состав выборки, период сбора данных,
  формулировки вопросов и ограничения переноса результатов.
- Разделяй наблюдение, интерпретацию, гипотезу и рекомендацию.
- Не делай причинный вывод из корреляции.
- Не скрывай статистические и контекстные ограничения ради более сильного заголовка.
```

### 7. Ресторан или локальный сервис: страница меню/предложения

**Цель страницы.** Понятно описать предложение, состав, условия заказа, ограничения и следующий шаг без несуществующих эмоциональных гарантий.

```text
DOMAIN / NICHE: Ресторан / доставка еды.
TARGET AUDIENCE: Пользователи, выбирающие блюдо или оформление заказа.
PAGE TYPE: menu category / service page.
LANGUAGE AND REGIONAL NORM: Russian, Russia.
TARGET TONE: Аппетитный, но точный и спокойный.
DESIRED AUTHOR VOICE: Команда ресторана.

VOICE PROFILE:
- Professional distance: low
- Terminology density: low
- Direct address: limited
- First person: editorial “we”
- Emotional intensity: moderate
- Figurative language: limited
- CTA directness: active
- Sentence complexity: simple
- Authorial explicitness: framed
- Evidence visibility: visible
- Narrative energy: dynamic
- Compression: dense
- Sentence fragmentation: limited

CONTENT MODE: CONTROLLED_ELABORATION
ELABORATION SCOPE: EXPLICIT_ONLY
OUTPUT MODE: PUBLISH
ROUTE: B_STANDARD_PAGE

Особые требования:
- Сохрани состав, вес, аллергены, остроту, доступность,
  зоны доставки и условия заказа.
- Не добавляй вкусовые обещания, ингредиенты или происхождение,
  которых нет в исходных данных.
- Не скрывай ограничения по времени, минимальной сумме и доступности.
```

Во всех этих сценариях основная настройка зависит не от «красоты голоса», а от трёх вопросов: **кто говорит**, **на каких данных он имеет право говорить** и **какое решение должен принять читатель**. Если голос требует личного опыта, независимой экспертизы или точного обещания, а GIST research pack этого не подтверждает, нужно либо изменить voice profile, либо оставить вопрос в `EDITORIAL_REVIEW`, а не компенсировать пробел стилистикой.  