# Admin API v1beta

GA4 configuration: accounts, properties, data streams, custom dimensions/metrics, conversion events.

## Base URL

```
https://analyticsadmin.googleapis.com/v1beta/
```

## OAuth scopes

| Scope | Возможности |
|---|---|
| `analytics.readonly` | Все GET (list, get) |
| `analytics.edit` | Создание/обновление/удаление properties, customDimensions, conversionEvents |
| `analytics.manage.users` | User management |

Service account работает так же, как для Data API — те же ключи, отдельный grant в GA4 (Property/Account Access Management).

## Endpoint map

### Accounts

| Endpoint | Назначение |
|---|---|
| `GET /accounts` | Список accounts текущего user/SA |
| `GET /accounts/{accountId}` | Детали аккаунта |
| `DELETE /accounts/{accountId}` | Удаление (опасно) |
| `PATCH /accounts/{accountId}` | Update display name etc |

### Properties

| Endpoint | Назначение |
|---|---|
| `GET /properties?filter=parent:accounts/{accountId}` | Список GA4 properties в аккаунте |
| `GET /properties/{propertyId}` | Детали property (timezone, currency, industry, parent account) |
| `POST /properties` | Создать новую property |
| `PATCH /properties/{propertyId}` | Update (currency, timezone, ...) |
| `DELETE /properties/{propertyId}` | Удалить (опасно, есть recovery) |

### Data streams

| Endpoint | Назначение |
|---|---|
| `GET /properties/{id}/dataStreams` | Список streams (web/iOS/Android) |
| `GET /properties/{id}/dataStreams/{streamId}` | Детали (measurement ID для web stream) |

### Custom dimensions

| Endpoint | Назначение |
|---|---|
| `GET /properties/{id}/customDimensions` | Список — нужен чтобы понять `customEvent:xxx` apiNames |
| `POST /properties/{id}/customDimensions` | Создать (scope EVENT/USER/ITEM) |
| `PATCH /properties/{id}/customDimensions/{cdId}` | Update displayName/description |
| `POST /properties/{id}/customDimensions/{cdId}:archive` | Архивировать (вместо delete) |

### Custom metrics

| Endpoint | Назначение |
|---|---|
| `GET /properties/{id}/customMetrics` | Список |
| `POST /properties/{id}/customMetrics` | Создать с measurementUnit (STANDARD, CURRENCY, FEET, METERS, ...) |

### Conversion events (legacy) / Key events

| Endpoint | Назначение |
|---|---|
| `GET /properties/{id}/conversionEvents` | Список (с 2026 deprecated в пользу keyEvents) |
| `POST /properties/{id}/conversionEvents` | Mark event as conversion |
| `DELETE /properties/{id}/conversionEvents/{id}` | Unmark |
| `GET /properties/{id}/keyEvents` | Новый API (Key Events) |
| `POST /properties/{id}/keyEvents` | Создать key event |

> С 2026 года GA4 переименовал "conversion events" в "key events". Старые endpoints работают через alias, но новые проекты — на `keyEvents`.

### Access reports

| Endpoint | Назначение |
|---|---|
| `POST /properties/{id}:runAccessReport` | Кто и когда обращался к данным property (audit log для безопасности) |

## Python client (`google-analytics-admin`)

```bash
pip install google-analytics-admin
```

```python
from google.analytics.admin import AnalyticsAdminServiceClient
from google.analytics.admin_v1beta.types import ListPropertiesRequest

admin = AnalyticsAdminServiceClient()  # GOOGLE_APPLICATION_CREDENTIALS

# Список properties в account
resp = admin.list_properties(ListPropertiesRequest(
    filter="parent:accounts/123456789",
    page_size=200,
))
for p in resp:
    print(p.name, p.display_name, p.currency_code, p.time_zone)

# Custom dimensions для property
cds = admin.list_custom_dimensions(parent="properties/381112233")
for cd in cds:
    print(cd.parameter_name, "→", cd.display_name, "(scope:", cd.scope.name, ")")
```

## Node.js client (`@google-analytics/admin`)

```bash
npm install @google-analytics/admin
```

```javascript
const {AnalyticsAdminServiceClient} = require('@google-analytics/admin');
const admin = new AnalyticsAdminServiceClient();

const [properties] = await admin.listProperties({
  filter: 'parent:accounts/123456789',
  pageSize: 200,
});
for (const p of properties) {
  console.log(p.name, p.displayName, p.currencyCode, p.timeZone);
}

const [cds] = await admin.listCustomDimensions({
  parent: 'properties/381112233',
});
for (const cd of cds) {
  console.log(cd.parameterName, cd.displayName, cd.scope);
}
```

## Discovery pattern: bootstrap всех properties

Для агентств / мульти-бренд проектов — типичная задача "получить все доступные GA4 properties и для каждой — список custom dims".

```python
accounts = admin.list_accounts()
all_properties = []
for acc in accounts:
    props = admin.list_properties(filter=f"parent:{acc.name}")
    for p in props:
        all_properties.append({
            "property_id": p.name.split("/")[-1],
            "display_name": p.display_name,
            "currency": p.currency_code,
            "timezone": p.time_zone,
            "industry": p.industry_category.name,
            "parent_account": acc.display_name,
        })
```

Сохранить в БД, использовать как источник для Data API pipeline.

## Custom dimension scope

| Scope | Семантика | apiName в Data API |
|---|---|---|
| `EVENT` | per-event параметр (например `plan_type`) | `customEvent:plan_type` |
| `USER` | user property | `customUser:vip_status` |
| `ITEM` | e-commerce item param | `customItem:item_tag` |

Эти `apiName` — то, что подставляется в `dimensions[].name` в `runReport`.

## Pattern: создать conversion event программно

```python
from google.analytics.admin_v1beta.types import ConversionEvent

ce = admin.create_conversion_event(
    parent="properties/381112233",
    conversion_event=ConversionEvent(event_name="purchase"),
)
print(ce.name, ce.create_time)
```

`event_name` должен **уже существовать** в GA4 (отправляться) — нельзя сделать conversion из несуществующего события.

## Quotas

Admin API имеет свои квоты, обычно 1500 req/day, 60 req/min на проект. Read-операции (list/get) дешёвые, mutations дороже. В отличие от Data API, токенной модели нет — обычный rate limit.

## Audit / security

- `runAccessReport` — отчёт о доступе к property (кто читал, какие dimensions/metrics)
- Полезно для compliance и расследования утечек
- Required: `analytics.edit` scope или Administrator role в Property Access
