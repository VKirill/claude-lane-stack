# Errors

GA4 Data API использует стандартный Google API error envelope:

```json
{
  "error": {
    "code":    403,
    "message": "User does not have sufficient permissions for this property...",
    "status":  "PERMISSION_DENIED",
    "details": [ /* optional */ ]
  }
}
```

## 400 INVALID_ARGUMENT

Невалидный запрос. Тело ответа описывает что именно.

### Частые причины

| Симптом | Причина | Лечение |
|---|---|---|
| `Invalid value at 'property'` | Передан `G-XXXXX` (Measurement ID) вместо числового Property ID | Использовать `properties/{numeric_id}` |
| `Did you mean...?` для dimension/metric | Опечатка или несуществующее имя | Проверить через `getMetadata` |
| `at least one dimension or metric is required` | Пустые `dimensions[]` и `metrics[]` | Добавить хотя бы один |
| `Date range too large` | dateRange > года при специфичных dimensions | Разбить на чанки |
| `dimension X is incompatible with metric Y` | Несовместимая комбинация (например, cohort × non-cohort) | `:checkCompatibility` |
| `Limit must be between 1 and 250000` | `limit > 250 000` | Уменьшить |
| `Cohort granularity does not match dateRange length` | DAILY cohort с dateRange ≠ 1 день | Подогнать длину |
| `Empty andGroup.expressions` | FilterExpression с пустым массивом | Положить ≥ 1 child |

### Что делать

400 — это **детерминированная** ошибка. Retry не поможет. Читать `error.message`, исправить запрос.

## 401 UNAUTHENTICATED

Токен невалиден или отсутствует.

| Причина | Лечение |
|---|---|
| Expired access token | Refresh через refresh_token (OAuth) или re-issue из service account |
| Неверный `GOOGLE_APPLICATION_CREDENTIALS` путь | Проверить env var и существование файла |
| Невалидный JSON ключ (повреждён) | Перевыпустить ключ |
| Ключ удалён в Cloud Console | Создать новый |

## 403 PERMISSION_DENIED

**Самая частая ошибка при первом подключении.**

### Причины (по убыванию частоты)

1. **Service account не добавлен в Property Access Management.** Решение: Admin → Property → Property Access Management → + → email SA → Viewer
2. **Data API не включён в Cloud project.** Решение: Cloud Console → APIs & Services → Library → Google Analytics Data API → Enable
3. **OAuth scope недостаточен.** Для Admin API mutations нужен `analytics.edit`, не `analytics.readonly`
4. **Аккаунт удалён или disabled** в Cloud
5. **Property из другого аккаунта**, где нет grant'а
6. **Quota project mismatch** — billing/quota project в Cloud Console не тот, что у Service Account

### Сообщения

| Message | Причина |
|---|---|
| `User does not have sufficient permissions for this property` | Нет grant в GA4 |
| `Google Analytics Data API has not been used in project XXX before or it is disabled` | API не включён |
| `Request had insufficient authentication scopes` | Wrong scope (для Admin mutations) |
| `accessNotConfigured` | API не включён в Cloud project |

## 404 NOT_FOUND

Property не существует или удалена.

| Причина | Лечение |
|---|---|
| Опечатка в property_id | Проверить через Admin → Property Settings |
| Property удалена | Восстановить (в течение 35 дней recovery period) |
| Service account грантован на другой property | Перепроверить grant |

## 429 RESOURCE_EXHAUSTED

Quota exceeded. См. [batch-and-quotas.md](batch-and-quotas.md) для деталей.

### Какая именно квота — читать из последнего успешного `propertyQuota`

| Категория | Реакция |
|---|---|
| `concurrentRequests` | Снизить parallelism, retry через 1-2с |
| `tokensPerHour` | Подождать до начала следующего UTC часа |
| `tokensPerDay` | Подождать до UTC 00:00 |
| `tokensPerProjectPerHour` | Использовать другой Cloud project ИЛИ ждать |
| `serverErrorsPerProjectPerHour` | На стороне Google → разбираться, что вызывало 500-ки |

### Retry policy

- **НЕ exponential backoff в секундах** — токен-квоты не сбрасываются столь быстро
- Concurrent — да, retry через 1-5с с jitter
- Token — sleep до начала следующего час/день
- Альтернатива — circuit breaker, копить в очередь и сливать после reset

## 500 INTERNAL / 503 UNAVAILABLE

На стороне Google. Транзиентные.

- **Retry с exponential backoff** + jitter, до 3-5 попыток
- Если повторяется системно — Google Cloud Status (https://status.cloud.google.com)
- Учитывается в `serverErrorsPerProjectPerHour` (10/час) — после исчерпания идёт 429

## Идемпотентность

GA4 Data API только читает. Retry безопасный — повторный запрос вернёт те же данные (с учётом possible re-processing после reset). Никаких idempotency keys не нужно.

## Sampling — не ошибка, но сигнал

`response.metadata.samplingMetadatas` непустой → данные сэмплированы. Это **не** HTTP error, но семантически — деградация качества данных. Реакции:

1. Уменьшить scope (короче dateRange, меньше dimensions)
2. Включить GA4 360 (бизнес-решение)
3. Переключиться на BigQuery Export GA4 (raw events, без sampling)
4. Принять и пометить данные как sampled

```python
for sm in resp.metadata.sampling_metadatas:
    if sm.samples_read_count < sm.sampling_space_size:
        ratio = sm.samples_read_count / sm.sampling_space_size
        logger.warning(f"Sampled: {ratio:.2%} ({sm.samples_read_count}/{sm.sampling_space_size})")
```

## `dataLossFromOtherRow`

`response.metadata.dataLossFromOtherRow: true` → cardinality cap, есть `(other)` bucket в результатах.

Реакции:
1. Уменьшить число dimensions или сузить фильтр
2. Принять и пометить data quality

## Pattern: full error handling

```python
from google.api_core import exceptions as gax

try:
    resp = client.run_report(request)
except gax.InvalidArgument as e:
    # 400 — баг в запросе, не retry
    logger.error(f"Bad request: {e.message}")
    raise
except gax.PermissionDenied as e:
    # 403 — проверять grant и API enablement
    logger.error(f"Access denied: {e.message}")
    raise
except gax.ResourceExhausted as e:
    # 429 — quota
    logger.warning(f"Quota exhausted: {e.message}")
    sleep_until_next_hour()
    return retry(request)
except gax.InternalServerError as e:
    # 500 — retry с backoff
    return retry_with_backoff(request)
except gax.ServiceUnavailable as e:
    # 503 — retry
    return retry_with_backoff(request)
```

## Что НЕ делать

- **Не глушить 403 в "no data"** — это сообщает пользователю, что отчёт пустой, тогда как фактически нет доступа
- **Не retry 400** — это deterministic ошибка, дополнительные попытки не помогут
- **Не игнорировать sampling/`(other)`** — продукт принимает решения на этих данных, искажение должно быть прозрачным
- **Не утечь error.message в публичный UI** — может содержать имена property/dimensions, sensitive в multi-tenant среде
