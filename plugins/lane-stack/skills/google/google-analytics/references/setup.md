# Setup — Authentication, Property ID, Scopes

## 1. Включить APIs в Google Cloud

В Cloud Console (https://console.cloud.google.com) для целевого проекта:

1. **APIs & Services → Library** → найти и включить:
   - **Google Analytics Data API** (для отчётов)
   - **Google Analytics Admin API** (для конфигурации, custom dimensions, accounts list)
2. Без обоих включенных API часть вызовов будет падать с 403 `accessNotConfigured`.

## 2. Найти Property ID (НЕ Measurement ID)

`property_id` — **числовой** идентификатор, обычно 9-10 цифр, например `381112233`.

**Где взять:**
- analytics.google.com → выбрать GA4 property
- **Admin (шестерёнка внизу слева) → Property Settings (в правой колонке "Property")**
- Поле **"PROPERTY ID"** (под именем property)

**Что НЕ Property ID:**
- `G-XXXXXXXXXX` — это **Measurement ID** потока данных (Tag ID). Используется в `gtag.js`, но **не работает** в Data API
- `UA-XXXXXX-Y` — Universal Analytics tracking ID, sunset с 2024-07-01, в API не работает вообще

В коде:

```python
property_id = "381112233"           # из Admin
full_path = f"properties/{property_id}"  # → "properties/381112233"
```

## 3. Service account (рекомендуется для backend)

### Создание

1. Cloud Console → **IAM & Admin → Service Accounts → Create service account**
2. Имя: `ga4-data-reader` (любое)
3. **Roles**: можно ничего не выдавать на уровне проекта (Cloud IAM); доступ к GA4 даётся отдельно на стороне Analytics
4. **Keys → Add Key → Create new key → JSON** → скачать файл (хранить как секрет)
5. Email сервис-аккаунта вида `ga4-data-reader@PROJECT-ID.iam.gserviceaccount.com` — нужен для следующего шага

### Grant в GA4 (КРИТИЧНО)

GA4 имеет свою систему прав, отдельную от Cloud IAM. Без явного grant API вернёт **403 PERMISSION_DENIED**.

1. analytics.google.com → **Admin → Property Access Management** (в правой колонке Property)
2. **+ → Add users**
3. Email service account (`xxx@yyy.iam.gserviceaccount.com`)
4. **Direct roles and data restrictions**: минимум `Viewer` (Data API only). `Analyst` — если нужно management.
5. Опционально: убрать чекбокс "Notify new users by email" (не имеет смысла для service account)
6. **Add**

> **Account-level access** (Admin → Account Access Management) альтернатива — даст доступ ко **всем** properties в account. Удобно для агентств, но шире разрешения.

### Использование

Стандартный путь — env var:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/secure/path/ga4-key.json
```

Клиент инстанцируется без аргументов:

```python
from google.analytics.data_v1beta import BetaAnalyticsDataClient
client = BetaAnalyticsDataClient()
```

```javascript
const {BetaAnalyticsDataClient} = require('@google-analytics/data');
const client = new BetaAnalyticsDataClient();
```

Альтернатива — передать `credentials` явно:

```python
from google.oauth2 import service_account
creds = service_account.Credentials.from_service_account_file(
    "/secure/path/ga4-key.json",
    scopes=["https://www.googleapis.com/auth/analytics.readonly"],
)
client = BetaAnalyticsDataClient(credentials=creds)
```

## 4. OAuth user flow (interactive, для CLI/desktop)

Когда отчёт строит человек под своим Google-аккаунтом:

1. Cloud Console → **APIs & Services → Credentials → Create credentials → OAuth client ID**
2. Application type — Web application или Desktop, в зависимости от сценария
3. Authorized redirect URIs (для Web)
4. Scopes:
   - `https://www.googleapis.com/auth/analytics.readonly` — read (Data API + Admin read)
   - `https://www.googleapis.com/auth/analytics.edit` — mutations Admin API (создание custom dimensions, conversion events)

Token refresh — стандартный Google OAuth pattern (refresh_token хранить надёжно).

## 5. OAuth scopes — таблица

| Scope | Для чего |
|---|---|
| `analytics.readonly` | Data API runReport/realtime/pivot/batch + Admin API GET-ы |
| `analytics.edit` | Admin API mutations (`customDimensions.create`, `conversionEvents.create`) |
| `analytics.manage.users` | Управление user-доступом к property |
| `analytics` (full) | Полный доступ ко всем endpoints |

Для backend pipelines почти всегда достаточно `analytics.readonly`.

## 6. Quickstart-проверка

После grant в GA4 и установки переменной окружения — минимальный smoke-test:

```python
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange, Dimension, Metric, RunReportRequest,
)

property_id = "381112233"
client = BetaAnalyticsDataClient()

resp = client.run_report(RunReportRequest(
    property=f"properties/{property_id}",
    dimensions=[Dimension(name="country")],
    metrics=[Metric(name="activeUsers")],
    date_ranges=[DateRange(start_date="7daysAgo", end_date="today")],
))
for row in resp.rows:
    print(row.dimension_values[0].value, row.metric_values[0].value)
```

Если вернулись rows — настройка корректная. Если 403 — проверить Property Access Management. Если 400 INVALID_ARGUMENT — проверить, что `property_id` — числовой ID, не `G-XXX`.

## 7. Multi-property

Часто требуется обходить десятки property (агентство, мульти-бренд). Подход:

1. Один service account
2. Account-level grant в GA4 (Admin → Account Access Management) → доступ ко всем properties в account автоматически
3. Список properties — через Admin API `properties.list?filter=parent:accounts/{accountId}`
4. Бежим по списку, делаем `runReport` на каждый

## 8. Безопасность ключа

- **Не коммитить** JSON-ключ в git (даже в private repo)
- В production — Secret Manager (Google Secret Manager, Vault, AWS SM)
- В dev — `.env` + `.gitignore`
- Ротация ключей: создать новый, перевыпустить, удалить старый (Cloud Console → Service Accounts → Keys)
- Утечка = доступ ко **всем** GA4 properties, где сервис-аккаунт в grant-листе. Срочно удалить ключ и инвалидировать grant
