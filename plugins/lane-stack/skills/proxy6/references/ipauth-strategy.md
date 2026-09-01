# ipauth strategy — full-replace semantics, dev/prod separation

`ipauth` binds source IPs to your proxy6 account. After binding, the bound IPs can use the proxies WITHOUT user/pass auth. Other IPs still get user/pass.

## Two different "IP allowlists" — don't confuse them

| Surface | Purpose | Where configured |
|---|---|---|
| **API key allowlist** | Restricts who can CALL the proxy6 API with your key | Dashboard at proxy6.net |
| **`ipauth` allowlist** | Restricts who can USE the rented proxies without password | API method `ipauth` |

This file is about the second. The first is in [setup.md](setup.md).

## When to use ipauth vs user/pass

| Scenario | Use |
|---|---|
| Stable production workers behind fixed egress IP(s) | `ipauth` — no secrets in workers |
| Workers behind dynamic IPs (lambda, residential dev machine) | user/pass |
| Multi-tenant — proxy shared between many services | user/pass — different services may have different IPs |
| Mobile / CI runs | user/pass — IPs change every run |
| Single fleet, single egress NAT | `ipauth` |

Prefer `ipauth` for production worker fleets — strips the credential from the worker, reduces leakage risk if a worker is compromised.

## ⚠️ Full-replace semantics

`ipauth(ip=<csv>)` REPLACES the entire bound-IP list. There is **no add/remove**. Pass the FULL UNION of all IPs that should be bound.

```
Current list:  1.1.1.1, 2.2.2.2, 3.3.3.3
Call:          ipauth(ip="4.4.4.4")
New list:      4.4.4.4
Effect:        1.1.1.1, 2.2.2.2, 3.3.3.3 now require user/pass
```

If those three IPs were running production workers with no password configured, **they instantly stop working**.

### Canonical pattern: always compose the union

```python
async def update_ipauth(client: Proxy6Client, desired: set[str]) -> None:
    """Replace the bound-IP list with `desired` (must be the full union)."""
    csv = ",".join(sorted(desired))
    await client.ipauth(ip=csv)
```

Source `desired` from a single registry (e.g. a YAML file in your infra repo, or a service like Doppler), NOT from per-team patches. Every change goes through the registry.

### Clear all bindings

```
ipauth(ip="delete")
```

This is the only way to fully reset. All proxies revert to user/pass auth. Useful when:
- Decommissioning a worker fleet entirely.
- Recovering from a misconfiguration (cleared the list, going back to passwords).
- Migrating to a new infrastructure layout.

## Dev/prod separation

There is only ONE bound-IP list per api_key. To avoid dev IPs being trusted in prod proxies:

| Option | How |
|---|---|
| **Separate api_keys for dev and prod** (recommended) | Two proxy6 accounts or sub-accounts (if available on tier); never mix |
| **Use user/pass in dev, ipauth in prod** | Dev workers always pass `user`/`pass`; prod has its IP bound and password fields omitted |
| **Never bind dev IPs** | Dev uses user/pass; prod uses ipauth. Dev machines never end up in the bound list. |

The first option (separate keys) is the only way to fully isolate billing and behavior — recommended for any team > 1 person.

## Update workflow

When adding or removing an IP from the bound list:

1. Pull the current registry — `cat infra/proxy6-ipauth-prod.yaml` (or equivalent).
2. Edit: add the new IP, OR remove the old.
3. Diff & review (peer review on the PR — this is high-stakes).
4. Apply: call `ipauth(ip=<full union>)` via your CI / ops script.
5. Verify: spot-check from one of the bound IPs (no password) and one non-bound IP (should require password).

NEVER call `ipauth` from an interactive shell with a single IP unless that IP is **literally the only one that should be bound**.

## Failure modes

### "Workers can't reach any proxy after the deploy"
- Someone called `ipauth` with a partial list and dropped the prod NAT egress IP.
- Restore: call `ipauth(ip=<full prior union>)` from the registry. Re-add the missing IP.
- Postmortem: enforce the "always full union" rule in code review.

### "Bound a wrong IP and now traffic from an attacker is using proxies"
- Immediately: `ipauth(ip="delete")` to revert everything to user/pass.
- Then rotate user/pass credentials by calling `buy` for replacement proxies and `delete` for the compromised ones — proxy6 doesn't expose a per-proxy password rotation API.

### `error_id 105` from ipauth
- One of the IPs in the CSV is malformed (e.g. `1.2.3.` or contains a port). Fix the CSV and retry.

## Observability

Log every `ipauth` call with: caller, timestamp, prior list, new list (diff), reason. Alert on `ipauth` calls outside the standard change window.
