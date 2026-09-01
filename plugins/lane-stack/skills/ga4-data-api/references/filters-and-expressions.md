# FilterExpression DSL

`dimensionFilter` и `metricFilter` принимают одну и ту же структуру `FilterExpression`. Древовидный DSL: каждый узел — **один из** четырёх вариантов (oneOf), нельзя сочетать.

## Узлы

```json
FilterExpression = {
  "andGroup":      FilterExpressionList,   // AND по списку выражений
  "orGroup":       FilterExpressionList,   // OR по списку выражений
  "notExpression": FilterExpression,       // NOT над выражением (унарный)
  "filter":        Filter                  // Лист: реальное условие
}
```

`FilterExpressionList`:
```json
{ "expressions": [FilterExpression, FilterExpression, ...] }
```

`Filter` (лист):
```json
{
  "fieldName": "<dimensionName или metricName>",
  // одно из:
  "stringFilter":   { ... },
  "inListFilter":   { ... },
  "numericFilter":  { ... },
  "betweenFilter":  { ... }
}
```

## stringFilter

```json
{
  "matchType":     "EXACT|BEGINS_WITH|ENDS_WITH|CONTAINS|FULL_REGEXP|PARTIAL_REGEXP",
  "value":         "string",
  "caseSensitive": false
}
```

| matchType | Семантика |
|---|---|
| `EXACT` | Полное совпадение |
| `BEGINS_WITH` | Префикс |
| `ENDS_WITH` | Суффикс |
| `CONTAINS` | Подстрока |
| `FULL_REGEXP` | RE2 regex, полное совпадение строки |
| `PARTIAL_REGEXP` | RE2 regex, любое вхождение |

`caseSensitive` — default `false`. Поддерживает `MATCH_TYPE_UNSPECIFIED` (но не использовать).

## inListFilter

```json
{
  "values":        ["v1", "v2", "v3"],
  "caseSensitive": false
}
```

Дешевле, чем `OR` из `EXACT`-фильтров.

## numericFilter

```json
{
  "operation": "EQUAL|LESS_THAN|LESS_THAN_OR_EQUAL|GREATER_THAN|GREATER_THAN_OR_EQUAL",
  "value":     { "int64Value": "100" }   // или { "doubleValue": 1.5 }
}
```

Используется в `metricFilter`. В `dimensionFilter` применим только к численным dimensions (`hour`, custom numeric dimensions).

## betweenFilter

```json
{
  "fromValue": { "int64Value": "10" },
  "toValue":   { "int64Value": "100" }
}
```

Inclusive границы. Для метрик и численных dimensions.

## dimensionFilter vs metricFilter

```
[Raw events]
   ↓
   apply dimensionFilter    ← WHERE clause, до агрегации
   ↓
[Aggregated rows by dimensions]
   ↓
   apply metricFilter        ← HAVING clause, после агрегации
   ↓
[Final result]
```

**Примеры разницы:**

| Цель | Какой фильтр |
|---|---|
| Только `eventName == "purchase"` | `dimensionFilter` |
| Только страны, где `sessions > 100` | `metricFilter` |
| `deviceCategory IN ('mobile','tablet')` | `dimensionFilter` |
| `totalRevenue BETWEEN 100 AND 10000` | `metricFilter` |
| Регексп по `pagePath` | `dimensionFilter` |

## Пример: AND из двух условий

```json
"dimensionFilter": {
  "andGroup": {
    "expressions": [
      { "filter": {
          "fieldName": "browser",
          "stringFilter": { "matchType": "EXACT", "value": "Chrome" }
      }},
      { "filter": {
          "fieldName": "country",
          "stringFilter": { "matchType": "EXACT", "value": "United States" }
      }}
    ]
  }
}
```

## Пример: вложенное `(A OR B) AND NOT C`

```json
"dimensionFilter": {
  "andGroup": {
    "expressions": [
      { "orGroup": {
          "expressions": [
            { "filter": { "fieldName": "deviceCategory",
                          "stringFilter": {"matchType":"EXACT","value":"mobile"}}},
            { "filter": { "fieldName": "deviceCategory",
                          "stringFilter": {"matchType":"EXACT","value":"tablet"}}}
          ]
      }},
      { "notExpression": {
          "filter": { "fieldName": "sessionMedium",
                      "stringFilter": {"matchType":"EXACT","value":"(none)"}}
      }}
    ]
  }
}
```

## Пример: regex по pagePath

```json
"dimensionFilter": {
  "filter": {
    "fieldName": "pagePath",
    "stringFilter": {
      "matchType":     "PARTIAL_REGEXP",
      "value":         "^/blog/(\\d{4})/.*",
      "caseSensitive": false
    }
  }
}
```

## Пример: только key events с revenue > 1000

```json
{
  "dimensionFilter": {
    "filter": {
      "fieldName": "eventName",
      "inListFilter": { "values": ["purchase", "subscribe"] }
    }
  },
  "metricFilter": {
    "filter": {
      "fieldName":     "totalRevenue",
      "numericFilter": {
        "operation": "GREATER_THAN",
        "value":     { "doubleValue": 1000.0 }
      }
    }
  }
}
```

## Python — pydantic-style клиент

```python
from google.analytics.data_v1beta.types import (
    Filter, FilterExpression, FilterExpressionList, NumericValue,
)

mobile_or_tablet = FilterExpression(or_group=FilterExpressionList(expressions=[
    FilterExpression(filter=Filter(
        field_name="deviceCategory",
        string_filter=Filter.StringFilter(match_type="EXACT", value="mobile"))),
    FilterExpression(filter=Filter(
        field_name="deviceCategory",
        string_filter=Filter.StringFilter(match_type="EXACT", value="tablet"))),
]))

not_direct = FilterExpression(not_expression=FilterExpression(filter=Filter(
    field_name="sessionMedium",
    string_filter=Filter.StringFilter(match_type="EXACT", value="(none)"))))

dim_filter = FilterExpression(and_group=FilterExpressionList(
    expressions=[mobile_or_tablet, not_direct]))
```

## Node.js — JSON-style

```javascript
const dimensionFilter = {
  andGroup: {
    expressions: [
      { orGroup: { expressions: [
          { filter: { fieldName: 'deviceCategory',
                       stringFilter: { matchType: 'EXACT', value: 'mobile' }}},
          { filter: { fieldName: 'deviceCategory',
                       stringFilter: { matchType: 'EXACT', value: 'tablet' }}},
      ]}},
      { notExpression: {
          filter: { fieldName: 'sessionMedium',
                     stringFilter: { matchType: 'EXACT', value: '(none)' }}
      }}
    ]
  }
};
```

## Подводные камни

- **`stringFilter.value` — строго string.** Для числовой dimension (например, `hour`) нужен `numericFilter`, не `stringFilter` с `"5"`
- **RE2, не PCRE.** Backreferences `\1` не поддерживаются. `(?P<name>...)` named groups — да
- **`caseSensitive: false` по умолчанию.** Уточнить для точного брендового поиска
- **`(direct) / (none)`** — да, с пробелами и скобками; именно так дёргается direct-трафик в GA4
- **`metricFilter` на metric с `expression`** работает: создал `{"name":"rpu","expression":"totalRevenue/activeUsers"}`, фильтр `rpu > 1.5` — валидный
- **Пустой `andGroup.expressions: []`** → 400. Каждый группирующий узел требует ≥ 1 элемент
- **Нельзя сочетать `andGroup` + `filter` в одном узле** (oneOf). Если нужны оба — оборачивай `filter` в `andGroup.expressions[0]`
