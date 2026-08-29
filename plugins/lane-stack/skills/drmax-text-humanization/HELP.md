Ниже — справочная система по **TEXT HUMANIZATION by DrMax v1.6.1 — RUNTIME FINAL**: режимы, маршруты, входные переменные, их значения и рабочие шаблоны. Скилл предназначен для контролируемой редактуры: он улучшает подачу утверждённого содержания, но не заменяет GIST-анализ, исследование, фактчекинг или предметную экспертизу.

## 1. Принцип работы

Скилл работает поверх GIST-черновика и его semantic contract. До редактуры он внутренне выделяет защищённые элементы: главный ответ, критерии, условия, ограничения, доказательность, проверки, метрики и обязательные действия; затем редактирует лексику, синтаксис, ритм, структуру и voice profile; в конце сверяет результат с исходным смыслом через semantic diff и Publish Gate.

Базовый pipeline:

```text
Исследование / first-party data
→ GIST Content Logic
→ GIST Humanization Handoff + draft
→ TEXT HUMANIZATION v1.6.1
→ semantic diff + repair pass при необходимости
→ PUBLISH или EDITORIAL_REVIEW
```

Приоритеты неизменны: сначала фактическая точность и доказательность, затем semantic contract и decision functions, после — ограничения и безопасность, а уже потом ясность, ритм и стилистическая выразительность.

## 2. Режимы работы

### Content mode

`CONTENT MODE` определяет, может ли скилл только редактировать форму или в ограниченных случаях разворачивать уже одобренный смысл.


| Значение | Что делает | Что запрещено |
| :-- | :-- | :-- |
| `FORM_ONLY_HUMANIZATION` | Редактирует язык, синтаксис, ритм, связки, порядок абзацев внутри сохранённой архитектуры; может яснее сформулировать уже существующую связь или механизм | Любые новые факты, примеры, кейсы, механизмы, результаты, источники, обещания и внешнее знание |
| `CONTROLLED_ELABORATION` | Разрешает ограниченное смысловое разворачивание, но только в пределах `ELABORATION SCOPE` | Нельзя менять evidence status, добавлять внешнюю фактуру или новую причинно-следственную связь |

Если `FORM_ONLY_HUMANIZATION` конфликтует с настройкой elaboration, действует более строгий режим: `ELABORATION SCOPE = NONE`.

**Пример: только редактура формы**

```text
CONTENT MODE: FORM_ONLY_HUMANIZATION
ELABORATION SCOPE: NONE

Задача:
Убери канцелярит и повторы. Сохрани все факты, цифры,
условия применимости и порядок аргументации.
```

**Пример: допустимое контролируемое пояснение**

```text
CONTENT MODE: CONTROLLED_ELABORATION
ELABORATION SCOPE: EXPLICIT_PLUS_LOGICAL

Разрешается яснее сформулировать прямое следствие уже указанного
условия. Не добавляй новых фактов, примеров, данных и причин.
```


### Elaboration scope

`ELABORATION SCOPE` определяет пределы допустимого разворачивания материала.


| Значение | Практический смысл |
| :-- | :-- |
| `NONE` | Только редактура формы; ничего смыслово не добавлять |
| `EXPLICIT_ONLY` | Разворачивать лишь факты, примеры, сценарии, механизмы и ограничения, которые прямо разрешены в handoff |
| `EXPLICIT_PLUS_LOGICAL` | Дополнительно делать явным прямое логическое следствие уже данного claim, условия или механизма, если это не создаёт новый factual claim |

Например, из фразы «размер зависит от объёма слоя под изделием» допустимо сделать более ясный вывод «перед покупкой стоит сверить замеры с учётом базового слоя», если сама проверка уже задана в черновике или handoff. Недопустимо добавлять новый размерный совет, которого в исходном материале нет.

### Output mode

`OUTPUT MODE` задаёт формат ответа скилла.


