---
name: yandex-cloud
description: "[RU: Яндекс.Облако — yc CLI, Compute Cloud, Managed PostgreSQL/MySQL/Redis/ClickHouse/MongoDB/Kafka, Object Storage S3, VPC, Managed Kubernetes, IAM, Lockbox, Cloud Functions] Yandex Cloud production operations — yc CLI (canonical control), Compute Cloud (VMs + disks + snapshots + placement groups), Managed Service for PostgreSQL 17 / MySQL 8 / Redis 7 / ClickHouse / MongoDB / Kafka / Greenplum / OpenSearch, Object Storage (S3-compatible), VPC (folders, networks, security groups, NAT GW), Managed Service for Kubernetes 1.31, Application Load Balancer (L7) + Network Load Balancer (L4), Container Registry, Cloud Functions / Serverless Containers, IAM (service accounts, OAuth, federations), Lockbox (secrets), Cloud DNS, Cloud Logging, Monitoring, Backup. Canonical docs: https://github.com/yandex-cloud/docs (mirrored to https://yandex.cloud/ru/docs). Use when: yc CLI, yandex cloud, яндекс облако, yc compute, yc-mdb-pg, mdb-pg, managed postgresql яндекс, managed redis яндекс, ydb, ymq, object storage yc, s3.yandexcloud.net, vpc яндекс, security groups яндекс, yandex k8s, managed kubernetes, container registry, lockbox, service account, IAM token, oauth-token yandex, yc init, yc config profile, terraform yandex provider, миграция на яндекс облако, yc compute instance create, yandex serverless. SKIP: AWS/GCP/Azure (→aws/gcp/azure equivalents); self-managed PostgreSQL on bare metal (→postgresql + linux-sysadmin); Yandex.Cloud-Functions code logic itself (→nodejs/python); Yandex 360 / Yandex Music / consumer products."
stacks:
  - cloud
  - devops
  - sysadmin
tags:
  - yandex-cloud
  - yc
  - cloud
  - iaas
  - paas
category: devops
color: red
displayName: Yandex Cloud
risk: high-stakes
---

<!-- versions:start -->

## 🎯 Version Requirements (May 2026)

**Canonical sources:**
- **Docs repo**: https://github.com/yandex-cloud/docs (markdown source for yandex.cloud/ru/docs)
- **Public mirror**: https://yandex.cloud/ru/docs · https://yandex.cloud/en/docs
- **yc CLI**: latest stable from https://storage.yandexcloud.net/yandexcloud-yc/install.sh (rolling release)
- **Terraform provider**: `yandex-cloud/yandex` v0.115.x+
- **S3 endpoint**: `https://storage.yandexcloud.net` (S3 v4 sig)
- **Cloud API gRPC endpoint**: `*.api.cloud.yandex.net:443`

