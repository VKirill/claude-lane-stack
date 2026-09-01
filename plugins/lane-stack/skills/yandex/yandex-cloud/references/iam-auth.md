# IAM & Auth

Canonical docs: https://github.com/yandex-cloud/docs/tree/master/ru/iam · Public: https://yandex.cloud/ru/docs/iam/

## Hierarchy

```
Organization                    ← root, federation lives here
└── Cloud(s)                    ← billing unit
    └── Folder(s)               ← IAM scope, quotas, most resources
        └── Resources           ← VMs, buckets, clusters, etc.
```

IAM bindings can attach at any level. **Most-permissive wins** — a `viewer` at folder + `editor` at resource = editor for that resource.

## Identity types

| Type | Use | Auth method |
|---|---|---|
| **Federated user** | Real humans via corporate IdP (SAML/OIDC) | Browser flow, `yc init --federation-id` |
| **Yandex passport user** | Personal Yandex account (dev/dev-org only) | OAuth via `yc init` |
| **Service account** | Automation, VMs, CI, k8s | Static key (JSON) or metadata-server token (on a VM) |

## Roles

Two flavors:

| | Examples | Use |
|---|---|---|
| **Primitive** | `viewer`, `editor`, `admin` | Quick start; over-permissive in prod |
| **Service-specific** | `storage.uploader`, `compute.operator`, `managed-postgresql.editor` | Production — least-privilege |

List all roles: `yc iam role list | grep <service>`. Lookup: `yc iam role get storage.uploader`.

## Service account quickstart

```bash
# Create SA
yc iam service-account create --name app-prod --description "Prod app SA"

# Bind least-privilege roles (folder-level)
yc resource-manager folder add-access-binding $YC_FOLDER_ID \
  --role storage.uploader \
  --service-account-id $(yc iam service-account get app-prod --format value)

yc resource-manager folder add-access-binding $YC_FOLDER_ID \
  --role lockbox.payloadViewer \
  --service-account-id $(yc iam service-account get app-prod --format value)

# Attach to a VM (no static keys needed)
yc compute instance create --service-account-name app-prod ...

# Inside the VM:
TOKEN=$(curl -s -H 'Metadata-Flavor: Google' \
  169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token | jq -r .access_token)
# Use $TOKEN as Bearer for *.api.cloud.yandex.net
```

This is **the** recommended pattern for VMs / k8s pods / serverless — no key files to leak or rotate.

## When you need a key file (no metadata server)

For external CI (GitHub Actions, GitLab Runner outside YC):

```bash
yc iam key create --service-account-name ci-runner -o ci-key.json
# ci-key.json contains: id, service_account_id, created_at, key_algorithm, public_key, private_key (PEM)
# Use with: yc config set service-account-key ci-key.json
```

**Rotate yearly.** Track keys: `yc iam key list --service-account-name ci-runner`.

## OAuth tokens — limited use

`yc init` interactive flow produces a long-lived OAuth token in `~/.config/yandex-cloud/config.yaml`. It's tied to **your user identity**.

- ✅ Personal CLI use
- ❌ Never bake into scripts (loses person → loses access)
- ❌ Never share between people
- ❌ Never put in CI

## Federation (corporate SSO)

For orgs with Active Directory / Keycloak / Okta:

1. Configure federation in YC org admin
2. Map IdP groups → YC groups
3. Users log in via SAML → get Yandex Cloud session
4. `yc init --federation-id <id>` for CLI

Federation tokens expire — `yc` prompts re-auth automatically.

## Common roles cheat sheet

| Role | Grants |
|---|---|
| `viewer` | Read everything (resource list, properties) |
| `editor` | Create/update most things, NOT IAM |
| `admin` | Including IAM — give sparingly |
| `resource-manager.viewer/editor/admin` | Manage folders/clouds |
| `iam.serviceAccounts.user` | Use an SA (attach to VM); does NOT grant SA's roles |
| `iam.serviceAccounts.tokenCreator` | Mint IAM tokens for the SA |
| `compute.operator` | Start/stop VMs, no create/delete |
| `storage.uploader` | Write objects, no list/delete bucket |
| `storage.editor` | Full bucket access |
| `managed-postgresql.editor` | Cluster + DB + users mgmt |
| `lockbox.payloadViewer` | Read secret payloads (NOT versions/metadata) |
| `lockbox.editor` | Full Lockbox |
| `k8s.cluster-api.viewer/editor` | Manage MK8s clusters |
| `monitoring.editor` | Write metrics + dashboards |
| `logging.writer/reader` | Cloud Logging |
| `dns.editor` | Cloud DNS zones |

## IAM token lifecycle

Both metadata-token and `iam create-token` mint **12-hour** bearer tokens. Cache + refresh; never embed in URLs.

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| `Permission denied` for SA despite role | Role bound to wrong folder | Verify with `yc resource-manager folder list-access-bindings $FOLDER_ID` |
| Token expired mid-deploy | 12h IAM token in long script | Refresh before each major step |
| Removed user still authenticated | OAuth token cached locally | Force re-auth: `yc config profile activate <p>` |
| SA accidentally given `admin` | Over-permissive | Replace with service-specific roles; audit via `yc audit-trails` |
| k8s pod can't reach Object Storage | Workload identity not bound | Attach SA to node group OR use workload identity binding |
