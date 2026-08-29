# Clutter & Canonicalization engineering

*Book section: Часть 2 / Глава 3 / 3.3. Каноникализация*

## What it covers

Минимизация общесайтового штрафа clutterScore через жесткое управление каноникализацией (rel=canonical) и редиректами (forwardingdup). Цель — предотвратить 'размазывание' негативных сигналов (isSmearedSignal) с мусорных параметрических URL на качественные разделы сайта.

## Concrete steps / questions

- Не превышает ли количество параметрических дублей порог срабатывания clutterScore?
- Используется ли ContentChecksum96 для выявления внутренних дублей до того, как это сделает Google?
- Консолидированы ли все сигналы (PageRank, NavBoost) на одном CompositeDoc через 301 редирект?

## Cross-reference

Pairs with DrMax v1.5 prompts: **16, 19** (in skill `seo-prompt-engineering-2026`)
