# Multi-stage Content Prompt Engineering

*Book section: Часть 5 / Глава 3 / 3.1. Задачи, структура, входные данные*

## What it covers

Методика создания экспертного контента через 4-фазный конвейер (Этапы 0-3), минимизирующая риск pandaDemotion за счет жесткого подавления 'маркетинговой воды'. Система использует иерархию KV-cache (P1-P3) для управления вниманием LLM, внедряя модули FACTUAL и SEO_PRIORITY. Это гарантирует высокую плотность сущностей (midCount) и соответствие интентам, что критично для сигналов siteAuthority и качественной индексации в Google 2026.

## Concrete steps / questions

- Этап 0: Установка guardrails и подавление стилевых клише (Style-Suppressor).
- Этап 1: Сбор сущностей (NER), интентов и LSI-фраз в формате JSON.
- Этап 2: Проектирование таксономии (IA) на основе кластеризации интентов (Intent-first).
- Этап 3: Генерация финального обзора с обязательной проверкой coverage_entities >= 0.90.
- Автоматическая валидация: проверка наличия zero_click_snippets для каждого H2/H3.

## Cross-reference

Pairs with DrMax v1.5 prompts: **17, 24** (in skill `seo-prompt-engineering-2026`)
