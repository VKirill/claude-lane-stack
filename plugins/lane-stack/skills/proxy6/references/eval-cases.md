# proxy6 — Eval cases

v3 format: **user-voice phrasing** (Russian / typos / incomplete wording) + **Expected behavior** column (which sub-files should load, not just "this skill activates").

## Positive — should activate (12)

| User-voice prompt | Expected behavior |
|---|---|
| "купи 10 ipv4 ru через proxy6 на месяц" | Load `purchase-and-billing.md` pre-buy sequence + `methods.md` (`buy`); enforce `getprice` → `getcount` → balance check; cite `descr` requirement |
| "proxy6 выдает error_id 100 что делать" | Load `error-codes.md` (100) + `troubleshooting.md` (key section); check env var, smoke test with curl |
| "почему получаю 105 от proxy6 после деплоя" | Load `troubleshooting.md` (105 / Docker section) + `setup.md` IP allowlist; check egress IP from inside container |
| "сделай ротацию прокси6 на пул из 50 ipv6" | Load `pool-management.md` rotation strategies + `proxy-versions.md` IPv6 caveats; pick sticky vs round-robin based on workload |
| "напиши клиент proxy6 на httpx с retry на 429" | Load `integration-python.md` + `rate-limit-and-retry.md` token bucket + `recommended-defaults.md` retry policy |
| "px6.link клиент в Node.js с TypeScript" | Load `integration-node.md` Bottleneck limiter + `recommended-defaults.md` retry policy + types section |
| "автопродление прокси6 — стоит ли включать?" | Load `purchase-and-billing.md` `auto_prolong` section; default OFF, requires alert + kill-switch; cite `recommended-defaults.md` |
| "удали прокси с descr=test-pool в proxy6" | Load `wrong-vs-right.md` pair 4 (blind delete) + `methods.md` `delete`; require `getproxy(descr=...)` dry-run + `delete(ids=...)` |
| "ipauth proxy6 заменил список и прод отвалился" | Load `troubleshooting.md` (ipauth wipeout) + `ipauth-strategy.md` full-replace semantics; restore from registry, postmortem |
| "при prolong нескольких прокси разной версии нет price_single" | Load `methods.md` `prolong` mixed-version + `troubleshooting.md` (mixed-version section); group by version |
| "почему error_id 300 при покупке proxy6" | Load `error-codes.md` (300) + `purchase-and-billing.md` pre-flight; run `getcount` first |
| "scraping с rotation через proxy6 — 429 шторм" | Load `troubleshooting.md` (429 storm) + `rate-limit-and-retry.md` shared limiter + `wrong-vs-right.md` pair 8 |

## Negative — should NOT activate (10)

| User-voice prompt | Should route to | Why |
|---|---|---|
| "Webshare прокси купить через API" | **webshare** (cascade, not yet active) | Different provider |
| "Mobileproxy API получить новый IP" | **mobileproxy** (cascade, not yet active) | Different provider |
| "Brightdata residential rotating session" | **brightdata** (cascade, not yet active) | Different provider |
| "как настроить httpx через прокси `http://...`" | **httpx** | Using a proxy in HTTP code (post-acquisition), not proxy6 API |
| "node fetch с прокси-агентом socks5" | **nodejs** | HTTP-client config, not provider API |
| "mitmproxy локальный для отладки трафика" | **mitmproxy** (cascade) | Local debugging proxy, not retail provider |
| "nginx forward proxy для офиса" | **linux-sysadmin** | Self-hosted forward proxy |
| "Telegram MTProto auth session string" | **telegram-bot** | MTProto client config, not proxy purchase |
| "Squid setup with ACL" | **linux-sysadmin** | Self-hosted proxy |
| "CORS proxy для фронтенда" | (no skill — anti-pattern) | In-browser CORS bypass, not proxy6 |

## Edge cases — 5

| User-voice prompt | Resolution |
|---|---|
| "купи прокси через proxy6 и сразу скрапни через httpx" | Cross-skill: **proxy6** PRIMARY (load `purchase-and-billing.md` + `methods.md`) + cross-link **httpx** for downstream HTTP-via-proxy usage |
| "сравни proxy6 vs Webshare для scraping RU" | Out of scope for direct purchase — this skill covers proxy6 only. Surface differences (proxy6: per-day pricing, RU-domestic, 3 req/s limit) without claiming Webshare details |
| "интеграция proxy6 в Telegram-боте на grammY для MTProto" | **proxy6** PRIMARY (load `proxy-versions.md` MTproto section + `methods.md` `buy`) + cross-link **telegram-bot** for MTProto client config |
| "Сравни IPv4 dedicated и IPv6 в proxy6 для Google Ads scraping" | **proxy6** primary — load `proxy-versions.md`; recommend IPv4 dedicated for Google (reputation-sensitive), test IPv6 on staging first |
| "хочу пул на 100 прокси с автообновлением и rotation в Python" | **proxy6** primary chain: `purchase-and-billing.md` → `pool-management.md` rotation → `integration-python.md` client + scheduler |

## How to verify (manual)

1. Open a fresh session with this skill loaded.
2. Paste each Positive prompt → confirm:
   - The system reminder lists `proxy6` as an active skill
   - The response references files matching the "Expected behavior" column
   - Specific proxy6 terms appear: `px6.link`, `error_id`, `getprice`, `getcount`, `buy`, `descr`, `ipauth`, `version=3/4/5/6`
3. Paste each Negative prompt → confirm `proxy6` does NOT appear in the routed skill response, and the suggested fallback skill is mentioned.
4. Edge cases: confirm the response calls out the cross-link explicitly ("primary: proxy6, see also: httpx / telegram-bot").

If a prompt routes wrong:
- Negative becoming Positive → tighten the `description` SKIP rules
- Positive becoming Negative → add the missing trigger term to `description` (already includes `proxy6.net`, `px6.link`, `ipauth`, `auto_prolong`, all relevant `error_id` numbers)
- Edge routing only to one skill → enrich Related Skills cross-links

Run after any change to `SKILL.md` description or major reference restructure — that's the regression check.
