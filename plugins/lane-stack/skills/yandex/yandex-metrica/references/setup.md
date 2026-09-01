# Setup — OAuth, counter_id, scopes

## Base URL and authentication

```
Host: api-metrika.yandex.net
Authorization: OAuth <token>          # official scheme
# also accepted:
Authorization: Bearer <token>
```

Missing header → 401. Invalid / revoked token → 401. A token from a different app with the same scopes works.

## OAuth flow (Implicit — fine for scripts and servers)

1. **Create an app** at https://oauth.yandex.ru/client/new
   - Platform: **Web services** or **For API access / debugging**
   - Redirect URI: `https://oauth.yandex.ru/verification_code` (quick-start: copy the token by hand)
   - Permissions: pick the scopes you need (see below)
2. Note the app's `client_id`.
3. Open in a browser:
   ```
   https://oauth.yandex.ru/authorize?response_type=token&client_id=<CLIENT_ID>
   ```
4. Authenticate → you are redirected to the verification_code URL → copy `access_token` from it.

For production use **Authorization Code flow** (`response_type=code`) with a server-side `code` → `access_token` exchange via `POST https://oauth.yandex.ru/token` with `client_secret`. This yields a refresh token.

## Scopes

| Scope | Allows |
|---|---|
| `metrika:read` | Reporting API, Logs API, read counter settings, list counters |
| `metrika:write` | CRUD on counters / goals / filters / operations / representatives |
| `metrika:expenses` | Expense imports (`expenses/upload`); covered by `metrika:write` |
| `metrika:user_params` | User-params imports; covered by `metrika:write` |
| `metrika:offline_data` | Offline-conversion / CRM imports; covered by `metrika:write` |
| `passport:business` | For Yandex ID Business (org) accounts |

**Rule**: issue the minimum scope. Analytics / dashboards need only `metrika:read`. `metrika:write` only when CRUD is actually required.

## Token storage

- **DO NOT** put the token in a repo, logs, URL query strings, or front-end code
- **DO** keep it in env, a secret manager (Vault / AWS SM / Yandex Lockbox), or encrypted-at-rest in the DB
- Audit log every use: `user_id`, `counter_id`, endpoint, timestamp
- Rotate every 6–12 months; revoke via the Yandex ID account page
- Tokens have **no default TTL** — they live until the user or the app revokes them

## Discovering `counter_id` (the tag ID)

```bash
curl -H "Authorization: OAuth $TOKEN" \
  https://api-metrika.yandex.net/management/v1/counters
```

Response:

```json
{
  "counters": [
    {
      "id": 12345678,
      "name": "My site",
      "site": "example.ru",
      "status": "Active",
      "owner_login": "vasya",
      "permission": "view",
      "pro": false
    }
  ],
  "rows": 1
}
```

- `permission`: `own` / `view` / `edit`
- `pro: true` = Metrika Pro (larger Logs API storage)
- `counter_id` is `id`. Pass as `ids=12345678` to Reporting; embed in the path `/counter/{id}/...` for Logs / Management.

## Multi-counter requests (Reporting only)

`ids=12345678,87654321,11111111` — sums data across counters. Useful for holdings or groups of sites with identical goals. Behavior: SUM across counters, not average.

## First-connection smoke test

```bash
# 1. List counters
curl -sS -H "Authorization: OAuth $TOKEN" \
  "https://api-metrika.yandex.net/management/v1/counters?per_page=5" | jq

# 2. Minimal report — visits yesterday
curl -sS -H "Authorization: OAuth $TOKEN" \
  "https://api-metrika.yandex.net/stat/v1/data?ids=$COUNTER_ID&metrics=ym:s:visits&date1=yesterday&date2=yesterday" | jq '.data[0].metrics'
```

If both return 200 — token / scope / counter_id are wired correctly.

## First-run troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| 401 on every request | `Authorization` header missing / typo | echo the header, ensure `OAuth ` (with trailing space) or `Bearer ` |
| 403 on `/stat/v1/data` | counter_id belongs to someone else / scope is too narrow | `GET /management/v1/counters` to see what is actually visible |
| 403 on `POST /goals` | `metrika:read` without `metrika:write` | reissue token with `metrika:write` |
| 400 `invalid token` | token revoked by the user | reissue via OAuth flow |
| Empty `counters` | token owner has no counters | check which account you authorized as |

## Multi-account / organizations

For Yandex ID Business accounts add `passport:business`. A personal-account token **cannot** see organization counters and vice versa. To see both, the user needs representative rights (`representatives`) granted by the organization.