| Значение | Когда использовать | Что вернёт скилл |
| :-- | :-- | :-- |
| `PUBLISH` | Черновик достаточен, риски понятны, нужен готовый текст | Только финальный текст без пояснений |
| `EDITORIAL_REVIEW` | Есть неполные вводные, конфликт, риск смыслового дрейфа или требуется контроль редактора | Отчёт о сохранности GIST-логики, список изменений, semantic risks, open issues и обработанный текст |
| `DIAGNOSTIC` | Нужно проверить текст, а не обязательно переписать его | Диагностику контекста, маршрута, protection map, блоков, рисков и нерешённых вопросов; текст — только при прямом запросе на редактуру |

`PUBLISH` запрещён, если критический или core-элемент был потерян, ослаблен, расширен, усилен, перенесён слишком далеко от claim либо лишён decision function. При такой проблеме скилл делает один целевой Repair Pass; если нарушение не устранено, переключается на `EDITORIAL_REVIEW`.

**Пример: готовый текст**

```text
OUTPUT MODE: PUBLISH

Верни только финальную версию текста.
Не добавляй отчёт, комментарии и объяснение изменений.
```

**Пример: редакторская проверка**

```text
OUTPUT MODE: EDITORIAL_REVIEW

Сначала покажи:
1. Какие GIST-элементы защищены.
2. Какие риски есть в исходном тексте.
3. Какие изменения внесены.
4. Какие данные нужно уточнить.
После этого выведи обработанный текст.
```


### Route

`ROUTE` определяет глубину и строгость обработки.


| Route | Назначение | Когда выбирать |
| :-- | :-- | :-- |
| `A_QUICK_BLOCK` | Быстрая контролируемая редактура короткого блока | Карточка, FAQ-ответ, email-блок, абзац, обычно до 300 слов |
| `B_STANDARD_PAGE` | Стандартная полная редактура | Статья, лендинг, гайд, категория, описание продукта обычного риска |
| `C_HIGH_RISK` | Расширенная проверка сложного или чувствительного контента | Медицинская, юридическая, финансовая, исследовательская, техническая, B2B-тематика, сложные сравнения |
| `D_DIAGNOSTIC` | Проверка без обязательного переписывания | Аудит логики, рисков, genericity, терминов и сохранности |
| `AUTO` | Автовыбор маршрута | Используйте по умолчанию, если риск и формат не определены заранее |

В `AUTO` скилл выбирает `B_STANDARD_PAGE` по умолчанию и повышает маршрут до `C_HIGH_RISK`, если видит исследования, числа, пороги, доказательные claims, ограничения, регулируемую тему, сложное сравнение или высокую цену ошибки. Для `C_HIGH_RISK` обязательны полный handoff и block contracts.

**Пример: короткий FAQ**

```text
ROUTE: A_QUICK_BLOCK
CONTENT MODE: FORM_ONLY_HUMANIZATION
OUTPUT MODE: PUBLISH

Задача: отредактируй ответ FAQ, сохрани обязательное действие
и исключение из правила.
```

**Пример: технический гайд**

```text
ROUTE: C_HIGH_RISK
CONTENT MODE: FORM_ONLY_HUMANIZATION
OUTPUT MODE: EDITORIAL_REVIEW

Это технический B2B-гайд. Сохрани названия API, пороги,
условия интеграции, ограничения и порядок проверки.
```


## 3. Контекстные переменные

Эти поля объясняют, **для кого, где и в каком регистре** редактируется текст.


| Переменная | Что задаёт | Пример настройки |
| :-- | :-- | :-- |
| `DOMAIN / NICHE` | Нишу и предметную область | `e-commerce / outdoor clothing` |
| `TARGET AUDIENCE` | Уровень знаний, роль и потребность читателя | `Покупатели, выбирающие первый туристический рюкзак` |
| `PAGE TYPE` | Формат и функцию страницы | `guide`, `comparison`, `category`, `FAQ`, `B2B`, `research` |
| `LANGUAGE AND REGIONAL NORM` | Язык и региональные нормы | `Russian, Russia`; `English, US` |
| `TARGET TONE` | Общую коммуникативную манеру | `analytical`, `instructional`, `technical`, `editorial` |
| `DESIRED AUTHOR VOICE` | Тип авторского голоса | `сдержанный эксперт`; `практический консультант`; `технический аналитик` |

