# Compute Cloud

Canonical docs: https://github.com/yandex-cloud/docs/tree/master/ru/compute · Public: https://yandex.cloud/ru/docs/compute/

## Concepts

| Term | What |
|---|---|
| **Folder** | Logical group of resources inside a Cloud — billing, IAM, quotas attach here |
| **Zone** | Availability zone — `ru-central1-a`, `ru-central1-b`, `ru-central1-d` (no `-c` after retirement) |
| **Platform** | Hardware family — `standard-v3` (Intel Ice Lake), `standard-v2` (Cascade Lake), `gpu-standard-v3` (NVIDIA), `memory-optimized-v3` |
| **Preset** | CPU + RAM pair — `s3-c2-m4` = standard-v3, 2 vCPU, 4 GB RAM |
| **Image / Disk** | Boot disk created from a public image (Ubuntu 24.04 LTS, Debian 12, etc.) or custom snapshot |
| **Placement group** | Spread / partition placement to avoid single-rack failure |
| **Preemptible** | Cheaper (~70% off) but reclaimable within 24h |
| **Filesystem** | Persistent file storage attached over NFS-like protocol |

## Common operations

### Create VM (Ubuntu 24.04)

```bash
yc compute instance create \
  --name app-1 \
  --zone ru-central1-a \
  --platform standard-v3 \
  --cores 2 --memory 4 --core-fraction 100 \
  --create-boot-disk image-folder-id=standard-images,image-family=ubuntu-2404-lts,size=20,type=network-ssd \
  --network-interface subnet-name=default-ru-central1-a,nat-ip-version=ipv4 \
  --metadata-from-file user-data=cloud-init.yaml,ssh-keys=ssh-keys.txt \
  --service-account-name worker-sa \
  --hostname app-1
```

### Stop / start / delete

```bash
yc compute instance stop  app-1     # billing pauses for compute (disk still billed)
yc compute instance start app-1
yc compute instance delete app-1    # IRREVERSIBLE; confirm with user
```

### Snapshot + restore

```bash
yc compute snapshot create --source-disk-name app-1-boot --name app-1-pre-upgrade
yc compute disk create --source-snapshot-name app-1-pre-upgrade --type network-ssd --size 20
# Then create new VM with --attach-disk-name ...
```

## Disk types

| Type | Use | IOPS guarantee |
|---|---|---|
| `network-hdd` | Cold backup target, dev | Low |
| `network-ssd` | Default app + DB | Good, scales with size |
| `network-ssd-nonreplicated` | High-IOPS need + own replication | Highest, but no internal replication |
| `network-ssd-io-m3` | Mission-critical DB | Latency-optimised tier |

For PostgreSQL on a Compute VM: `network-ssd` 100+GB; for high TPS, `network-ssd-nonreplicated` with WAL-G to Object Storage. Better: use Managed PostgreSQL.

## cloud-init

Bake first-boot config via `--metadata-from-file user-data=cloud-init.yaml`. Example:

```yaml
#cloud-config
users:
  - name: ubuntu
    sudo: ALL=(ALL) NOPASSWD:ALL
    ssh_authorized_keys:
      - ssh-ed25519 AAAA...
package_update: true
package_upgrade: true
packages: [angie, postgresql-client, ufw]
runcmd:
  - ufw default deny incoming
  - ufw allow 22/tcp
  - ufw allow 80,443/tcp
  - ufw --force enable
```

## Service account on VM (recommended)

Attach an SA at create time → inside VM call `169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token` to get a fresh IAM token without storing keys. This is how apps on YC should authenticate to Object Storage / Lockbox / Managed DBs.

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| `yc compute instance create` hangs at "PROVISIONING" | Subnet has no NAT GW / public IP requested but disabled | Add `nat-ip-version=ipv4` or attach NAT GW to route table |
| SSH connection refused after reboot | UFW enabled before allow 22 in cloud-init | Always `ufw allow 22/tcp` BEFORE `ufw --force enable` |
| Preemptible VM gone after 24h | Working as designed | Use non-preemptible for stateful workloads |
| Disk full but `df` shows space free | inode exhaustion (many small files) | `df -i`; clean `/var/log/journal`, old containers |
| VM in zone `ru-central1-c` not creating | Zone retired | Use `-a`, `-b`, or `-d` |

## Cross-references

- VM behind ALB → `load-balancer.md`
- Managed PG instead of self-hosted on VM → `managed-databases.md`
- Secrets fetch from VM via metadata → `secrets-lockbox.md`
- OS-level config inside the VM → `linux-sysadmin` skill
