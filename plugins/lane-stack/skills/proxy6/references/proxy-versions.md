# Proxy versions — 3 / 4 / 5 / 6

proxy6.net sells four products under one API. The `version` parameter selects which one.

## Quick selector

| Workload | Recommended version |
|---|---|
| Cheap general scraping where target doesn't blacklist shared IPs | `3` IPv4 Shared |
| Dedicated IP for ad ops / sensitive automation | `4` IPv4 |
| Telegram client traffic only | `5` MTproto |
| Modern IPv6-only or IPv6-aware targets (some Google APIs, dual-stack sites) | `6` IPv6 |

## The four versions

### `version=3` — IPv4 Shared

- Pool of IPv4 addresses **shared with other proxy6 customers**.
- Cheapest tier.
- Burnout risk: shared usage means other customers can flag the IP on the target before you start.
- Good for: bulk price scraping, public data, RSS / open APIs.
- Bad for: account-tied automation, ad creation accounts, anti-bot-heavy sites.

### `version=4` — IPv4 Dedicated

- One IPv4 address rented to one customer for the period.
- Higher price than Shared.
- Predictable reputation — only your traffic on it.
- Standard pick for: account-tied workflows, social media automation, ad operations, anything where the target site fingerprints by IP.
- Caveat: still on consumer / datacenter ranges depending on country mix; not residential.

### `version=5` — MTproto

- Telegram-specific proxy flavour (MTproto protocol).
- Not usable for generic HTTP/SOCKS traffic.
- Used by Telegram clients to route MTproto traffic — e.g. for unblocking in restricted networks or for botnet-like operations.
- Pricing tier different from IPv4 — see `getprice(version=5)`.

### `version=6` — IPv6

- IPv6 address.
- Cheaper than IPv4 Dedicated because IPv6 supply is abundant.
- Works only against IPv6-aware destinations. Many older sites are IPv4-only and will reject IPv6 connections.
- Test your target before bulk-buying IPv6 — use `check` after `buy` and a real HEAD through the proxy.
- Common use: scraping Google / Yandex / Cloudflare dual-stack targets where IPv6 is cheaper and equally accepted.

## Protocol support

All versions support **HTTP** and **SOCKS** (and an `auto` mode that listens on a port that accepts either). MTproto (`version=5`) is its own protocol family.

Set `type` on `buy` to control:
- `type=http` — HTTP/HTTPS only.
- `type=socks` — SOCKS5 only.
- `type=auto` — both on the same port (slightly higher overhead).

## Pricing structure

`getprice` returns:
- `price_single` — per proxy per day in account currency.
- `price` — total.

Tiered: longer `period` → lower `price_single`. Larger `count` → small volume discount on some tiers.

Always call `getprice(count, period, version)` immediately before `buy` — published prices on proxy6.net website can lag the API.

## Country availability

Different countries stock different versions. `getcountry(version=4)` and `getcountry(version=6)` will return DIFFERENT lists. Always check before buying — buying IPv6 for a country that doesn't stock it returns `error_id 220` or `error_id 300`.

## When to mix versions

Mix versions in the same `descr` pool only if your scraper handles both transparently. Reasons NOT to mix:
- `prolong` on mixed `ids` returns no `price_single` — accounting harder.
- Rotation logic must understand version to pick the right `host`/`ip` field (IPv4 uses `host`, IPv6 uses `ip`).
- Ban detection per-IP is the same, but reputation differs by version.

Default: one `descr` tag = one version + one country.