**Пример заполнения**

```text
DOMAIN / NICHE: SaaS для отделов продаж
TARGET AUDIENCE: Руководители продаж в B2B-компаниях
PAGE TYPE: comparison
LANGUAGE AND REGIONAL NORM: Russian, Russia
TARGET TONE: analytical
DESIRED AUTHOR VOICE: практический B2B-консультант
```

Эти переменные не дают скиллу права менять факты или доказательность. Они только определяют допустимый уровень терминологии, плотность объяснений, дистанцию автора, синтаксис и степень прямого обращения к читателю.

## 4. Voice profile

`VOICE PROFILE` превращает общее описание тона в конкретные параметры редакторского решения.


| Параметр | Значения | Что меняет |
| :-- | :-- | :-- |
| `Professional distance` | `low / medium / high` | Дистанцию автора от читателя и допустимую неформальность |
| `Terminology density` | `low / medium / high` | Количество специальных терминов и глубину их расшифровки |
| `Direct address` | `no / limited / active` | Допустимость обращений «вы», «ваш», прямых рекомендаций |
| `First person` | `prohibited / editorial “we” / author “I”` | Можно ли использовать «мы» или «я» |
| `Emotional intensity` | `restrained / moderate / expressive` | Сдержанность или динамичность подачи |
| `Figurative language` | `none / limited / moderate` | Допустимость метафор и образов |
| `CTA directness` | `restrained / practical / active` | Напрямую ли призывать к следующему действию |
| `Sentence complexity` | `simple / mixed / complex` | Среднюю сложность фраз и плотность условий |
| `Authorial explicitness` | `neutral / framed / opinionated` | Допустимость редакторского вывода и оценочного суждения |
| `Evidence visibility` | `implicit / visible / explicit` | Насколько заметно показывать источник, контекст и статус доказательности |
| `Narrative energy` | `calm / dynamic / assertive` | Темп и напор изложения |
| `Compression` | `dense / balanced / expansive` | Насколько сжимать материал |
| `Sentence fragmentation` | `none / limited / expressive` | Допустимость неполных фраз и фрагментов |

**Конфигурация для юридической статьи**

```text
VOICE PROFILE:
- Professional distance: high
- Terminology density: high
- Direct address: no
- First person: prohibited
- Emotional intensity: restrained
- Figurative language: none
- CTA directness: restrained
- Sentence complexity: complex
- Authorial explicitness: neutral
- Evidence visibility: explicit
- Narrative energy: calm
- Compression: dense
- Sentence fragmentation: none
```

**Конфигурация для практического гида**

```text
VOICE PROFILE:
- Professional distance: medium
- Terminology density: medium
- Direct address: limited
- First person: prohibited
- Emotional intensity: moderate
- Figurative language: limited
- CTA directness: practical
- Sentence complexity: mixed
- Authorial explicitness: framed
- Evidence visibility: visible
- Narrative energy: dynamic
- Compression: balanced
- Sentence fragmentation: limited
```

Explicit authorial judgment допустим только при одновременном выполнении четырёх условий: он разрешён voice profile, подтверждён источником, не меняет evidence status и сохраняет видимым limitation или trade-off. Вымышленный личный опыт запрещён независимо от выбранного голоса.

## 5. Semantic contract

Это главный блок защиты смысла. Он задаёт, что нельзя потерять во время редакторской обработки.


