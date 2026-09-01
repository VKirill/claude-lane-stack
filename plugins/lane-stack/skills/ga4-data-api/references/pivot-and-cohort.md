# Pivot Reports + Cohort Spec

## runPivotReport — 2D кросстабы

```
POST /v1beta/properties/{property_id}:runPivotReport
```

### Request schema

```json
{
  "dimensions": [{"name":"sessionSourceMedium"},{"name":"deviceCategory"}],
  "metrics":    [{"name":"sessions"},{"name":"totalRevenue"}],
  "dateRanges": [{"startDate":"30daysAgo","endDate":"yesterday"}],
  "pivots": [
    {
      "fieldNames": ["sessionSourceMedium"],
      "orderBys":   [{"metric":{"metricName":"sessions"},"desc":true}],
      "offset":     "0",
      "limit":      "20",
      "metricAggregations": ["TOTAL"]
    },
    {
      "fieldNames": ["deviceCategory"],
      "orderBys":   [{"dimension":{"dimensionName":"deviceCategory","orderType":"ALPHANUMERIC"}}],
      "limit":      "3"
    }
  ],
  "dimensionFilter":   { /* FilterExpression */ },
  "metricFilter":      { /* FilterExpression */ },
  "currencyCode":      "USD",
  "cohortSpec":        null,
  "keepEmptyRows":     false,
  "returnPropertyQuota": true
}
```

### Что делает pivot

- Все `dimensions` в `dimensions[]` должны быть распределены по pivots (если dimension не в pivot — она невидима в выводе)
- Каждый `pivots[i]` — отдельная "ось". Декартово произведение всех осей = строки результата
- `fieldNames[]` — какие dimensions показывать на этой оси
- `orderBys` / `offset` / `limit` — сортировка и пагинация **в пределах этой оси**

### Response

```json
{
  "pivotHeaders": [
    {
      "pivotDimensionHeaders": [
        {"dimensionValues":[{"value":"google / cpc"}]},
        {"dimensionValues":[{"value":"organic / google"}]}
      ],
      "rowCount": 20
    },
    {
      "pivotDimensionHeaders": [
        {"dimensionValues":[{"value":"desktop"}]},
        {"dimensionValues":[{"value":"mobile"}]},
        {"dimensionValues":[{"value":"tablet"}]}
      ],
      "rowCount": 3
    }
  ],
  "dimensionHeaders": [...],
  "metricHeaders":    [...],
  "rows":             [...],
  "aggregates":       [...],
  "metadata":         {...},
  "propertyQuota":    {...}
}
```

### Когда использовать

- Дашборд с матрицей: источник по горизонтали, устройство по вертикали
- Сравнение N топ-источников × M топ-стран
- Когда нужны top-N в каждом измерении (Pivot limits применяются per-axis, а не глобально)

### Когда НЕ использовать

- Простой плоский отчёт → `runReport` дешевле и проще парсить
- Полная свобода UI → парсить ответ pivot непросто, в production обычно плоский отчёт + локальный pivot в pandas/polars

### batchRunPivotReports

Аналог `batchRunReports` для pivot — до 5 в 1 вызов. Endpoint: `:batchRunPivotReports`.

## cohortSpec — когортный анализ

Внутри `runReport`. Анализирует retention/возвращаемость когорт пользователей.

### Schema

```json
"cohortSpec": {
  "cohorts": [
    {
      "name":      "weekly_2026-01-06",     // optional метка
      "dimension": "firstSessionDate",      // обычно эта (другие редко)
      "dateRange": {
        "startDate": "2026-01-06",          // первый день когорты
        "endDate":   "2026-01-12"           // последний день
      }
    }
  ],
  "cohortsRange": {
    "granularity": "DAILY|WEEKLY|MONTHLY",
    "startOffset": 0,                       // optional, default 0
    "endOffset":   8                        // сколько периодов наблюдать
  },
  "cohortReportSettings": {
    "accumulate": false                     // true: cumulative до n-го периода
  }
}
```

### Cohort dimensions

| Dimension | Когда доступна |
|---|---|
| `cohort` | Всегда (имя/индекс когорты) |
| `cohortNthDay` | `granularity=DAILY` |
| `cohortNthWeek` | `granularity=WEEKLY` |
| `cohortNthMonth` | `granularity=MONTHLY` |

### Cohort metrics

| Metric | Семантика |
|---|---|
| `cohortActiveUsers` | Активных пользователей в когорте в N-й период |
| `cohortTotalUsers` | Всего пользователей в когорте (база) |

Retention rate в SQL: `cohortActiveUsers / cohortTotalUsers`. На стороне API можно собрать через `metrics.expression`:

```json
{ "name": "retention", "expression": "cohortActiveUsers/cohortTotalUsers" }
```

### Полный пример: 8-недельный retention для когорт января

```json
{
  "dimensions": [
    {"name": "cohort"},
    {"name": "cohortNthWeek"}
  ],
  "metrics": [
    {"name": "cohortActiveUsers"},
    {"name": "cohortTotalUsers"},
    {"name": "retention", "expression": "cohortActiveUsers/cohortTotalUsers"}
  ],
  "dateRanges": [],
  "cohortSpec": {
    "cohorts": [
      { "name":"week_01", "dimension":"firstSessionDate",
        "dateRange": {"startDate":"2026-01-06","endDate":"2026-01-12"}},
      { "name":"week_02", "dimension":"firstSessionDate",
        "dateRange": {"startDate":"2026-01-13","endDate":"2026-01-19"}},
      { "name":"week_03", "dimension":"firstSessionDate",
        "dateRange": {"startDate":"2026-01-20","endDate":"2026-01-26"}},
      { "name":"week_04", "dimension":"firstSessionDate",
        "dateRange": {"startDate":"2026-01-27","endDate":"2026-02-02"}}
    ],
    "cohortsRange": {
      "granularity": "WEEKLY",
      "startOffset": 0,
      "endOffset":   7
    }
  },
  "orderBys": [
    {"dimension": {"dimensionName": "cohort"}},
    {"dimension": {"dimensionName": "cohortNthWeek", "orderType":"NUMERIC"}}
  ]
}
```

Получим матрицу: 4 cohort × 8 nthWeek = до 32 rows. Удобно построить retention curve.

### Гранулярности

| Granularity | Длина cohort range |
|---|---|
| `DAILY` | dateRange ровно 1 день |
| `WEEKLY` | dateRange ровно 7 дней (Mon-Sun по time zone property) |
| `MONTHLY` | dateRange ровно один календарный месяц |

Несовпадение длины → 400 INVALID_ARGUMENT.

### Важно

- `dateRanges` в основном теле запроса **не используется** для cohort (он определяется через `cohortsRange`). Передавать пустой массив или опустить
- Не все обычные dimensions/metrics доступны в cohort report (например, `pagePath` — нет)
- `accumulate: true` — useful для cumulative retention (1+1, 2+1, 3+2, ...)
- Cohorts дороже по token cost — несколько cohort в одном запросе быстро съедают бюджет
- Без `cohortNthDay`/`Week`/`Month` в dimensions — результат бесполезен (нельзя построить retention curve)