**Managed service versions (May 2026):**
- Managed PostgreSQL: 14/15/16/**17** (default new clusters)
- Managed MySQL: 5.7/8.0/**8.4**
- Managed Redis: 6.2/7.0/**7.2**
- Managed ClickHouse: latest LTS
- Managed Kubernetes: 1.27 → **1.31** (default)
- Managed Kafka: 3.x

**Always confirm version pins via** `yc managed-postgresql cluster list-hosts` etc. — never assume.

<!-- versions:end -->

## Usage

Loaded automatically when its description matches the active task. Read only the reference section you need — full documentation lives in the canonical repo above (this skill is a navigator, not a copy).

## Use this skill when

- Provisioning, migrating to, or operating workloads on **Yandex Cloud**
- Working with the `yc` CLI: profiles, federations, service accounts, IAM tokens
- Setting up Managed Service for PostgreSQL / MySQL / Redis / ClickHouse / MongoDB / Kafka / Greenplum
- Using Object Storage (S3-compatible) — bucket policy, lifecycle, presigned URLs, CORS
- Designing VPC: folders/clouds, networks, subnets, security groups, NAT gateways, peering
- Managed Service for Kubernetes — node groups, autoscaling, network policies, ALB Ingress
- IAM design — service accounts, roles, federations (SAML/OIDC), OAuth tokens
- Storing credentials in Lockbox; serving secrets to VMs/k8s/serverless via metadata
- Cloud Functions / Serverless Containers / API Gateway / Triggers
- Cost optimisation, billing alerts, committed-use discounts
- Migrating from self-hosted (Ubuntu + PostgreSQL + Redis on a single box) to managed YC services

## Do not use this skill when

- Target cloud is AWS / GCP / Azure / DigitalOcean / Hetzner — use the appropriate skill
- Task is application code that just happens to run on YC — use the framework skill (`nodejs`, `fastapi`, etc.)
- Task is purely about S3 SDK usage with `aws-sdk` against YC Object Storage — use the SDK skill, treat YC as a vanilla S3 endpoint
- Task is self-managed PostgreSQL/Redis on a YC Compute Cloud VM that you administer yourself — use `postgresql` / `redis` / `linux-sysadmin` (this skill covers managed services, not BYOPostgres)

## Purpose

This skill is the **operational map** for Yandex Cloud: which surface to reach for, the canonical control commands (`yc ...`), and the cross-references to the upstream docs at https://github.com/yandex-cloud/docs. It deliberately does NOT duplicate the docs — it routes the agent to the right reference and the right `yc` invocation.

This skill does NOT cover: application logic, language SDKs (defer to the language skill), other clouds. For raw S3 protocol semantics, defer to S3 docs; this skill knows the YC-specific deviations.

## Operating Contract

1. **Always confirm folder + cloud** before any destructive `yc` command — `yc config list` and `yc config get folder-id`
2. **Use `--dry-run` / `--format yaml` first** for any `yc * create` / `update` / `delete` — preview before mutate
3. **Service accounts > OAuth tokens** for automation — never bake `--token <OAuth>` into scripts; use SA + `iam create-token`
4. **Production deletes need confirmation** — `yc compute instance delete`, `yc managed-* cluster delete`, `yc storage bucket remove` are irreversible; ask before running
5. **Backups before schema/version upgrade** — `yc managed-postgresql backup list` + create on-demand before any `cluster update --postgresql-version`
6. **Network changes outside maintenance** trigger downtime — security-group edits + subnet moves; do during a window
7. **Read the docs repo, not stale memory** — paths in https://github.com/yandex-cloud/docs/tree/master/ru change; verify before quoting

## Service Map (canonical surface)

| Layer | Service | yc namespace | Docs path in `yandex-cloud/docs` |
|---|---|---|---|
| **IaaS compute** | Compute Cloud | `yc compute` | `ru/compute/` |
| **IaaS network** | Virtual Private Cloud | `yc vpc` | `ru/vpc/` |
| **PaaS DB** | Managed PostgreSQL | `yc managed-postgresql` | `ru/managed-postgresql/` |
| **PaaS DB** | Managed MySQL | `yc managed-mysql` | `ru/managed-mysql/` |
| **PaaS DB** | Managed Redis | `yc managed-redis` | `ru/managed-redis/` |
| **PaaS DB** | Managed ClickHouse | `yc managed-clickhouse` | `ru/managed-clickhouse/` |
| **PaaS DB** | Managed MongoDB | `yc managed-mongodb` | `ru/managed-mongodb/` |
| **PaaS DB** | Managed Kafka | `yc managed-kafka` | `ru/managed-kafka/` |
| **PaaS DB** | Managed Greenplum | `yc managed-greenplum` | `ru/managed-greenplum/` |
| **PaaS DB** | Managed OpenSearch | `yc managed-opensearch` | `ru/managed-opensearch/` |
| **Serverless** | YDB (Document/Distributed) | `yc ydb` | `ru/ydb/` |
| **Serverless** | Cloud Functions | `yc serverless function` | `ru/functions/` |
| **Serverless** | Serverless Containers | `yc serverless container` | `ru/serverless-containers/` |
| **Serverless** | API Gateway | `yc serverless api-gateway` | `ru/api-gateway/` |
| **Serverless** | Message Queue (SQS-comp) | `yc message-queue` | `ru/message-queue/` |
| **Storage** | Object Storage (S3) | `yc storage` | `ru/storage/` |
| **K8s** | Managed Kubernetes | `yc managed-kubernetes` | `ru/managed-kubernetes/` |
| **Registry** | Container Registry | `yc container registry` | `ru/container-registry/` |
| **LB** | Application LB (L7) | `yc alb` | `ru/application-load-balancer/` |
| **LB** | Network LB (L4) | `yc load-balancer` | `ru/network-load-balancer/` |
| **DNS** | Cloud DNS | `yc dns` | `ru/dns/` |
| **CDN** | CDN | `yc cdn` | `ru/cdn/` |
| **IAM** | IAM | `yc iam` | `ru/iam/` |
| **Secrets** | Lockbox | `yc lockbox` | `ru/lockbox/` |
| **Secrets** | KMS | `yc kms` | `ru/kms/` |
| **Observability** | Monitoring | `yc monitoring` | `ru/monitoring/` |
| **Observability** | Cloud Logging | `yc logging` | `ru/logging/` |
| **Audit** | Audit Trails | `yc audit-trails` | `ru/audit-trails/` |
| **Backup** | Cloud Backup | `yc backup` | `ru/backup/` |
| **Org** | Organization Manager | `yc organization-manager` | `ru/organization/` |

## Response shape

Three sections in every operational response:

- **Plan**: what `yc` calls will run, in order
- **What was done**: bulleted actions taken (with `yc` outputs)
- **Current state**: verification command output (e.g. `yc compute instance get`)
- **Rollback**: how to undo, if applicable (e.g. snapshot + `yc compute instance create` from snapshot)

## Related Skills

### OS layer
- ✓ `linux-sysadmin` — Ubuntu 24.04 inside Compute Cloud VMs; OS-level config, Angie, PM2, UFW

### Backing stores (when self-managed)
- ✓ `postgresql` — query analysis, vacuum, indexes; works the same against Managed PG
- ✓ `redis` — Redis 7 command semantics against Managed Redis

### Network & containers
- ✓ `docker` (cascade) — local builds before `yc container image push`
- ✓ `git` — terraform repo discipline for `yandex-cloud/yandex` provider

### Apps deployed to YC
- ✓ `fastify`, ✓ `hono`, ✓ `nodejs`, ✓ `nextjs`, ✓ `nuxt`, ✓ `astro`, ✓ `fastapi`, ✓ `django`

### Code discipline
- ✓ `karpathy-guidelines`

## API Reference

Domain-specific references (Pattern 2) — load only what's relevant. **All deeper material lives in https://github.com/yandex-cloud/docs** — these references summarize the YC-specific surface and point to the canonical paths.

| Topic | File |
|---|---|
| `yc` CLI — install, profiles, federations, service-account auth, scripting | [references/yc-cli.md](references/yc-cli.md) |
| Compute Cloud — VMs, disks, snapshots, placement groups, preemptible, GPU | [references/compute.md](references/compute.md) |
| Managed databases — PG / MySQL / Redis / ClickHouse / MongoDB / Kafka / Greenplum / OpenSearch | [references/managed-databases.md](references/managed-databases.md) |
| Object Storage — S3 endpoint quirks, bucket policy, lifecycle, presigned URLs, static hosting | [references/object-storage.md](references/object-storage.md) |
| VPC — folders/clouds hierarchy, networks, subnets, security groups, NAT GW, peering, VPN | [references/vpc-network.md](references/vpc-network.md) |
| IAM & auth — service accounts, roles, OAuth, federations, IAM token lifecycle, primitive vs custom roles | [references/iam-auth.md](references/iam-auth.md) |
| Managed Kubernetes — cluster + node groups, autoscaling, ALB Ingress, network policies, container registry pull | [references/kubernetes.md](references/kubernetes.md) |
| Load Balancers — ALB (L7, HTTP/2, gRPC) vs NLB (L4, external/internal), backend groups, health checks | [references/load-balancer.md](references/load-balancer.md) |
| Serverless — Cloud Functions / Serverless Containers / API Gateway / Triggers / Message Queue / YDB serverless | [references/serverless.md](references/serverless.md) |
| Lockbox & KMS — secret payloads, versions, IAM access, mounting in VMs/k8s/serverless | [references/secrets-lockbox.md](references/secrets-lockbox.md) |
| Observability — Cloud Logging, Monitoring custom metrics, Audit Trails, log groups, query language | [references/observability.md](references/observability.md) |
| Migration — from self-hosted (Ubuntu + PG + Redis on Compute VM) to managed services | [references/migration.md](references/migration.md) |

**How to use**: looking up an option for `yc compute instance create` → `compute.md` + canonical docs. Designing IAM model for a new project → `iam-auth.md`. Picking ALB vs NLB → `load-balancer.md`. Migrating prod PG to Managed → `migration.md`.
