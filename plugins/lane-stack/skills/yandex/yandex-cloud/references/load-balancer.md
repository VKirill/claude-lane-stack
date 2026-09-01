# Load Balancers — ALB (L7) and NLB (L4)

Canonical docs:
- ALB — https://github.com/yandex-cloud/docs/tree/master/ru/application-load-balancer
- NLB — https://github.com/yandex-cloud/docs/tree/master/ru/network-load-balancer

## ALB vs NLB

| | **ALB (Application LB)** | **NLB (Network LB)** |
|---|---|---|
| Layer | L7 (HTTP/1.1, HTTP/2, gRPC, WebSocket) | L4 (TCP, UDP) |
| Path-based routing | ✅ Yes | ❌ No |
| Host-based routing | ✅ Yes | ❌ No |
| TLS termination | ✅ Native with certs from Certificate Manager | ❌ Pass-through only |
| WebSocket | ✅ | ✅ |
| gRPC | ✅ | ✅ (as TCP) |
| Auto-scaling backends | ✅ via target groups | ✅ via target groups |
| Latency overhead | ~ms (more processing) | sub-ms |
| Use for | API gateway, web sites, microservices behind one domain | Database front, raw TCP, max-throughput |

**Rule**: HTTP/HTTPS workload → ALB. Anything else → NLB.

## ALB structure

```
Load balancer (frontend listener:443)
  └── HTTP router (rules: host/path → backend group)
      └── Backend group (named pool)
          └── Targets:
              ├── Target group (Compute VMs / k8s pods, by IP) → with health check
              └── OR static endpoints / direct IPs
```

Health check is required per backend group. Recommended: HTTP GET `/healthz`, 5s interval, 3 unhealthy thresholds.

## ALB quickstart

```bash
# 1. Cert from Certificate Manager (Let's Encrypt or imported)
yc certificate-manager certificate request \
  --name api-cert --domains api.example.com --challenge-type dns

# Wait until status=ISSUED, then DNS-validate per output

# 2. Target group (e.g. VMs in two zones)
yc alb target-group create --name api-tg \
  --target subnet-name=prod-ru-central1-a,address=10.10.0.5 \
  --target subnet-name=prod-ru-central1-b,address=10.10.16.5

# 3. Backend group with HC
yc alb backend-group create --name api-bg \
  --http-backend "name=app,target-group-id=$(yc alb target-group get api-tg --format value),port=8080,healthcheck-port=8080,healthcheck-path=/healthz,healthcheck-interval=5s"

# 4. HTTP router (path → backend)
yc alb http-router create --name api-router
yc alb virtual-host create --name api-vh --router-name api-router \
  --authority "api.example.com"
yc alb http-router-rule create ... # map paths to api-bg

# 5. Load balancer
yc alb load-balancer create --name api-lb \
  --network-name prod-net \
  --location subnet-name=prod-ru-central1-a,zone=ru-central1-a \
  --location subnet-name=prod-ru-central1-b,zone=ru-central1-b \
  --listener "name=https,external-ipv4-endpoint=auto,port=443,tls-cert-id=$(yc certificate-manager certificate get api-cert --format value),http-router-id=$(yc alb http-router get api-router --format value)"
```

## NLB quickstart

```bash
# Target group (VMs)
yc load-balancer target-group create --name pg-tg \
  --region ru-central1 \
  --target subnet-name=prod-ru-central1-a,address=10.10.0.10 \
  --target subnet-name=prod-ru-central1-b,address=10.10.16.10

# NLB with TCP listener
yc load-balancer network-load-balancer create --name pg-nlb \
  --region ru-central1 \
  --listener name=pg,port=5432,target-port=5432,protocol=tcp,external-ipv4-endpoint=auto \
  --attached-target-group "target-group-id=$(yc load-balancer target-group get pg-tg --format value),healthcheck-name=tcp,healthcheck-tcp-port=5432"
```

## Internal vs external

- **External** (`external-ipv4-endpoint=auto`) — public IP, internet-facing
- **Internal** (`internal-ipv4-endpoint=...,subnet-name=...`) — VPC-only; good for service-to-service

## TLS / certs

Two sources:
1. **Yandex Certificate Manager — managed** (free, Let's Encrypt): YC handles renewal. Use this for public domains.
2. **Imported cert** (your own / wildcard from corp CA): you upload + rotate. Use for internal CAs.

Listener can have multiple certs (SNI) — `tls-cert-id=cert1,tls-cert-id=cert2,...`.

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| ALB returns 503 even with healthy backends | Backend group has no `http-router` linked, or HTTP rules don't match host | Verify `yc alb load-balancer get` shows router; check `Host:` header routing |
| Health check fails — target shows UNHEALTHY | Security group on target VMs doesn't allow LB health check IPs | Add ingress for SG of ALB target group |
| NLB 502 on HTTP traffic | Used NLB for HTTP — pass-through can't do app-aware health checks | Switch to ALB OR use TCP HC carefully |
| Cert won't issue | DNS challenge record missing | Add CNAME from cert-manager output to your DNS provider; or `--challenge-type http` |
| `tls handshake failure` | Cert in another folder than ALB | Move cert OR re-issue in ALB's folder |
| WebSocket disconnects every minute | ALB idle timeout default = 60s | Increase listener `idle-timeout` |
