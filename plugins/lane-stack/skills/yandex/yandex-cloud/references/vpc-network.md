# VPC — Virtual Private Cloud

Canonical docs: https://github.com/yandex-cloud/docs/tree/master/ru/vpc · Public: https://yandex.cloud/ru/docs/vpc/

## Hierarchy

```
Cloud (billing root)
└── Folder              (IAM + quotas scope)
    ├── Networks        (private overlay; multiple subnets across zones)
    │   └── Subnets     (CIDR per zone)
    ├── Security groups (stateful firewall)
    ├── Route tables    (custom routes — NAT GW, peering)
    └── Compute / Managed-DB / k8s resources
```

A **Network** spans zones; **Subnets** are zonal. Resources pick a subnet at create time → that fixes their zone.

## Default network

Auto-created on cloud bootstrap: one network named `default`, one subnet per zone (`default-ru-central1-a`, etc.) with CIDR `10.128.0.0/24`, `10.129.0.0/24`, etc. Fine for dev — replace for prod.

## Plan your CIDR

Pick **non-overlapping** with on-prem (for VPN) and AWS/GCP peering. Example:

| Network | Zone | Subnet CIDR |
|---|---|---|
| `prod-net` | `ru-central1-a` | `10.10.0.0/20` |
| `prod-net` | `ru-central1-b` | `10.10.16.0/20` |
| `prod-net` | `ru-central1-d` | `10.10.32.0/20` |

Don't oversize subnets — once created, CIDR cannot expand.

## Security groups (stateful firewall)

Default-deny ingress, default-allow egress. Attach to: Compute VMs, Managed-DB hosts, ALB, NLB targets, k8s nodes.

```bash
yc vpc security-group create \
  --name app-sg --network-name prod-net \
  --rule "direction=ingress,port=443,protocol=tcp,v4-cidrs=[0.0.0.0/0]" \
  --rule "direction=ingress,port=22,protocol=tcp,v4-cidrs=[YOUR_OFFICE_IP/32]" \
  --rule "direction=egress,from-port=0,to-port=65535,protocol=any,v4-cidrs=[0.0.0.0/0]"
```

**Production rule**: no port 22 from `0.0.0.0/0`. Office IP or bastion only.

For inter-service traffic, allow by SG reference (not CIDR):

```bash
yc vpc security-group update-rules app-sg \
  --add-rule "direction=ingress,port=5432,protocol=tcp,security-group-id=$(yc vpc security-group get db-sg --format value)"
```

This means "anything in `db-sg` can talk to me on 5432" — survives IP changes.

## NAT gateway

For private subnets that need egress to internet (e.g. `apt update`) without public IPs on each VM:

```bash
yc vpc gateway create --name natgw --shared-egress-gateway-config ""
yc vpc route-table create --name prod-rt --network-name prod-net \
  --route "destination=0.0.0.0/0,gateway-id=$(yc vpc gateway get natgw --format value)"
yc vpc subnet update default-ru-central1-a --route-table-name prod-rt
```

After this, VMs in that subnet without public IPs can still `curl` outside. Egress billed.

## Peering & connectivity

| Need | Tool |
|---|---|
| Two YC networks in same/diff cloud | **Yandex Cloud Interconnect** (paid, BGP) or NAT VM bridge |
| YC ↔ on-prem | **Cloud Interconnect** (direct) or **VPN gateway** (IPsec) |
| YC ↔ AWS/GCP | VPN gateway (IPsec) via partner |

For most projects: skip; design within one network.

## Private DNS

`yc dns` provides private zones — internal services resolve `db.prod.internal` to private IPs within VPC, never publicly. Use this instead of hardcoding Managed-DB FQDNs.

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| VM has no internet | No NAT GW and no public IP | Either add NAT GW + custom route OR `assign-public-ip=true` |
| Managed-PG unreachable from VM | Different network OR security groups don't permit | Same network; SG ingress from VM SG |
| Subnet CIDR conflict on peering | Overlapping with peer | Re-plan; create new subnets in non-conflicting range |
| `getaddrinfo ENOTFOUND <fqdn>` from VM | DNS not configured for private zone | `resolv.conf` should point at `169.254.169.254` (default cloud-init handles this) |
| Security-group rule edit caused outage | Forgot egress rule when default-changed | Always test SG via `nc -zv host port` from another VM first |

## Cross-references

- VMs go in subnets → `compute.md`
- Managed-DB hosts pick subnets at create → `managed-databases.md`
- ALB / NLB use SGs + subnets → `load-balancer.md`
- k8s clusters span subnets across zones → `kubernetes.md`