| Поле | Для чего нужно | Пример |
| :-- | :-- | :-- |
| `Job to be done` | Какую практическую задачу решает пользователь | `Выбрать рюкзак для похода выходного дня` |
| `Topic core` | Центральная тема материала | `Выбор объёма и посадки туристического рюкзака` |
| `Primary decision-relevant distinction` | Ключевое различие, от которого зависит решение | `Объём рюкзака выбирают по длительности и составу снаряжения, а не по росту` |
| `Main answer` | Основной ответ, если это FAQ, гайд или исследование | `Для похода на 1–2 дня обычно нужен рюкзак 20–35 л, если этого достаточно для снаряжения` |
| `Decision map` | Последовательность принятия решения | `Сценарий → объём → посадка → совместимость → проверка` |
| `Mandatory selection criteria` | Обязательные критерии выбора | `объём, длина спины, нагрузка, совместимость с гидратором` |
| `Mandatory limitations, exclusions, failure modes` | Условия, когда правило не работает | `Не использовать рекомендацию для зимнего автономного похода` |
| `Mandatory verification methods` | Что читатель должен проверить | `Сверить длину спины и примерить рюкзак с нагрузкой` |
| `Mandatory metrics` | Цифры, которые нужны пользователю | `объём в литрах, грузоподъёмность` |
| `Mandatory next action / CTA` | Следующий обязательный шаг | `Сравнить замеры и примерить рюкзак` |
| `Facts… that must remain unchanged` | Защищённые факты, числа, имена и термины | `20–35 л; название модели; длина спины 48 см` |
| `Claims and evidence status` | Степень подтверждённости каждого утверждения | `first-party measurement`; `research finding`; `interpretation` |
| `Research context` | Контекст исследования или замера | `Тест проводился при нагрузке 8 кг` |
| `Transfer limitations` | Границы переноса вывода | `Результат нельзя переносить на рюкзаки с другой подвеской` |
| `Terms that must not be simplified` | Термины, которые нельзя заменять случайными синонимами | `торс; поясной ремень; load lifters` |
| `Elements that may be compressed/reordered` | Материал, с которым можно работать свободнее | `историческая справка; второстепенный пример` |
| `Allowed factual material…` | Единственный разрешённый источник для добавочного пояснения | `описание механизма из документации производителя` |

**Пример краткого semantic contract**

```text
GLOBAL GIST CONTRACT:
- Job to be done: помочь выбрать размер куртки для походов
- Topic core: посадка мембранной куртки
- Primary decision-relevant distinction:
  Размер зависит от слоя одежды под курткой
- Mandatory selection criteria:
  Обхват груди, длина рукава, предполагаемый базовый слой
- Mandatory limitations, exclusions, and failure modes:
  Таблица не заменяет примерку при нестандартной фигуре
- Mandatory verification methods:
  Сверить замеры изделия, а не только маркировку размера
- Mandatory next action / CTA:
  Открыть таблицу замеров и сопоставить с одеждой пользователя
- Facts…:
  Не менять названия размеров, сантиметры и условия измерения
```


## 6. Metrics и терминология

### Metric visibility

`METRIC VISIBILITY` отделяет полезные читателю метрики от технических показателей внутреннего процесса.


| Поле | Назначение | Пример |
| :-- | :-- | :-- |
| `User-facing metrics` | Должны остаться в тексте | `вес, цена, срок, объём, процент, порог` |
| `Internal measurement only` | Используются внутри процесса, но не публикуются | `внутренний quality score` |
| `Metrics prohibited in user-facing copy` | Нельзя выводить читателю | `служебный рейтинг риска; внутренний KPI` |

```text
METRIC VISIBILITY:
- User-facing metrics: вес 1,2 кг; объём 30 л
- Internal measurement only: редакторский quality score
- Metrics prohibited in user-facing copy: внутренний рейтинг товарной группы
```


### Protected terminology policy

Этот блок фиксирует, как скилл обращается с терминами.


