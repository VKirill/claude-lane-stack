# Managed Databases

Canonical docs (per service):
- PostgreSQL — https://github.com/yandex-cloud/docs/tree/master/ru/managed-postgresql
- MySQL — https://github.com/yandex-cloud/docs/tree/master/ru/managed-mysql
- Redis — https://github.com/yandex-cloud/docs/tree/master/ru/managed-redis
- ClickHouse — https://github.com/yandex-cloud/docs/tree/master/ru/managed-clickhouse
- MongoDB — https://github.com/yandex-cloud/docs/tree/master/ru/managed-mongodb
- Kafka — https://github.com/yandex-cloud/docs/tree/master/ru/managed-kafka
- Greenplum — https://github.com/yandex-cloud/docs/tree/master/ru/managed-greenplum
- OpenSearch — https://github.com/yandex-cloud/docs/tree/master/ru/managed-opensearch

## Common pattern

Every managed cluster has the same shape:

1. **Cluster** — top-level entity, owns network + IAM + backup policy
2. **Hosts** — N replicas across zones, one is primary (PG/MySQL/Mongo) or all equal (Redis cluster / ClickHouse shards)
3. **Databases + Users** — created inside the cluster
4. **Connection** — via private FQDN like `c-<cluster-id>.rw.mdb.yandexcloud.net` (read-write) or `.ro.` (replica)
5. **Maintenance window** — weekly slot where YC patches; default anytime, set explicit for prod

## Managed PostgreSQL — quickstart

```bash
yc managed-postgresql cluster create \
  --name prod-pg \
  --environment production \
  --network-name default \
  --host zone-id=ru-central1-a,subnet-name=default-ru-central1-a,assign-public-ip=false \
  --host zone-id=ru-central1-b,subnet-name=default-ru-central1-b,assign-public-ip=false \
  --resource-preset s3-c2-m8 \
  --disk-type network-ssd --disk-size 100 \
  --postgresql-version 17 \
  --user name=app,password=$(openssl rand -base64 32) \
  --database name=appdb,owner=app \
  --backup-window-start hours=2,minutes=0 \
  --security-group-ids enz...

# Get connection FQDN
yc managed-postgresql host list --cluster-name prod-pg

# Connect (from inside YC network or VPN)
psql "host=c-CLUSTER.rw.mdb.yandexcloud.net port=6432 \
      sslmode=verify-full sslrootcert=/etc/ssl/certs/YandexInternalRootCA.crt \
      dbname=appdb user=app"
```

## Connection-pool quirk

Each Managed PG cluster ships with **Odyssey** connection pooler in front (port 6432). App connections go to Odyssey, not directly to Postgres. Implications:

- `pg_stat_activity` shows pooler sessions, not app sessions
- Long-running prepared statements need `pool_mode = session` in pool params (default is `transaction`)
- Set application pool to lower count than Odyssey limit — chain pool sizes correctly

## Backup

| Type | When | How to restore |
|---|---|---|
| **Automatic** | Daily during backup window, retained 7 days (free) or 30/90 days (paid) | `yc managed-postgresql cluster restore --backup-id <id> --name prod-pg-restored ...` (NEW cluster, can't in-place) |
| **Manual / on-demand** | Before risky change | `yc managed-postgresql cluster backup --name prod-pg` |
| **WAL-archive PITR** | Continuous | Restore to any point within retention window |

**Rule**: always `yc managed-postgresql cluster backup` BEFORE version upgrade / config change. Restore is to a NEW cluster — plan downtime accordingly.

## Connection from outside YC

Managed clusters default to **private FQDN only**. To connect from your laptop:

1. **VPN to YC** — recommended; use `yc-bastion` or WireGuard on a Compute VM in the same VPC
2. **Public IP** — set `assign-public-ip=true` per host; security group must allow your IP; expensive on egress
3. **Bastion VM** — `ssh -L 6432:c-XXX.rw.mdb.yandexcloud.net:6432 user@bastion`; safe + simple

Never expose Managed PG/Redis to 0.0.0.0/0 — even with strong passwords; security groups should default-deny.

## Managed Redis quirks

- No `CONFIG SET` for some keys — done via cluster `update --config`
- Sentinel/cluster mode is exposed; pick at cluster creation
- `maxmemory-policy` configurable; `noeviction` (default) blocks writes when full — set to `allkeys-lru` for cache-like
- TLS: `--config tls-port=6379,port=0` to force-TLS only

## Managed ClickHouse — shards + replicas

Two-dimensional: shard (data partitioning) × replica (HA). For most projects: 1 shard, 2-3 replicas. Multi-shard only for >TB-scale.

```bash
yc managed-clickhouse cluster create ... \
  --shard-name shard1 \
  --host type=clickhouse,zone-id=ru-central1-a,shard-name=shard1 \
  --host type=clickhouse,zone-id=ru-central1-b,shard-name=shard1 \
  --host type=zookeeper,zone-id=ru-central1-a \
  --host type=zookeeper,zone-id=ru-central1-b \
  --host type=zookeeper,zone-id=ru-central1-d
```

ZooKeeper hosts are mandatory for >1 replica per shard.

## Pricing watch-outs

- **Disk** billed continuously even when cluster `STOPPED`
- **Public IP** + **egress** can dwarf compute cost in chatty workloads
- **Backup over 7 days** is paid per GB
- **Connection pool sessions** count toward host's `max_connections` quota; oversizing app pool = cluster runs out

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| `FATAL: no pg_hba.conf entry` | User exists but doesn't have access to the DB | `yc managed-postgresql user grant-permission --cluster-name X --user-name app --database-name appdb` |
| Slow query suddenly slower after upgrade | Plan regression after PG version bump | Check `pg_stat_statements`, possibly `ANALYZE`, fall back to prior version via restore |
| Replica lag growing | Network or long write txn on primary | `pg_stat_replication`; check long-running queries; consider larger preset |
| Connection rejected `host=...rw.mdb.yandexcloud.net` from VM | Security group on VM doesn't allow egress; or DB SG doesn't allow VM's subnet | Open both SGs |
| Redis cluster: `MOVED` reply confusing client | App not configured for cluster mode | Use `redis-cli -c` or ioredis cluster mode |
