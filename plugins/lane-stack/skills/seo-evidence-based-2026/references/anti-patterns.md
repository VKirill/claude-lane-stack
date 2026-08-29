# Anti-patterns

*Source: book: Доказательное SEO 2026 — Максим Храповицкий / DrMax (Telegram @DrMaxSEO)*

## ❌ Disallow for Noindex

**Why wrong:** Google не увидит тег noindex, если сканирование запрещено, и страница останется в индексе с флагом isRoboted.

**Fix:** Оставить страницу открытой для сканирования, но добавить мета-тег noindex.

## ❌ Keyword Stuffing in Titles

**Why wrong:** Триггерит штраф dupTokens и снижает семантическую когерентность (goldmineBlockbertFactor).

**Fix:** Писать естественно звучащие заголовки, ориентированные на клик (goodClick).

## ❌ Template Boilerplate Overload

**Why wrong:** Повышает clutterScore и снижает OriginalContentScore из-за повторяющихся блоков.

**Fix:** Минимизировать шаблонный текст, делая упор на уникальные данные в каждом CompositeDoc.

## ❌ Dead Link Building

**Why wrong:** Покупка ссылок на страницах с нулевым трафиком не активирует NavBoost и PageRank-NearestSeeds.

**Fix:** Выбирайте доноров с живым трафиком или 'разогревайте' страницу-донор внешними сигналами.

## ❌ Disconnected Entity

**Why wrong:** Анонимный контент в YMYL-темах получает unauthoritativeScore и Lowest рейтинг от асессоров.

**Fix:** Создайте детальные страницы авторов с Person Schema, ссылками на LinkedIn и внешние публикации.

## ❌ Typicality Bias Content

**Why wrong:** Стандартная AI-генерация создает 'типичный' контент с низким Information Gain, который игнорируется AI Overviews.

**Fix:** Используйте метод 'Киборга' для внедрения в текст уникальной 'наземной правды' (Ground Truth).

## ❌ Marketing Fluff (Water)

**Why wrong:** Размывает Entity Salience и midCount, сигнализируя о низком качестве контента (pandaDemotion).

**Fix:** Использовать жесткий стилевой режим P1 с запретом на эпитеты и оценочные суждения.

## ❌ Semantic Leakage

**Why wrong:** Перекрестные ссылки между неродственными кластерами снижают siteFocusScore.

**Fix:** Соблюдать матриархальную систему: связи между коконами только через Target-страницы.

## ❌ Orphan Support Pages

**Why wrong:** Страницы без 'материнской' ссылки не передают LinkValue и выпадают из тематического графа.

**Fix:** Каждая Support Page обязана иметь 1 Mother-ссылку на свой Mixed-узел.

## ❌ Inference Drift

**Why wrong:** Использование анкоров, конфликтующих с канонической ролью сайта в SCDL.

**Fix:** Проводить аудит инференс-нагрузки перед простановкой внешних ссылок.

## ❌ Generic Prompting

**Why wrong:** Отсутствие роли и ограничений ведет к размытию интента и росту GibberishScore.

**Fix:** Использовать Prompt-as-Code с четкой схемой input/output и системными инструкциями.

## ❌ Blind Competitor Anchor Copying

**Why wrong:** Слепое копирование анкорного профиля конкурента может привести к наследованию его Penguin-рисков.

**Fix:** Проводить аудит анкорного профиля на манипулятивные паттерны перед формированием своей стратегии.

## ❌ Ignoring Dwell Time in Content Audit

**Why wrong:** Оценка качества контента без учета Dwell Time игнорирует ключевой сигнал NavBoost.

**Fix:** Анализировать Bounce Rate и Dwell Time в связке с типом интента страницы (educational vs transactional).
