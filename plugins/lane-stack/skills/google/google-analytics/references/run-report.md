# runReport — стандартный отчёт

## Endpoint

```
POST https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport
Authorization: Bearer {access_token}
Content-Type: application/json
```

## Полный schema запроса

```json
{
  "dimensions": [{"name": "string"}],
  "metrics":    [{"name": "string", "expression": "string"}],
  "dateRanges": [{"startDate": "YYYY-MM-DD|NdaysAgo|today|yesterday",
                  "endDate":   "YYYY-MM-DD|today",
                  "name":      "optional_label"}],
  "dimensionFilter": { /* FilterExpression — см. filters-and-expressions.md */ },
  "metricFilter":    { /* FilterExpression */ },
  "offset": "0",
  "limit":  "10000",
  "metricAggregations": ["TOTAL", "MINIMUM", "MAXIMUM", "COUNT"],
  "orderBys": [
    { "metric":    {"metricName": "sessions"}, "desc": true },
    { "dimension": {"dimensionName": "date", "orderType": "ALPHANUMERIC"} },
    { "pivot":     {"metricName": "sessions",
                     "pivotSelections": [{"dimensionName":"country","dimensionValue":"Russia"}]} }
  ],
  "currencyCode": "USD",
  "cohortSpec":      { /* см. pivot-and-cohort.md */ },
  "keepEmptyRows": false,
  "returnPropertyQuota": true,
  "comparisons": [ /* для сравнительных отчётов */ ]
}
```

## Поля

### `dimensions[]`

