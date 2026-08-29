# Semantic LinkValue & Topical Authority Mapping

*Book section: Часть 5 / Глава 10.2. Расчет ссылок и анкоров внутренней перелинковки*

## What it covers

Проектирование матрицы внутренней перелинковки для усиления тематической связности и распределения Link Equity. Метод напрямую влияет на onsiteProminence и PageRank-NearestSeeds, создавая логические связи между pillar и cluster страницами. Использование LSI-ключей в анкорах предотвращает anchorMismatchDemotion и повышает семантическую плотность кластера.

## Concrete steps / questions

- Определить логические связи: pillar → cluster, cluster → pillar, cluster ↔ cluster.
- Сформировать карту перелинковки без циклов и дублирующихся анкоров.
- Сгенерировать уникальные анкоры на основе LSI-ключей и сущностей (entities).
- Обеспечить релевантность анкора содержимому целевой страницы, а не источника.

## Cross-reference

Pairs with DrMax v1.5 prompts: **09, 18** (in skill `seo-prompt-engineering-2026`)
