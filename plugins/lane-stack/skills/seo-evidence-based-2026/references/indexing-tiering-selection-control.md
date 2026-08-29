# Indexing Tiering & Selection control

*Book section: Часть 1 / Глава 1 / 1.2.1. Индексация и тиризация*

## What it covers

Обеспечение попадания контента в 'Base' тир индексации (Alexandria/SegIndexer) через оптимизацию scaledSelectionTierRank. Метод направлен на предотвращение попадания страниц в 'Landfills' (свалки) путем улучшения первичных сигналов качества в CompressedQualitySignals еще до начала ранжирования.

## Concrete steps / questions

- Попадает ли новый контент в основной индекс (Base) или отсеивается в Zeppelins/Landfills?
- Достаточно ли высок первичный скоринг Mustang для прохождения фильтрации?
- Не заблокированы ли критические ресурсы, влияющие на оценку качества при индексации?

## Cross-reference

Pairs with DrMax v1.5 prompts: **14, 24** (in skill `seo-prompt-engineering-2026`)
