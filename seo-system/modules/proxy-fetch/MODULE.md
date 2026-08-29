# Module: proxy-fetch

## Purpose
Интеграция [proxy6 / px6.net](https://px6.net/ru/developers): в TUI достаточно **API key** → пул активных IP подтягивается через `getproxy` и используется там, где нужен fetch через прокси.

## API
Base: `https://px6.link/api/{key}/{method}/`  
Harness uses **read-only** methods for normal SEO work: `getproxy`, (probe via same).

## Config
| Path | Content |
|---|---|
| `~/secrets/proxy6.env` | `PROXY6_API_KEY=…` |
| `routing.yaml` → `fetch.use_proxy` | on/off for scan/fetch |
| `routing.yaml` → `clustering.use_proxy` | on/off for SERP |
| `~/.agents/seo-services/proxy6-pool.json` | cached pool (1h) |

## TUI
`seodoc` → **Providers** (enter key) or **Proxy** tab → `r` load pool, `t` test, `f` toggle use_proxy.

## Code
- `seo_proxy_lib.py` — pool + `fetch_url`
- `seo_scan_lib.py` — uses proxy when enabled
- `seo-serp-save` — optional proxy for xmlstock