До **9** одновременно. Имя — например `country`, `eventName`, `pagePath`. Полный список — `getMetadata` или [официальная схема](https://developers.google.com/analytics/devguides/reporting/data/v1/api-schema). Custom dimensions — через `customEvent:my_param` / `customUser:my_param`.

### `metrics[]`

`name` — стандартная метрика (`activeUsers`, `sessions`, `totalRevenue`). `expression` — формула из других метрик: `"averageRevenuePerUser"` уже есть, но можно собрать свою: `{"name":"rpu","expression":"totalRevenue/activeUsers"}`. Custom metrics — `customEvent:my_metric`.

### `dateRanges[]`

До **4** ranges одновременно. Каждый — `startDate` + `endDate`. Форматы:

- `YYYY-MM-DD` (`2026-01-15`)
- `today`, `yesterday`
- `NdaysAgo` (`7daysAgo`, `30daysAgo`)

`name` — опциональная метка для различения в выводе при multi-range (`"current"`, `"previous"`). Если 2+ ranges, в каждой row появляется dimension `dateRange` со значением name/индекса.

### `dimensionFilter` / `metricFilter`

FilterExpression DSL — см. [filters-and-expressions.md](filters-and-expressions.md).

- `dimensionFilter` — pre-aggregation (WHERE)
- `metricFilter` — post-aggregation (HAVING)

### `orderBys[]`

Три варианта:

```json
{ "metric":    {"metricName": "sessions"}, "desc": true }
{ "dimension": {"dimensionName": "date", "orderType": "ALPHANUMERIC|CASE_INSENSITIVE_ALPHANUMERIC|NUMERIC"} }
{ "pivot":     {"metricName": "sessions", "pivotSelections": [...]} }
```

`desc: true` — по убыванию (default ascending).

### `limit` / `offset`

- `limit`: max **250 000** строк на запрос (default 10 000)
- `offset`: с какой строки начать (для pagination)

Pagination pattern:

```python
LIMIT = 100_000
offset = 0
all_rows = []
while True:
    req.limit = LIMIT
    req.offset = offset
    resp = client.run_report(req)
    all_rows.extend(resp.rows)
    if len(resp.rows) < LIMIT:
        break
    offset += LIMIT
```

Также `response.row_count` — общее число строк до limit.

### `metricAggregations[]`

`TOTAL`, `MINIMUM`, `MAXIMUM`, `COUNT`. Возвращаются в отдельных полях ответа: `totals[]`, `minimums[]`, `maximums[]`, `counts[]`. Это **не** sum(rows), а агрегат по всему срезу, учитывающий cardinality cap.

### `keepEmptyRows`

`false` (default) — строки с нулевыми metric-values пропускаются. `true` — оставлять. Полезно для timeseries без пробелов в датах.

### `returnPropertyQuota`

`true` — в ответ добавляется `propertyQuota` блок со всеми пятью токенными бюджетами и concurrent. Включай в production-скриптах.

### `currencyCode`

ISO 4217 (`USD`, `EUR`, `RUB`). Конвертация revenue-метрик. По умолчанию — currency property.

## Schema ответа

```json
{
  "dimensionHeaders": [{"name": "country"}],
  "metricHeaders":    [{"name": "activeUsers", "type": "TYPE_INTEGER"}],
  "rows": [
    { "dimensionValues": [{"value": "Russia"}],
      "metricValues":    [{"value": "12345"}] }
  ],
  "totals":    [{"dimensionValues":[{"value":"RESERVED_TOTAL"}],"metricValues":[{"value":"50000"}]}],
  "minimums":  [...],
  "maximums":  [...],
  "rowCount":  42,
  "metadata": {
    "currencyCode": "USD",
    "timeZone":     "Europe/Moscow",
    "dataLossFromOtherRow": false,
    "samplingMetadatas": []
  },
  "propertyQuota": {
    "tokensPerDay":              {"consumed": 1500, "remaining": 198500},
    "tokensPerHour":             {"consumed": 80,   "remaining": 39920},
    "concurrentRequests":        {"consumed": 1,    "remaining": 9},
    "serverErrorsPerProjectPerHour": {"consumed": 0, "remaining": 10},
    "potentiallyThresholdedRequestsPerHour": {"consumed": 0, "remaining": 120},
    "tokensPerProjectPerHour":   {"consumed": 80,   "remaining": 13920}
  },
  "kind": "analyticsData#runReport"
}
```

### Sampling

`metadata.samplingMetadatas[]` — по одной записи на dateRange. Если массив непустой и есть `samplesReadCount < samplingSpaceSize` — данные сэмплированы.

`metadata.dataLossFromOtherRow: true` — cardinality cap, есть `(other)` bucket. Какие-то строки склеены.

### Типы metric values

`metricHeaders[].type`:
- `TYPE_INTEGER`
- `TYPE_FLOAT`
- `TYPE_SECONDS` (длительность)
- `TYPE_MILLISECONDS`
- `TYPE_CURRENCY`
- `TYPE_STANDARD`
- `TYPE_PERCENT`

Все `value` в `metricValues[].value` — строки, парсить по `type`.

## Полный пример: трафик по источнику за 30 дней

```json
POST /v1beta/properties/381112233:runReport
{
  "dimensions": [
    {"name": "date"},
    {"name": "sessionSourceMedium"},
    {"name": "deviceCategory"}
  ],
  "metrics": [
    {"name": "sessions"},
    {"name": "activeUsers"},
    {"name": "engagementRate"},
    {"name": "conversions"},
    {"name": "totalRevenue"}
  ],
  "dateRanges": [
    {"startDate": "30daysAgo", "endDate": "yesterday"}
  ],
  "dimensionFilter": {
    "notExpression": {
      "filter": {
        "fieldName": "sessionSourceMedium",
        "stringFilter": {"matchType": "EXACT", "value": "(direct) / (none)"}
      }
    }
  },
  "orderBys": [
    {"metric": {"metricName": "sessions"}, "desc": true}
  ],
  "limit": "100",
  "metricAggregations": ["TOTAL"],
  "keepEmptyRows": false,
  "returnPropertyQuota": true
}
```

## getMetadata — проверка доступных dimensions/metrics

```
GET /v1beta/properties/{id}/metadata
```

Возвращает полный список dimensions/metrics, включая custom dimensions/metrics конкретной property (с их `apiName` вида `customEvent:plan_type`). Полезно для UI-валидации.

## checkCompatibility

```
POST /v1beta/properties/{id}:checkCompatibility
```

Тот же запрос, что и в `runReport`, но возвращает `dimensionCompatibilities[]` и `metricCompatibilities[]` со статусом `COMPATIBLE` / `INCOMPATIBLE` — без выполнения отчёта. Полезно для UI билдеров запросов.

## Лучшие практики

- **Маленькие date ranges с агрегацией в БД лучше одного огромного.** За месяц с `pagePath` — десятки тысяч токенов. По одному дню × 30 — те же данные, но границы quota мягче и кэшируются индивидуально
- **Не запрашивать "всё подряд".** Каждая дополнительная dimension умножает cardinality
- **Использовать `dimensionFilter` ДО.** Срезы с фильтром на конкретный `eventName` дешевле, чем "всё → фильтровать локально"
- **`keepEmptyRows: true` ТОЛЬКО когда нужно** (например, timeseries дашборд). Иначе пустые строки = трата
- **Кэшировать.** Данные за вчера и старше стабильны (после ~48 ч стабилизации конверсий). Snapshot в БД с TTL
