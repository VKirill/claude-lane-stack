# yc CLI

Canonical docs: https://github.com/yandex-cloud/docs/tree/master/ru/cli · Public: https://yandex.cloud/ru/docs/cli/

## Install

```bash
curl -sSL https://storage.yandexcloud.net/yandexcloud-yc/install.sh | bash
exec -l $SHELL              # reload PATH
yc version                  # verify
yc components update        # rolling release; update regularly
```

System-wide install for CI/automation: download the static binary from `https://storage.yandexcloud.net/yandexcloud-yc/release/<version>/linux/amd64/yc` and place in `/usr/local/bin/yc`. Pin the version in CI; do not run `components update` in CI containers.

## Auth modes

| Mode | When | How |
|---|---|---|
| **Interactive OAuth** | One-time dev setup | `yc init` → opens browser → token stored in `~/.config/yandex-cloud/config.yaml` |
| **Service account key** | CI/CD, scripts, production | `yc iam key create --service-account-id <id> -o sa-key.json` → `yc config set service-account-key sa-key.json` |
| **IAM token** (short-lived) | API direct, gRPC clients | `yc iam create-token` → 12h Bearer, refresh before expiry |
| **Federated auth (SAML/OIDC)** | Org with corporate IdP | `yc init` with `--federation-id` |
| **Metadata server** (inside VM) | VM with attached SA | No keys — `curl 169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token` |

Production rule: **never** put OAuth tokens in scripts. Always SA key or VM metadata. OAuth tokens have user lifetime; SA keys are revocable per-key.

## Profiles

```bash
yc config profile list
yc config profile create prod
yc config profile activate prod
yc config set cloud-id b1g…  folder-id b1g…  service-account-key ./sa.json
yc config list                            # current profile
```

Tip: per-folder profiles (`profile-staging`, `profile-prod`) prevent cross-folder mistakes — the most common YC outage cause.

## Output formats

| Flag | Output |
|---|---|
| (default) | Pretty table |
| `--format json` | Machine-parseable JSON |
| `--format yaml` | YAML for `yc * update --file` round-trip |
| `--format value` | Bare value (one field, no headers) — for `$(yc … --format value)` |

`--jq '.id'` runs jq on JSON output — built in, no piping needed.

## Common patterns

```bash
# Get folder ID into env
export YC_FOLDER_ID=$(yc config get folder-id)

# Get one field via jq
INSTANCE_ID=$(yc compute instance get my-vm --format json --jq '.id')

# Round-trip edit
yc compute instance get my-vm --format yaml > /tmp/i.yaml
$EDITOR /tmp/i.yaml
yc compute instance update my-vm --file /tmp/i.yaml      # only some fields supported per-resource — check docs

# Wait for async operation
OP=$(yc compute instance create … --async --format value)
yc operation get "$OP"            # poll until done=true
yc wait "$OP"                     # blocks until done
```

## Scripting hygiene

- Always `--async` for long ops in CI, then `yc wait` — prevents 5-min default timeout
- Pin `yc` version: `yc components update --version=<x.y.z>` in the runner image
- For multi-folder admin scripts: pass `--folder-id <id>` explicitly on every call; don't rely on active profile
- Errors print to stderr; check `$?` — `yc` returns non-zero on failure (unlike `aws` v1 sometimes)

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| `permission denied: resource-manager.clouds.list` | Active profile points at wrong cloud | `yc config profile activate <correct>` |
| `Cannot perform request: Federation token expired` | SAML cookie expired | `yc init --federation-id … --no-browser` re-auth |
| `tcp dial tcp [...]:443: i/o timeout` | UFW/proxy blocking `*.api.cloud.yandex.net` | Allow egress 443 to that hostname |
| Slow first call after idle | DNS resolve | Cache nothing — it's normal; ignore |
| Script picks wrong folder | Forgot to activate profile | Use `--folder-id` on every call OR `yc config profile activate` at top of script |
