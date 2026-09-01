# Yandex.Webmaster — Site Diagnostics

## Endpoint

```
GET /v4/user/{user-id}/hosts/{host-id}/diagnostics
```

**Response**:

```json
{
  "problems": {
    "DISALLOWED_IN_ROBOTS": {
      "severity": "FATAL",
      "state": "ABSENT",
      "last_state_update": "2024-01-15T10:30:00.000+03:00"
    },
    "NO_SITEMAPS": {
      "severity": "POSSIBLE_PROBLEM",
      "state": "PRESENT",
      "last_state_update": "2024-01-10T08:00:00.000+03:00"
    },
    "NOT_MOBILE_FRIENDLY": {
      "severity": "RECOMMENDATION",
      "state": "ABSENT",
      "last_state_update": "2024-01-14T12:00:00.000+03:00"
    }
  }
}
```

`problems` is a map keyed by problem type → `{severity, state, last_state_update}`.

## Severity (`SiteProblemSeverityEnum`)

| Severity | Meaning | Reaction |
|---|---|---|
| `FATAL` | site broken / inaccessible / forbidden | page the owner immediately |
| `CRITICAL` | major risk (SSL, perf) | alert within the hour |
| `POSSIBLE_PROBLEM` | SEO-affecting issue | planned fix |
| `RECOMMENDATION` | improvement, not blocking | when-have-time |

## State (`ApiSiteProblemState`)

| State | Meaning |
|---|---|
| `PRESENT` | problem **is** on the site now |
| `ABSENT` | problem is **not** present (verified clean) |
| `UNDEFINED` | not enough data to decide |

## Problem types

### FATAL

- `DISALLOWED_IN_ROBOTS` — whole site blocked in `robots.txt`
- `DNS_ERROR` — DNS not responding / not resolving
- `MAIN_PAGE_ERROR` — homepage returns 4xx/5xx
- `THREATS` — malware / phishing / unwanted software detected

### CRITICAL

- `SLOW_AVG_RESPONSE_TIME` — average response time too high
- `SSL_CERTIFICATE_ERROR` — invalid / expired / untrusted certificate
- (more may be added)

### POSSIBLE_PROBLEM

- `NO_SITEMAPS` — no sitemap.xml or Yandex did not find one
- `NO_ROBOTS_TXT` — no robots.txt
- `TOO_MANY_PAGE_DUPLICATES` — many duplicate pages (canonical issue)
- (others — redirect chains, sitemap errors, etc.)

### RECOMMENDATION

- `NOT_MOBILE_FRIENDLY` — site not adaptive
- `FAVICON_PROBLEM` — no favicon
- `NO_METRIKA_COUNTER` — no Yandex.Metrica counter
- (further ranking-related recommendations)

> Verify against current docs: exact problem-type list — Yandex periodically adds or renames. Treat unknown values as `UNKNOWN_PROBLEM` in your enum.

## Alerting usage

```python
async def alert_on_critical(client, host_id):
    diag = await client.diagnostics(host_id)
    problems = diag.get("problems", {})

    fatal_active = [
        ptype for ptype, info in problems.items()
        if info["severity"] == "FATAL" and info["state"] == "PRESENT"
    ]
    critical_active = [
        ptype for ptype, info in problems.items()
        if info["severity"] == "CRITICAL" and info["state"] == "PRESENT"
    ]

    if fatal_active:
        await send_alert(level="critical", problems=fatal_active)
    if critical_active:
        await send_alert(level="warning", problems=critical_active)
```

## Update frequency

`last_state_update` shows when Yandex last verified that problem. **Not real-time** — typical lag is 24-48 h after the actual site change. Do not panic if you fixed `robots.txt` 10 minutes ago and the API still shows `DISALLOWED_IN_ROBOTS: PRESENT`.

## Errors

| HTTP | Code |
|---|---|
| 200 | ok |
| 403 | `INVALID_USER_ID` |
| 404 | `HOST_NOT_VERIFIED` |

## Common mistakes

- **Paging the owner for `severity=RECOMMENDATION`** — not actionable as an incident; use a weekly digest.
- **Ignoring `state=UNDEFINED`** — Yandex could not verify, which often means there is already an access issue. Log it.
- **Cross-checking with `summary`** — `/hosts/{host-id}/summary` also returns `problems_count` by severity but without per-type breakdown. `diagnostics` is the detailed source.
- **Reading `ABSENT` as "checked yesterday"** — read `last_state_update`. For FATAL it is usually fresher.
