# Observability — Monitoring, Cloud Logging, Audit Trails

Canonical docs:
- Monitoring — https://github.com/yandex-cloud/docs/tree/master/ru/monitoring
- Cloud Logging — https://github.com/yandex-cloud/docs/tree/master/ru/logging
- Audit Trails — https://github.com/yandex-cloud/docs/tree/master/ru/audit-trails

## Three signals

| Signal | Service | Use |
|---|---|---|
| **Metrics** | Yandex Monitoring | Numeric time-series; dashboards; alerts |
| **Logs** | Cloud Logging | Structured app + infra logs; query, retain |
| **Audit** | Audit Trails | Who did what in YC API (control plane) |

Distributed tracing is not first-class on YC — use Tempo/Jaeger self-hosted on Compute or Managed-K8s.

## Monitoring

### Service-emitted metrics

Every YC service emits metrics into `Monitoring` automatically:
- `Compute` — CPU, RAM, disk, network per instance
- `Managed-PG` / `Managed-Redis` etc. — server-internal metrics
- `ALB` / `NLB` — request rates, codes, latencies
- `Object Storage` — bucket bytes, requests
- `MK8s` — node/pod-level metrics

Browse: console.cloud.yandex/monitoring, or:

```bash
yc monitoring metric list --service compute --resource-type compute_instance
```

### Custom metrics

Push from your app via REST API. Endpoint: `https://monitoring.api.cloud.yandex.net/monitoring/v2/data/write`.

```bash
TOKEN=$(yc iam create-token)
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "https://monitoring.api.cloud.yandex.net/monitoring/v2/data/write?folderId=$YC_FOLDER_ID&service=custom" \
  -d '{
    "metrics": [
      {"name": "orders_completed", "labels": {"env": "prod"}, "type": "COUNTER", "value": 142}
    ]
  }'
```

SDK clients exist for Node/Python/Go.

### Alerts

```bash
yc monitoring alert create \
  --name prod-pg-cpu-high \
  --query 'cpu_utilization{folderId="...", host="c-XXX-pg-1"} > 80' \
  --window 5m \
  --notification-channel-ids ...
```

Notification channels: email, SMS, Telegram, webhook.

## Cloud Logging

### Log groups

A **log group** is a named retention bucket (default folder log group exists). Apps write logs into one or more groups.

```bash
yc logging group create --name app-logs --retention-period 168h
```

Retention: from 1 hour to 31 days (free) or 1 year (paid).

### Writing logs

Three paths:

1. **Agent — Cloud Logging agent (yc-logging-agent)**: install on Compute VM; reads files / journald; ships to a log group. Recommended for VM-based apps.
2. **Fluent Bit / OTel Collector**: same idea, BYO agent. Use existing infrastructure if you have it.
3. **Direct API**: `POST https://ingester.logging.yandexcloud.net/logging/v1/write` with batch of `{ timestamp, level, message, json_payload }`. Use from Functions / Containers (no agent there).
4. **k8s — Cloud Logging Operator**: install Helm chart; collects pod stdout.

### Querying

YC web console has a query language similar to Loki LogQL — filter by group / label, free-text grep, regex.

```
resource_type="serverless.functions.function" AND
resource_id="d4e..." AND
level >= "WARN"
```

CLI:

```bash
yc logging read \
  --group-name app-logs \
  --filter 'level="ERROR" AND json_payload.user_id="42"' \
  --since 1h
```

### What to log (cross-ref `logging-standards-2026` skill)

Always log:
- Request ID / trace ID (correlation)
- User ID for action attribution (not PII content)
- Outbound API calls with duration + status

Never log:
- Tokens, API keys, JWTs
- Full request bodies (may contain credit cards / passwords)
- PII unless redacted at source

## Audit Trails

Control-plane audit (who called which `yc * create / update / delete` API):

```bash
# Set up a trail (one-time): captures events and ships to Cloud Logging or Object Storage
yc audit-trails trail create \
  --name prod-trail \
  --logging-destination-log-group-id $(yc logging group get audit-logs --format value) \
  --filtering-policy management-events-filter='resource-scopes=[{type=resource-manager.folder,id='$YC_FOLDER_ID'}]'
```

Query audit events in Cloud Logging by `event_source` / `event_type` / `authentication.user_id` / `request_metadata.user_agent`.

**Always enable audit trails for prod folders.** Otherwise you cannot trace "who deleted that bucket".

## Cost discipline

| Pitfall | Cost impact |
|---|---|
| Default retention forever | Logs accumulate; bill grows linearly |
| Log every request body | Volume explosion + leaks |
| Custom metric per user (high cardinality) | Monitoring per-series pricing punishes this |
| Audit Trails on too-broad scope | Verbose events |

Tune retention per log group; sample high-volume info logs; aggregate metrics by class not by individual ID.

## Cross-references

- App logging patterns → `logging-standards-2026` skill
- Sentry integration for error tracking → same skill (templates)
- Find anomalies and root cause → `systematic-debugging` skill
- Track who broke prod via audit → audit-trails section above