| Поле | Назначение | Пример |
| :-- | :-- | :-- |
| `Terms to preserve` | Не заменять и не упрощать | `SLA`, `API`, `CAC`, `конверсия` |
| `Terms to translate` | Переводить по установленному правилу | `customer journey → путь клиента` |
| `Terms requiring first-use explanation` | Раскрыть при первом упоминании | `retention — удержание клиентов` |
| `Forbidden substitutions` | Не использовать вместо точного термина | `платформа → сервис`, если речь именно о платформе |
| `Official names and abbreviations` | Сохранять буквально | `Google Analytics 4`, `ISO 27001`, `REST API` |

```text
PROTECTED TERMINOLOGY POLICY:
- Terms to preserve: UTM-метка, attribution window
- Terms to translate: customer journey → путь клиента
- Terms requiring first-use explanation: ROAS
- Forbidden substitutions: «окупаемость рекламы» вместо ROAS
- Official names and abbreviations: Google Ads, GA4
```

Скилл трактует терминологический дрейф как отдельный semantic risk. Защищённые названия, API, формулы, код, единицы измерения и официальные сокращения нельзя менять «для более живого стиля».

## 7. Block contracts

`BLOCK CONTRACTS` нужны для значимых блоков: тех, где есть критерий, ограничение, доказательство, сравнение, метрика, CTA, условие, verification либо элемент `LOCKED-CRITICAL`/`LOCKED-CORE`.


| Поле | Значение |
| :-- | :-- |
| `Block ID` | Уникальный идентификатор блока, например `SIZE-02` |
| `Protection level` | Уровень защиты: `LOCKED-CRITICAL`, `LOCKED-CORE`, `LOCKED-STABLE`, `REFORMULABLE`, `OPTIONAL` |
| `Presence status` | Статус присутствия: `PRESENT`, `ABSENT_BY_DESIGN`, `MISSING_FROM_DRAFT`, `UNKNOWN`, `CONFLICTING` |
| `Source anchor` | Где именно находится исходный смысл: заголовок, таблица, абзац, handoff |
| `Original fragment` | Исходная формулировка, особенно для critical-блоков |
| `Block type` | Тип: criterion, limitation, comparison, CTA, evidence, instruction и т. д. |
| `User uncertainty` | Какой вопрос читателя снимает блок |
| `Decision function` | Какую роль блок играет в выборе или действии |
| `Claim` | Что именно утверждается |
| `Evidence status` | Факт, интерпретация, гипотеза, first-party measurement и т. д. |
| `Required condition` | При каком условии claim применим |
| `Limitation` | Где claim не действует или требует осторожности |
| `Verification` | Как читатель может проверить применимость |
| `Allowed transformations` | Что можно менять в форме |
| `Forbidden transformations` | Что менять нельзя |

**Пример block contract**

```text
BLOCK ID: SIZE-02
PROTECTION LEVEL: LOCKED-CORE
PRESENCE STATUS: PRESENT
SOURCE ANCHOR: H2 «Как выбрать размер», абзац 2
ORIGINAL FRAGMENT:
«При ношении поверх базового слоя выбирайте размер по замерам изделия».

BLOCK TYPE: selection criterion
USER UNCERTAINTY:
Подойдёт ли куртка для ношения поверх флиса?

DECISION FUNCTION:
Не допустить ошибку выбора размера до покупки.

CLAIM:
Посадка зависит от объёма слоя под курткой.

EVIDENCE STATUS:
First-party measurement.

REQUIRED CONDITION:
Куртку планируют носить поверх базового или утепляющего слоя.

LIMITATION:
Правило не переносится на свободную городскую посадку.

VERIFICATION:
Сверить замеры изделия с таблицей.

ALLOWED TRANSFORMATIONS:
Упростить синтаксис, сделать порядок проверки заметнее.

FORBIDDEN TRANSFORMATIONS:
Убрать сверку замеров; превратить правило в универсальный совет.
```


## 8. Protection levels и статусы

### Protection levels

