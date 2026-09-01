# Managed Service for Kubernetes (MK8s)

Canonical docs: https://github.com/yandex-cloud/docs/tree/master/ru/managed-kubernetes · Public: https://yandex.cloud/ru/docs/managed-kubernetes/

## Concepts

| Term | What |
|---|---|
| **Cluster** | Control plane (master) — managed by YC, HA optional, regional or zonal |
| **Node group** | Pool of worker VMs with identical preset — multiple groups per cluster |
| **Master release channel** | `RAPID` (latest), `REGULAR` (default), `STABLE` (LTS-ish) |
| **CNI** | `CALICO` (default) or `Cilium` |
| **Container Registry** | YC native registry for images; pull via SA |

## Create a cluster

```bash
# Service account for master ops + nodes
yc iam service-account create --name mk8s-master
yc iam service-account create --name mk8s-nodes
yc resource-manager folder add-access-binding $YC_FOLDER_ID \
  --role k8s.clusters.agent --service-account-id $(yc iam sa get mk8s-master --format value)
yc resource-manager folder add-access-binding $YC_FOLDER_ID \
  --role vpc.publicAdmin --service-account-id $(yc iam sa get mk8s-master --format value)
yc resource-manager folder add-access-binding $YC_FOLDER_ID \
  --role container-registry.images.puller --service-account-id $(yc iam sa get mk8s-nodes --format value)

yc managed-kubernetes cluster create \
  --name prod-mk8s \
  --network-name prod-net \
  --master-version 1.31 \
  --zonal zone=ru-central1-a,subnet-name=prod-ru-central1-a \
  --service-account-name mk8s-master \
  --node-service-account-name mk8s-nodes \
  --release-channel REGULAR \
  --public-ip                # master accessible via public endpoint; restrict with master allowlist

# Switch to HA regional (3 master replicas across zones) for prod
#   --regional region=ru-central1,location=zone=ru-central1-a,subnet-name=...,location=...,location=...
```

## Node groups

```bash
yc managed-kubernetes node-group create \
  --name workers-a \
  --cluster-name prod-mk8s \
  --platform standard-v3 \
  --cores 4 --memory 16 \
  --disk-type network-ssd --disk-size 64 \
  --location zone=ru-central1-a,subnet-name=prod-ru-central1-a \
  --auto-scale min=2,max=10,initial=3 \
  --auto-upgrade  --auto-repair
```

For HA: create one node group per zone. The cluster scheduler spreads pods across nodes; pods can fail-over zones if the node group fails.

## Get kubeconfig

```bash
yc managed-kubernetes cluster get-credentials prod-mk8s --external --force
# Writes to ~/.kube/config, context = yc-prod-mk8s
kubectl get nodes
```

`--external` adds the public endpoint; `--internal` only works inside the VPC.

## Networking

- **Pod CIDR** + **Service CIDR** set at cluster creation; cannot change. Pick non-overlapping with VPC and on-prem.
- **Master security group** restricts who can reach the API server (port 443). Set this for prod — don't expose to 0.0.0.0/0.
- **NLB** (Network Load Balancer) for `Service type=LoadBalancer` — provisioned automatically; YC charges per NLB.
- **ALB** (Application Load Balancer) via **ALB Ingress Controller** for L7 routing; install Helm chart.

## ALB Ingress

```bash
# Install controller
helm repo add yc-alb https://yandex-cloud.github.io/alb-ingress-controller
helm install alb-ic yc-alb/yc-alb-ingress-controller -n alb-system --create-namespace \
  --set folderID=$YC_FOLDER_ID

# Ingress resource
cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-ingress
  annotations:
    ingress.alb.yc.io/subnets: <subnet-a-id>,<subnet-b-id>
    ingress.alb.yc.io/security-groups: <sg-id>
    ingress.alb.yc.io/external-ipv4-address: auto
spec:
  ingressClassName: alb
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: api-svc
                port: { number: 80 }
EOF
```

## Container Registry

```bash
yc container registry create --name prod
REG_ID=$(yc container registry get prod --format value --jq .id)

# Push from laptop (uses yc OAuth token)
yc container registry configure-docker
docker tag myapp:v1 cr.yandex/$REG_ID/myapp:v1
docker push cr.yandex/$REG_ID/myapp:v1
```

Cluster nodes pull automatically when their SA has `container-registry.images.puller` on the folder.

## Workload identity (SA in pods)

Instead of mounting SA key files, bind a YC service account to a k8s ServiceAccount via the [federation mechanism](https://yandex.cloud/ru/docs/managed-kubernetes/tutorials/sa-static-key) — pods auto-get IAM tokens. Recommended for new clusters.

## Upgrades

| Strategy | How |
|---|---|
| **Master** | Auto (release channel + maintenance window) OR `yc managed-kubernetes cluster update --master-version 1.31` |
| **Nodes** | Auto with `--auto-upgrade` (recreates nodes in batches) OR manual `node-group update --version 1.31` |
| **Skip-level** | NOT supported — must upgrade one minor at a time (1.29 → 1.30 → 1.31) |

Test upgrades in a non-prod cluster first. Check Deprecated API usage with `kubectl get --raw /metrics | grep apiserver_requested_deprecated_apis`.

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| `ImagePullBackOff` from `cr.yandex/...` | Node SA lacks `images.puller` | Add binding |
| `Service type=LoadBalancer` stuck `<pending>` | Cluster master SA lacks `vpc.publicAdmin` / `loadbalancer.admin` | Add bindings |
| `kubectl` timeout | Public endpoint disabled / SG blocks your IP | `--internal` from a VM in the VPC OR open SG |
| Pod can't reach Managed-PG | SG on PG cluster doesn't allow node subnet | Allow node subnet CIDR or SG reference |
| Autoscaler doesn't add nodes | Quota in folder reached | `yc quota-manager quota get --service compute` |
| Master upgrade stuck | Workload PDB blocks drain | Adjust PodDisruptionBudget; or use `--no-drain` (risky) |

## Cross-references

- VPC for cluster + pod CIDR planning → `vpc-network.md`
- Backing managed-DB connectivity from pods → `managed-databases.md`
- Secrets in pods via Lockbox → `secrets-lockbox.md`
- Container Registry images → see CR section above + `compute.md` cloud-init for pre-pull
