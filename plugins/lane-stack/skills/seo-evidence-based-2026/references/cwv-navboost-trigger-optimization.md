# CWV-NavBoost Trigger optimization

*Book section: Часть 2 / Глава 4 / 4.1. CWV как триггер для NavBoost*

## What it covers

Оптимизация Core Web Vitals (LCP, INP, CLS) не как самоцель, а как способ предотвращения badClicks. Техника использует данные mobileCwv и time-to-first-byte-per-doc из Chrome (CrUX) для обеспечения технической стабильности, исключающей раздражение пользователя и его уход в SERP.

## Concrete steps / questions

- Провоцирует ли высокий CLS ошибочные клики и последующий возврат в поиск (badClick)?
- Является ли задержка TTFB критическим барьером для отрисовки LCP-элемента?
- Соответствует ли INP (Interaction to Next Paint) ожиданиям пользователя об отзывчивости интерфейса?

## Cross-reference

Pairs with DrMax v1.5 prompts: **24** (in skill `seo-prompt-engineering-2026`)
