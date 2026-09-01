# Realtime API — runRealtimeReport

## Endpoint

```
POST https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runRealtimeReport
```

## Окно

- **30 минут** для стандартного GA4
- **60 минут** для GA4 360
- НЕ "live now" — данные с задержкой ~30-60 сек от события

## Request schema

```json
{
  "dimensions": [{"name": "country"}, {"name": "eventName"}],
  "metrics":    [{"name": "activeUsers"}, {"name": "eventCount"}],
  "dimensionFilter": { /* FilterExpression */ },
  "metricFilter":    { /* FilterExpression */ },
  "limit": "100",
  "metricAggregations": ["TOTAL"],
  "orderBys": [{"metric": {"metricName": "activeUsers"}, "desc": true}],
  "returnPropertyQuota": true,
  "minuteRanges": [
    {"name": "last_5min",  "startMinutesAgo": 5,  "endMinutesAgo": 0},
    {"name": "prev_5min",  "startMinutesAgo": 10, "endMinutesAgo": 6}
  ]
}
```

### `minuteRanges[]`

- До **2 ranges** в запросе
- `startMinutesAgo`: inclusive начало (default 29; max 29 / 59 для 360)
- `endMinutesAgo`: inclusive конец (default 0)
- `name`: метка для различения в выводе (как `dateRanges[].name`)

Если 2+ ranges → в результате появляется неявная dimension `dateRange` с именем/индексом.

## Поддерживаемые dimensions (realtime)

Узкий поднабор стандартных:

| Dimension | Примечание |
|---|---|
| `appVersion` | |
| `audienceId`, `audienceName` | |
| `city`, `country`, `countryId` | Геолокация |
| `deviceCategory` | |
| `eventName` | Главная dimension realtime |
| `minutesAgo` | Сколько минут назад событие |
| `platform` | web / ios / android |
| `streamId`, `streamName` | Источник GA4 потока |
| `unifiedScreenName` | Универсальная страница (web + mobile) |

**Чего НЕТ в realtime** (но есть в обычном):
- `pagePath`, `pageTitle`, `pageLocation` (есть только `unifiedScreenName`)
- `sessionSource`, `sessionMedium`, `sessionCampaign...` (нет session-scope атрибуции)
- `firstUserSource/Medium/...`
- `browser`, `operatingSystem`
- e-commerce dimensions (`itemName`, `transactionId`, ...)
- Cohort dimensions

Полный список — через `GET /v1beta/properties/{id}/metadata` для realtime отдельно.

## Поддерживаемые metrics

| Metric | Описание |
|---|---|
| `activeUsers` | Активные пользователи в окне |
| `screenPageViews` | Просмотры |
| `eventCount` | События |
| `conversions` | Ключевые события |

## Что не поддерживается

- `cohortSpec` — нет
- `dateRanges` — заменены на `minuteRanges`
- `metricAggregations` ограничены
- Audiences-фильтрация — через специальный `audienceId` (если настроены аудитории)

## Пример: топ-страны прямо сейчас

```json
{
  "dimensions": [{"name": "country"}],
  "metrics":    [{"name": "activeUsers"}],
  "orderBys":   [{"metric": {"metricName": "activeUsers"}, "desc": true}],
  "limit":      "10"
}
```

## Пример: всплеск checkout-событий

```json
{
  "dimensions": [{"name": "minutesAgo"}, {"name": "eventName"}],
  "metrics":    [{"name": "eventCount"}],
  "dimensionFilter": {
    "filter": {
      "fieldName": "eventName",
      "inListFilter": {"values": ["begin_checkout", "purchase", "add_to_cart"]}
    }
  },
  "orderBys": [{"dimension": {"dimensionName": "minutesAgo", "orderType": "NUMERIC"}}]
}
```

## Когда использовать

- Дашборд "сейчас на сайте" (активные пользователи, топ-страны/устройства)
- Алертинг: всплеск/падение трафика → Slack/email
- Smoke-test после деплоя: появились ли события?
- Мониторинг кампании в первые часы запуска

## Когда НЕ использовать

- Историческая аналитика (даже за вчера) → `runReport`
- Source / Medium attribution (нет в realtime)
- Точные конверсионные метрики (revenue, transactions) — нужны session-level dimensions, отсутствуют

## Quota

Realtime имеет отдельную квоту-категорию **Realtime Tokens**, с теми же числами что Core:
- Realtime Tokens / property / day: 200 000 (360 = 2 000 000)
- Realtime Tokens / property / hour: 40 000
- Realtime Tokens / project / property / hour: 14 000
- Concurrent Realtime Requests / property: 10

Не конкурирует с Core квотой — это отдельный пул.

## Pattern: long-poll каждые 30-60 сек

```python
import time
while True:
    resp = client.run_realtime_report(...)
    update_dashboard(resp)
    time.sleep(30)  # 60 — безопаснее для квоты
```

Не используй < 30s интервал — нет смысла (данные не успевают обновляться) + лишние токены.

## Python client

```python
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    Dimension, Metric, RunRealtimeReportRequest, MinuteRange,
)

resp = client.run_realtime_report(RunRealtimeReportRequest(
    property=f"properties/{property_id}",
    dimensions=[Dimension(name="country")],
    metrics=[Metric(name="activeUsers")],
    minute_ranges=[MinuteRange(name="last_30m", start_minutes_ago=29, end_minutes_ago=0)],
    limit=10,
    return_property_quota=True,
))
```

## Node.js client

```javascript
const [resp] = await analyticsDataClient.runRealtimeReport({
  property: `properties/${propertyId}`,
  dimensions: [{name: 'country'}],
  metrics:    [{name: 'activeUsers'}],
  minuteRanges: [{name: 'last_30m', startMinutesAgo: 29, endMinutesAgo: 0}],
  limit: 10,
  returnPropertyQuota: true,
});
```
