# proxy6 — Reference index

Slim index. Open the file you actually need; do not load everything.

## Decision map

| You are about to... | Open first |
|---|---|
| Bootstrap a new proxy6 client (Python or Node) | [setup.md](setup.md) → [integration-python.md](integration-python.md) or [integration-node.md](integration-node.md) |
| Call `getprice` / `getcount` / `getproxy` | [methods.md](methods.md) |
| Buy proxies | [purchase-and-billing.md](purchase-and-billing.md) → [methods.md](methods.md) (`buy`) |
| Prolong proxies | [purchase-and-billing.md](purchase-and-billing.md) → [methods.md](methods.md) (`prolong`) |
| Delete proxies | [methods.md](methods.md) (`delete`) → [wrong-vs-right.md](wrong-vs-right.md) (blind-delete pair) |
| Pick `version` (3 / 4 / 5 / 6) | [proxy-versions.md](proxy-versions.md) |
| Hit a 429 / `error_id 100 / 105 / 300 / 400` | [error-codes.md](error-codes.md) → [troubleshooting.md](troubleshooting.md) |
| Tune retry / timeout / rate budget | [recommended-defaults.md](recommended-defaults.md) |
| Manage a long-running pool | [pool-management.md](pool-management.md) |
| Configure IP allowlist (`ipauth`) | [ipauth-strategy.md](ipauth-strategy.md) |
| Audit an existing implementation | [wrong-vs-right.md](wrong-vs-right.md) |

## Files

| File | Purpose | Lines |
|---|---|---|
| [setup.md](setup.md) | API key handling, log scrubbing, IP allowlist, rate-limit overview | small |
| [methods.md](methods.md) | All 10 methods with params, examples | medium |
| [proxy-versions.md](proxy-versions.md) | 3/4/5/6 — which one to use when | small |
| [error-codes.md](error-codes.md) | All 17 error codes + HTTP 429 | small |
| [rate-limit-and-retry.md](rate-limit-and-retry.md) | 3 req/s budget, token bucket, retry config | small |
| [purchase-and-billing.md](purchase-and-billing.md) | Money safety, pre-buy sequence, `auto_prolong` | medium |
| [pool-management.md](pool-management.md) | `descr` tagging, rotation, ban detection, cleanup | medium |
| [ipauth-strategy.md](ipauth-strategy.md) | Full-replace semantics, dev/prod separation | small |
| [integration-python.md](integration-python.md) | httpx + tenacity + pydantic | medium |
| [integration-node.md](integration-node.md) | fetch / axios + p-retry + bottleneck | medium |
| [recommended-defaults.md](recommended-defaults.md) | SSOT for retry / timeout / budgets | small |
| [wrong-vs-right.md](wrong-vs-right.md) | Anti-pattern pairs | medium |
| [troubleshooting.md](troubleshooting.md) | Symptom-indexed failures | medium |
| [eval-cases.md](eval-cases.md) | Routing tests (positive / negative / edge) | small |

## Convention

- "RU proxy" in this skill always means **retail RU proxy provider proxy6.net** — not generic "proxies sold from Russia".
- `version` always refers to the `version` URL/query param (3/4/5/6), never to API version (proxy6 has one stable REST endpoint).
- `descr` is the proxy6-side "comment" field — capped at 50 chars, indexed for `delete` / `setdescr` filters.