| Уровень | Что можно делать |
| :-- | :-- |
| `LOCKED-CRITICAL` | Нельзя удалить, ослабить, расширить, усилить, исказить или небезопасно перенести |
| `LOCKED-CORE` | Нельзя удалить, заменить общим текстом или лишить decision function |
| `LOCKED-STABLE` | Допустима только точная компактная переформулировка без искажения факта |
| `REFORMULABLE` | Можно редактировать, сокращать и переставлять при сохранении смысла, условий и доказательности |
| `OPTIONAL` | Можно убрать или объединить, если не теряется decision value |

К `LOCKED-CRITICAL` обычно относятся safety/legal/medical/financial limitations, evidence status, числа, даты, пороги, дозировки, обязательные условия и проверки. К `LOCKED-CORE` — Job to be Done, главный ответ, ключевой критерий, filter, comparison logic, CTA, архитектура решения и значимый механизм.

### Presence status

| Статус | Как понимать |
| :-- | :-- |
| `PRESENT` | Элемент есть в черновике и имеет anchor |
| `ABSENT_BY_DESIGN` | Элемент намеренно не выводится читателю, например внутренняя метрика |
| `MISSING_FROM_DRAFT` | Элемент требуется по handoff, но отсутствует в черновике |
| `UNKNOWN` | Нельзя безопасно определить смысл, обязательность или источник |
| `CONFLICTING` | Требования или исходные блоки противоречат друг другу |

`UNKNOWN`, `MISSING_FROM_DRAFT` и `CONFLICTING` — не разрешение на свободную интерпретацию. Если такой элемент важен для решения, результат должен перейти в `EDITORIAL_REVIEW`, а не маскировать проблему гладким текстом.

## 9. Handoff: минимальный и полный

### Минимальный handoff

Допустим для короткого низкорискового текста, если в нём нет исследовательских claims, значимых чисел, сложных фильтров, регулируемой тематики, материальных ограничений и рекомендаций с высокой ценой ошибки.

```text
DOMAIN / NICHE: онлайн-образование
TARGET AUDIENCE: начинающие маркетологи
PAGE TYPE: FAQ
TARGET TONE: practical
CONTENT MODE: FORM_ONLY_HUMANIZATION
OUTPUT MODE: PUBLISH
ROUTE: A_QUICK_BLOCK

Ключевой факт:
Доступ к записи вебинара открывается на 30 дней.

Текст:
[вставить FAQ-ответ]
```


### Полный handoff

Нужен для исследований, технических и B2B-текстов, сравнений, медицины, права, финансов, регулируемых тем, материалов с цифрами, порогами, датами, условиями, совместимостью, несколькими сценариями и transfer limitations.

```text
DOMAIN / NICHE: CRM для отдела продаж
TARGET AUDIENCE: коммерческие директора B2B-компаний
PAGE TYPE: comparison
LANGUAGE AND REGIONAL NORM: Russian, Russia
TARGET TONE: analytical
DESIRED AUTHOR VOICE: технический B2B-консультант

CONTENT MODE: FORM_ONLY_HUMANIZATION
ELABORATION SCOPE: NONE
OUTPUT MODE: EDITORIAL_REVIEW
ROUTE: C_HIGH_RISK

GLOBAL GIST CONTRACT:
- Job to be done: выбрать CRM для отдела из 15 менеджеров
- Topic core: сравнение CRM по интеграциям и контролю воронки
- Primary decision-relevant distinction:
  Подходящая CRM определяется не числом функций, а совместимостью
  с процессом продаж и источниками данных
- Mandatory selection criteria:
  интеграции, права доступа, настройка воронки, экспорт данных
- Mandatory limitations:
  Нельзя переносить оценку на компании с нестандартной системой учёта
- Mandatory verification methods:
  Проверить API, права ролей и тестовый импорт данных
- Claims and evidence status:
  Сравнение основано на документации вендоров
- Terms that must not be simplified:
  API, webhook, SSO, role-based access control

TEXT TO HUMANIZE:
[вставить черновик]
```


