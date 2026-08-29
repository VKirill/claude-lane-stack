# Semantic Cocoon Topology Design

*Book section: Часть 6 / Глава 4 / 4.2. Проектирование трехуровневой иерархии*

## What it covers

Проектирование трехуровневой иерархии (Target/Mixed/Support) для максимизации siteFocusScore и TopicAuthority. Методика опирается на Entity Salience и midCount из Content Warehouse API, превращая сайт в федерацию тематических кластеров. Это позволяет Google точнее определять topicEmbeddings (через BERT/MUM) и присваивать сайту статус экспертного источника в нише.

## Concrete steps / questions

- Идентификация родительской сущности (Entity) в Knowledge Graph.
- Создание Target Page (Матриарх) для аккумуляции LinkValue по ВЧ-запросам.
- Разработка Mixed Pages (Узлы) для классификации темы и СЧ-интентов.
- Генерация Support Pages (Фундамент) для закрытия НЧ-запросов и микро-интентов.
- Проверка изоляции темы: отсутствие семантического шума из соседних коконов.

## Cross-reference

Pairs with DrMax v1.5 prompts: **18, 21** (in skill `seo-prompt-engineering-2026`)
