# google-ads — Reference Index

Карта по разделам. Загружай только нужный файл, не всё сразу.

## Decision map

| Что спрашивает клиент / какая задача | Файл |
|---|---|
| «Можно ли запустить Google Ads в Россию» / клиент таргетит РФ | [russia-context.md](russia-context.md) — **читай первым** |
| «Какой формат подходит под мою задачу» / «RSA vs PMax vs Display» | [ad-formats.md](ad-formats.md) |
| «Сколько символов в headline / description / path» / валидация лимитов | [character-limits.md](character-limits.md) + запуск validator |
| «Напиши headlines для RSA» / «как структурировать креатив» | [creative-frameworks.md](creative-frameworks.md) |
| «Можно ли рекламировать [ниша]» / disapproved ad / policy check | [policies.md](policies.md) |
| «Какой CTR ожидать» / «какой CPC нормально для ниши» / расчёт бюджета | [benchmarks.md](benchmarks.md) |
| «Готов ли я запускать кампанию» / final check перед launch | [pre-launch-checklist.md](pre-launch-checklist.md) |
| «Как пользоваться validator» / format input YAML | [validator-usage.md](validator-usage.md) |

## Quick start workflow

Когда клиент приходит с запросом про Google Ads — иди по этому порядку:

1. **Russia gate** — `russia-context.md` — клиент таргетит РФ → STOP, направление в Я.Директ. Иначе → продолжаем.
2. **Format choice** — `ad-formats.md` — выбор RSA / PMax / Display / etc по задаче.
3. **Policy check** — `policies.md` — ниша разрешена? Какие ограничения?
4. **Bench expectations** — `benchmarks.md` — какой CTR / CPC ожидать; устанавливаем целевые KPI.
5. **Creative** — `creative-frameworks.md` — пишем headlines / descriptions по правилам.
6. **Limits check** — `character-limits.md` — сверяем лимиты по формату.
7. **Validate** — `scripts/validate-ads.py` — прогон креатива через скрипт.
8. **Pre-launch** — `pre-launch-checklist.md` — финальный чек-лист.

## Files at a glance

- **russia-context.md** (~100 строк) — блокировка с 2022, что доступно/недоступно, альтернативы
- **ad-formats.md** (~400 строк) — 8 форматов с asset groups, target use cases, лимитами
- **character-limits.md** (~200 строк) — единая таблица всех лимитов по форматам и assets
- **creative-frameworks.md** (~250 строк) — как писать под RSA (динамическая сборка), pinning, diversity
- **policies.md** (~250 строк) — restricted/prohibited категории, editorial, misrepresentation
- **benchmarks.md** (~200 строк) — CTR/CPC/CR/QS по 12+ индустриям 2026
- **pre-launch-checklist.md** (~100 строк) — 35-пунктовый pre-launch
- **validator-usage.md** (~80 строк) — usage скрипта, input format, error codes

## Scripts

- **scripts/validate-ads.py** — CLI Python валидатор для всех 8 форматов. См. `validator-usage.md`.
