# Serverless — Functions, Containers, API Gateway, Triggers, Queue, YDB

Canonical docs:
- Cloud Functions — https://github.com/yandex-cloud/docs/tree/master/ru/functions
- Serverless Containers — https://github.com/yandex-cloud/docs/tree/master/ru/serverless-containers
- API Gateway — https://github.com/yandex-cloud/docs/tree/master/ru/api-gateway
- Message Queue (SQS-comp) — https://github.com/yandex-cloud/docs/tree/master/ru/message-queue
- YDB — https://github.com/yandex-cloud/docs/tree/master/ru/ydb

## Cloud Functions

Stateless function-as-a-service. Runtimes: Node.js 22, Python 3.12, Go 1.23, Java 21, .NET 8, PHP 8.3, Bash, Custom (Docker-based).

```bash
# Package + deploy
zip -r fn.zip index.js package.json

yc serverless function create --name api-fn
yc serverless function version create \
  --function-name api-fn \
  --runtime nodejs22 \
  --entrypoint index.handler \
  --memory 128m --execution-timeout 10s \
  --source-path fn.zip \
  --service-account-name fn-sa \
  --environment NODE_ENV=production,LOCKBOX_SECRET_ID=$(yc lockbox secret get app --format value --jq .id)
```

Limits per invocation: 4 GB RAM, 15 min runtime, 25 MB payload.

Cold start: ~100-500 ms for Node/Python, more for JVM. For latency-critical, use **provisioned instances** or migrate to Serverless Containers + min-instances.

## Serverless Containers

Same model but you bring an OCI image; better for big deps or non-listed runtimes.

```bash
yc serverless container create --name app-svc
yc serverless container revision deploy \
  --container-name app-svc \
  --image cr.yandex/$REG/app:v1 \
  --memory 512m --cores 1 --concurrency 16 \
  --execution-timeout 30s \
  --service-account-name fn-sa \
  --min-instances 1                     # prevents cold start
```

Container must listen on `$PORT` (default 8080) and respond to HTTP. Health check optional.

## API Gateway (OpenAPI-driven)

Route HTTP requests to Functions / Containers / Object Storage / external URLs with one OpenAPI spec:

```yaml
openapi: 3.0.0
info: { title: api, version: 1.0.0 }
paths:
  /users/{id}:
    get:
      parameters: [{ name: id, in: path, required: true, schema: { type: string } }]
      x-yc-apigateway-integration:
        type: cloud_functions
        function_id: d4e...
        service_account_id: aje...
```

```bash
yc serverless api-gateway create --name api-gw --spec spec.yaml
# Returns default domain like d5d...apigw.yandexcloud.net
```

Attach custom domain → Certificate Manager cert → public HTTPS.

## Message Queue (SQS-compatible)

Drop-in SQS replacement. Use `aws-sdk` with `endpoint: https://message-queue.api.cloud.yandex.net`. Auth via S3-style static keys from service account.

```bash
yc message-queue queue create --name jobs.fifo --is-fifo --content-based-deduplication
```

Visibility timeout, dead-letter queues, FIFO ordering, batch send/receive — same as SQS.

## Triggers (event-driven invocation)

Wire events to Functions/Containers/Queue:

| Source | Examples |
|---|---|
| `yc serverless trigger create timer` | Cron-style |
| `yc serverless trigger create message-queue` | Drain a queue into a function |
| `yc serverless trigger create iot-message` | IoT Core message → fn |
| `yc serverless trigger create object-storage` | S3 ObjectCreated → fn |
| `yc serverless trigger create logging` | Cloud Logging group has new record → fn |
| `yc serverless trigger create cloud-logs` | Audit Trails event → fn |
| `yc serverless trigger create container-registry` | New image pushed → fn |
| `yc serverless trigger create yds` | Yandex Data Streams record → fn |

## YDB (Yandex Database)

Two modes:
- **Serverless**: pay per RU/s + storage; auto-scale; perfect for variable load
- **Dedicated**: rented nodes; predictable cost

Strongly consistent, distributed, supports SQL (subset of ANSI) + key-value. Drivers: Node, Python, Go, Java, .NET.

```bash
yc ydb database create --name app-db --serverless
# Get connection endpoint
yc ydb database get app-db --format json --jq .endpoint
```

Use for: session store, event log, metadata. Don't use for: complex JOINs (use Managed PG), full-text (use OpenSearch).

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| Function timeout on first call after deploy | Cold start + dep init | Bigger memory (faster CPU), min-instances, or lighter deps |
| Function can't read Object Storage | SA missing `storage.viewer` | Add binding |
| API Gateway: 401 on every request | Default auth blocks unauth requests | Either add `x-yc-apigateway-authorizer: { type: none }` to operation OR provide JWT |
| Message Queue: messages disappear | Visibility timeout < processing time | Increase visibility; or use FIFO with deduplication |
| YDB query slow | No primary key prefix scan | Design key to match access pattern; YDB is key-ordered |
| Trigger doesn't fire | SA missing role on source (e.g. `storage.viewer` for S3 trigger) | Add binding |

## Cross-references

- Function/Container uses Lockbox secrets → `secrets-lockbox.md`
- API Gateway domain via cert → `load-balancer.md` (Certificate Manager part)
- Function logs go to Cloud Logging → `observability.md`
