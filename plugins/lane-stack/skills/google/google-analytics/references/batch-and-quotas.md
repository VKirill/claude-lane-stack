# Batch + Quotas

## batchRunReports — 5 отчётов в 1 вызове

```
POST https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:batchRunReports
```

### Schema

```json
{
  "requests": [
    { /* RunReportRequest #1 — без property, наследуется из path */ },
    { /* RunReportRequest #2 */ },
    { /* RunReportRequest #3 */ },
    { /* RunReportRequest #4 */ },
    { /* RunReportRequest #5 */ }
  ]
}
```

- **Max 5 requests** в одном batch
- Все запросы — к **той же property** (она в path URL, не в каждом запросе)
- Property поле в внутреннем запросе можно опустить, либо передать тот же ID

### Response

```json
{
  "reports": [
    { /* RunReportResponse #1 */ },
    { /* RunReportResponse #2 */ },
    ...
  ],
  "kind": "analyticsData#batchRunReports"
}
```

`reports[]` — массив ответов в том же порядке, что и `requests[]`. Если один из под-запросов падает с ошибкой — batch целиком возвращает 4xx/5xx (не frame-by-frame).

### Когда использовать

- Дашборд с 3-5 виджетами на одной property → 1 HTTP вместо 5
- Параллельные срезы (по источнику + по устройству + по странам + конверсии + revenue)
- Снижает latency в 3-5×, экономит rate-limit (1 concurrent slot вместо 5)
- **НЕ экономит токены** — каждый под-запрос платит свою цену

### Token-стоимость

Сумма токенов = сумма по всем 5 под-запросам. Concurrent — занимает 1 slot.

### batchRunPivotReports

То же для pivot: `:batchRunPivotReports`, до 5 `RunPivotReportRequest` за раз.

## Quota model

### Стандартные числа (Standard GA4)

| Quota | Limit | Сброс |
|---|---|---|
| Core Tokens / property / day | **200 000** | UTC день |
| Core Tokens / property / hour | **40 000** | UTC час |
| Core Tokens / project / property / hour | **14 000** | UTC час |
| Core Concurrent Requests / property | **10** | мгновенно |
| Core Server Errors / project / property / hour | **10** | UTC час |
| Potentially Thresholded Requests / hour | **120** | UTC час |

### GA4 360

Все Core-числа умножаются на **10** (2M токенов/день).

### Realtime / Funnel — отдельные пулы

Та же структура и числа, не конкурируют с Core.

## Что такое токен

Не фиксированная "1 запрос = 1 токен". Стоимость одного `runReport` зависит от:

- **Длина dateRange** — за неделю дороже, чем за день
- **Число dimensions** — больше срезов = выше стоимость
- **Число metrics** — мало влияет
- **Cardinality dimensions** — `pagePath`, `eventName`, `landingPagePlusQueryString`, `pageLocation` — high-cardinality, тратят десятки токенов даже на узком dateRange
- **Сложность FilterExpression** — глубокие andGroup/orGroup увеличивают цену
- **Объём событий property** — крупные сайты дороже маленьких на тех же dimensions
- **Pivot и cohort** — дороже flat
- **Sampling-обработка** — если требуется обработать больше событий, чем порог

Точную формулу Google не публикует — только эмпирически через `propertyQuota` в ответе.

## PropertyQuota в response

При `returnPropertyQuota: true`:

```json
"propertyQuota": {
  "tokensPerDay":                      {"consumed": 12450, "remaining": 187550},
  "tokensPerHour":                     {"consumed": 320,   "remaining": 39680},
  "tokensPerProjectPerHour":           {"consumed": 320,   "remaining": 13680},
  "concurrentRequests":                {"consumed": 1,     "remaining": 9},
  "serverErrorsPerProjectPerHour":     {"consumed": 0,     "remaining": 10},
  "potentiallyThresholdedRequestsPerHour": {"consumed": 0, "remaining": 120}
}
```

Сохраняй `consumed/remaining` после каждого запроса в логи. Если `remaining` падает быстрее ожидаемого — есть тяжёлые запросы.

### Сколько стоил последний запрос

Делать diff `consumed` до и после, либо использовать готовый счётчик в Redis (см. integration.md).

## Best practices для quota

1. **Кэшировать.** Данные за вчера и старше стабильны после ~48h. Snapshot в БД, не дёргать API
2. **Узкие dateRanges.** За день × 30 вызовов лучше, чем за месяц × 1 — лучше для cardinality cap, кэш гранулярнее
3. **Параллельность ≤ 8.** Лимит 10 — оставлять 1-2 на пиковые операции
4. **Откладывать высокую cardinality.** Если нужно `pagePath` или `eventName` — выделить отдельный pipeline с rate-limit, остальное собирать кучно
5. **Batch когда возможно.** 5 виджетов дашборда → 1 batch вместо 5 запросов
6. **Алертить на `remaining < 20%`.** На уровне log monitoring или Prometheus
7. **`returnPropertyQuota: true` в production.** Без этого slепые quota issues

## 429 RESOURCE_EXHAUSTED

Получили 429 → читать `propertyQuota` (если возвращалось до 429), определить, какая категория исчерпана:

- Если `concurrentRequests.remaining = 0` → подождать и повторить
- Если `tokensPerHour.remaining ≈ 0` → подождать до конца часа (UTC reset)
- Если `tokensPerDay.remaining ≈ 0` → ждать до UTC midnight
- Если `tokensPerProjectPerHour.remaining = 0` → запросы из этого проекта временно заблокированы; либо использовать другой Cloud project, либо разнести trafic

**Не retry с exponential backoff в течение секунды** — токен-квоты не сбрасываются в секундах.

## Расчёт бюджета для pipeline

Пример: 100 properties × ежедневный snapshot из 5 виджетов.

- 100 properties × 1 batch (5 reports) / day = 100 batch-вызовов
- Каждый batch ≈ 50-500 токенов (зависит от размера property)
- Бюджет на property: 200 000 токенов/день — 100× запас даже на тяжёлых property
- Concurrent: запускать параллельно ≤ 10 properties

При планировании больших pipelines всегда сначала **проверить на 5-10 properties с `returnPropertyQuota`** и только потом масштабировать.