## 10. Специальные правила формата

Скилл отдельно защищает таблицы, списки, формулы, код, цитаты и источники. Он не меняет числа, единицы, пороги, формулы, переменные, API names, названия продуктов, строки таблиц с ограничениями и смысл источника.

### Таблица

```text
Не меняй значения в таблице и не объединяй строки,
если исчезает важное различие. Сохрани порядок критериев,
так как он отражает decision logic.
```


### Код или формула

```text
Код, переменные, API-методы и формулы не редактируй.
Можно улучшить только поясняющий текст до и после блока.
```


### Цитата или исследование

```text
Сохрани степень уверенности исходного вывода.
Не превращай корреляцию в причинность и не убирай
ограничение переноса результата.
```


## 11. Длинные документы

Для материалов длиннее примерно 3 000 слов применяется long-document protocol:

1. Создать единый semantic contract для всего документа.
2. Зафиксировать общий voice profile.
3. Вести единый словарь терминов и protected formulations.
4. Дать глобальные anchors всем critical/core-блокам.
5. Редактировать логическими секциями, не меняя architectural order.
6. Проверить согласованность терминов между секциями.
7. Проверить единство голоса между секциями.
8. Собрать документ и выполнить общий semantic diff.
9. Проверить genericity и replaceability на уровне всего текста.
10. Разрешить не более одного document-level Repair Pass.
11. При неустранённом межсекционном конфликте вернуть `EDITORIAL_REVIEW`.

**Шаблон**

```text
Это документ на 5 200 слов.

Используй:
ROUTE: C_HIGH_RISK
OUTPUT MODE: EDITORIAL_REVIEW
CONTENT MODE: FORM_ONLY_HUMANIZATION

Сначала создай единый semantic contract и словарь терминов.
Затем обработай разделы без изменения порядка решения.
После сборки проверь противоречия между разделами, терминологию,
voice consistency и сохранность всех LOCKED-элементов.
```


## 12. Универсальный шаблон запуска

```text
Используй TEXT HUMANIZATION by DrMax v1.6.1 — RUNTIME FINAL.

DOMAIN / NICHE:
[ниша]

TARGET AUDIENCE:
[аудитория]

PAGE TYPE:
[guide / category / product / comparison / FAQ / B2B / research]

LANGUAGE AND REGIONAL NORM:
[язык и регион]

TARGET TONE:
[analytical / instructional / editorial / technical / persuasive]

DESIRED AUTHOR VOICE:
[описание голоса]

VOICE PROFILE:
- Professional distance:
- Terminology density:
- Direct address:
- First person:
- Emotional intensity:
- Figurative language:
- CTA directness:
- Sentence complexity:
- Authorial explicitness:
- Evidence visibility:
- Narrative energy:
- Compression:
- Sentence fragmentation:

CONTENT MODE:
[FORM_ONLY_HUMANIZATION / CONTROLLED_ELABORATION]

ELABORATION SCOPE:
[NONE / EXPLICIT_ONLY / EXPLICIT_PLUS_LOGICAL]

OUTPUT MODE:
[PUBLISH / EDITORIAL_REVIEW / DIAGNOSTIC]

ROUTE:
[AUTO / A_QUICK_BLOCK / B_STANDARD_PAGE / C_HIGH_RISK / D_DIAGNOSTIC]

GLOBAL GIST CONTRACT:
[минимальный или полный handoff]

PROTECTED TERMINOLOGY POLICY:
[если есть значимые термины]

BLOCK CONTRACTS:
[обязательно для C_HIGH_RISK; для других маршрутов — для значимых блоков]

TEXT TO HUMANIZE:
[черновик]
```

Главное правило: чем выше риск ошибки, доказательная нагрузка, техническая сложность или цена неверного решения, тем полнее должен быть handoff и тем уместнее `C_HIGH_RISK` вместе с `EDITORIAL_REVIEW`.

