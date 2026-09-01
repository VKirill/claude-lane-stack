# Migration — self-hosted to Yandex Cloud managed services

Canonical docs:
- General migration — https://github.com/yandex-cloud/docs/tree/master/ru/datatransfer
- Data Transfer Service — https://github.com/yandex-cloud/docs/tree/master/ru/data-transfer

This reference targets the **current stack of this user**: Ubuntu 24.04 + Angie + PM2 + self-hosted PostgreSQL 18 + Redis 8 on one or two bare-metal / Compute VMs → equivalent on YC managed services.

## Decision tree

```
Self-hosted X today                  →  YC equivalent
─────────────────────────────────────────────────────────
PostgreSQL on Compute VM             →  Managed PostgreSQL  (recommended)
Redis on Compute VM                  →  Managed Redis        (recommended)
Angie reverse proxy on a VM          →  Compute VM with Angie OR ALB (depending on need)
PM2 Node apps on a VM                →  Compute VM (same)    OR Serverless Containers (if stateless)
Static assets on disk                →  Object Storage + CDN
cron jobs on a VM                    →  Stay (cron) OR Cloud Functions + Timer Trigger
Backups on second VM / external      →  Object Storage with lifecycle to cold/ice
```

**Don't migrate everything at once.** Pick the highest-value moves first: data stores (PG, Redis) and static assets (Object Storage). Compute and proxy can stay.

## Phase 1 — Migrate PostgreSQL to Managed-PG

### Pre-flight

- Pin PG version of Managed cluster to the **same major** as source (e.g. source PG 18 → target Managed PG 17 if 18 not yet GA, else 18). Cross-major migration adds complexity.
- Ensure source has `wal_level = logical` and `max_replication_slots ≥ 2`.
- Create a replication user on source: `CREATE ROLE yc_replicator REPLICATION LOGIN PASSWORD '...'`.
- `pg_hba.conf`: allow `yc_replicator` from the YC Data Transfer worker IP (provided in step 3).

### Migration via Data Transfer

```bash
# 1. Create endpoints
yc datatransfer endpoint create source-postgres \
  --name pg-source \
  --postgres-source on-premise=hosts=[<source-ip>],port=5432,user=yc_replicator,password=...,database=appdb,tls-mode=disabled

yc datatransfer endpoint create target-postgres \
  --name pg-target \
  --postgres-target managed-cluster-id=$(yc managed-postgresql cluster get prod-pg --format value),database=appdb,user=admin,password=...

# 2. Create transfer (Snapshot + CDC = zero-downtime cutover)
yc datatransfer transfer create snapshot-and-increment \
  --name pg-migrate \
  --source-id $(yc datatransfer endpoint get pg-source --format value) \
  --target-id $(yc datatransfer endpoint get pg-target --format value)

# 3. Activate
yc datatransfer transfer activate pg-migrate

# 4. Watch
yc datatransfer transfer list-operations --id $(yc datatransfer transfer get pg-migrate --format value)
```

### Cutover

When initial snapshot done + CDC lag stable (< few seconds):

1. Read-only mode on app
2. Wait until last writes replicated (`SELECT * FROM pg_stat_replication` on source)
3. Update app `DATABASE_URL` → Managed-PG FQDN (`c-XXX.rw.mdb.yandexcloud.net`)
4. Restart app
5. Verify writes go to Managed-PG; verify reads return same data
6. `yc datatransfer transfer deactivate pg-migrate`

Rollback plan: keep source DB running for 48h; revert `DATABASE_URL` if issue surfaces.

## Phase 2 — Migrate Redis

Redis has no built-in "live migration". Options:

| Method | When | Downtime |
|---|---|---|
| **Snapshot import** | Cache (data is regeneratable) | Minutes — flush + warm |
| **`MIGRATE` command** (key-by-key) | Small datasets | Seconds-minutes |
| **Redis replication → flip primary** | Persistent state | Seconds |
| **App-level dual-write** | Maximum safety | Days of operation |

For a **cache**: simplest is point app at Managed Redis, accept cold cache, warm it.

For **session store** or other stateful Redis: use Redis replication. Source becomes primary; Managed Redis joins as replica via VPN/peering; promote when ready.

Managed Redis ACL: app user with `~* &* +@all -@dangerous` is a sensible default.

## Phase 3 — Static assets to Object Storage

For a typical site, files end up in:
- `/var/www/uploads/`
- `/var/www/static/`

```bash
# Bulk copy with rclone or aws-cli
aws s3 sync /var/www/uploads/ s3://my-prod-uploads/ \
  --endpoint-url https://storage.yandexcloud.net \
  --storage-class STANDARD

# Update app to use S3 URLs (or signed URLs)
# Set up CDN in front for hot assets
```

Static-only sites: skip even the VM — Object Storage with `--website` flag + CDN serves the whole thing.

## Phase 4 — Compute (optional)

If the app is stateless and traffic is variable:

```
Old: 1 fat VM running PM2 + Angie + all apps
New: ALB → 2 Compute VMs (auto-scale via instance group) running PM2 + Angie
     OR ALB → Serverless Containers (pay-per-request, no PM2)
```

Keep this for last — it's optimization, not foundational. Plenty of YC users run a single Compute VM forever.

## Networking before any of the above

1. Create VPC `prod-net` with 3 zonal subnets
2. NAT GW for outbound from private subnets
3. Security groups: `app-sg`, `db-sg`, `bastion-sg` with least-privilege ingress
4. Bastion VM with SSH allowed only from your office IP
5. Update `~/.ssh/config` with ProxyJump via bastion

## Cost model shift

| Self-hosted bare metal | Managed YC |
|---|---|
| Fixed monthly server fee | Per-resource billing — compute by hour, disk by GB-month, egress by GB |
| Backups manual (cost = your time) | Backups included in Managed services (free retention bands) |
| Patching manual | Automatic on Managed services (during maintenance window) |
| Multi-zone HA costs 2× | Multi-zone HA on Managed = priced normally; do it from day 1 |

Run a cost estimate via [yandex.cloud/ru/prices](https://yandex.cloud/ru/prices) calculator before committing.

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| Data Transfer "permission denied" on source | `pg_hba.conf` doesn't include worker IPs | YC publishes worker IP ranges; add CIDR or `0.0.0.0/0` temporarily |
| Cutover doubles app latency | App now talks to Managed-PG across VPN/peering, more hops | Move app to Compute VM in same VPC as Managed-PG |
| Egress bill spike after migration | App outside YC pulling images / data from inside | Move client into YC or front with CDN |
| Costs higher than expected | Forgot to delete old Compute disks / snapshots | `yc compute disk list` / `snapshot list`; clean unused |
| Backup-restore took hours | Tested too-small disk for restore | Provision restore cluster with ≥ source disk size |

## Cross-references

- VPC design before migration → `vpc-network.md`
- Service accounts for Data Transfer workers → `iam-auth.md`
- DB tuning specifics → `managed-databases.md`
- App SSH and OS-layer config → `linux-sysadmin` skill
