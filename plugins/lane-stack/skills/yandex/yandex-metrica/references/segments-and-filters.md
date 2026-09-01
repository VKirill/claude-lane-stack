# Segments and filters DSL

The Reporting API `filters` param is a segment applied to the dataset before aggregation. Functionally equivalent to segments in the Metrika web UI.

## Operators

### Comparison

| Operator | Effect | Example |
|---|---|---|
| `==` | Exact equality | `ym:s:deviceCategory=='mobile'` |
| `!=` | Inequality | `ym:s:lastTrafficSource!='direct'` |
| `>`, `<`, `>=`, `<=` | Numeric comparison | `ym:s:pageViews>3` |

### String

| Operator | Effect | Example |
|---|---|---|
| `=@` | Substring match | `ym:pv:URL=@'product'` |
| `!@` | Not-substring | `ym:pv:URL!@'admin'` |
| `=~` | Regex match | `ym:pv:URL=~'^/blog/\\d+'` |
| `!~` | Regex no-match | `ym:pv:URL!~'\\.(jpg\|png)$'` |
| `=*` | Glob with `*` (wildcard substring) | `ym:pv:URL=*'*?utm_source=*'` |

### Null / IN

| Operator | Effect | Example |
|---|---|---|
| `=n` | Value is null / undefined | `ym:s:UTMSource=n` |
| `=N` | Value is not null | `ym:s:UTMSource=N` |
| `IN(...)` | In the value list (up to 100) | `ym:s:regionCity IN('Moscow','Saint Petersburg','Kazan')` |
| `NOT IN(...)` | Not in the list | `ym:s:browser NOT IN('Bot','Spider')` |

### Boolean

| Operator | Effect |
|---|---|
| `AND` | Conjunction (may be omitted; AND is the default) |
| `OR` | Disjunction |
| `NOT` | Negation |
| `(...)` | Grouping |

Precedence: `NOT` > `AND` > `OR`. Use parentheses explicitly.

## Cross-namespace via `EXISTS()`

To filter a `ym:s:` report by sessions that include a specific page view (`ym:pv:`):

```
EXISTS(ym:pv:URL=='https://example.com/landing')
```

`EXISTS(...)` means "there exists a hit/visit/event matching the inner condition". Without it, dimensions/metrics from different namespaces cannot coexist in the same filter.

## Filter expression examples

### 1. Organic traffic from Moscow only

```
ym:s:lastTrafficSource=='organic' AND ym:s:regionCity=='Moscow'
```

### 2. Mobile traffic, excluding old browser versions

```
ym:s:deviceCategory=='mobile' AND ym:s:browserMajorVersion>=100
```

### 3. Sessions that viewed any /blog/* page

```
EXISTS(ym:pv:URL=@'/blog/')
```

### 4. Sessions with goal 12345 OR 67890 from VK ads

```
(ym:s:UTMSource=='vk' OR ym:s:UTMSource=='vk_ads') AND (ym:s:goal12345IsReached=='Yes' OR ym:s:goal67890IsReached=='Yes')
```

### 5. Purchases over 5000 RUB, not refunded

```
EXISTS(ym:ev:eventType=='purchase' AND ym:ev:eventRevenue>5000) AND NOT EXISTS(ym:ev:eventType=='refund')
```

### 6. Visit length > 30 s, not a bounce, referrer from a given host

```
ym:s:visitDuration>30 AND ym:s:bounce=='No' AND ym:s:referer=@'.google.'
```

### 7. UTM campaigns by list

```
ym:s:UTMCampaign IN('spring_sale_2026','summer_sale_2026','autumn_sale_2026')
```

## Quoting and escaping

- String literals are in single quotes: `'value'`
- Inside strings: `\'` for apostrophe, `\\` for backslash
- Numbers are bare: `>3`, `==1`
- Boolean-like enum: `'Yes'` / `'No'` for `*IsReached` fields (these are **strings**, not bools)
- Regex with backslashes — double-escape: `=~'\\d+'`

## URL encoding

The `filters` param lives in the query string and must be URL-encoded. Most HTTP clients do this automatically. By hand:

- `'` → `%27`
- ` ` → `%20`
- `(` `)` → `%28` `%29`
- `==` → `%3D%3D`
- commas inside `IN()` — keep as `%2C`

## `filters` limits

| Limit | Value |
|---|---|
| Unique dimensions/metrics inside `filters` | up to 10 |
| Conditions between AND/OR | up to 20 |
| Expression length | up to 10 000 chars |
| Values in a single `IN(...)` / `NOT IN(...)` | up to 100 |

Exceeding → 400 with a clear message.

## `filters` vs persistent segment

- **`filters` param** = one-shot, transient. Lives only for that single request.
- **Persistent segment** = created via Management API:
  ```
  POST /management/v1/counter/{id}/segments
  ```
  Bound to a counter, has `name` and `expression`. Once created, it is referenced by `segment_id` and visible in the web UI. In Reporting API access it via `filters=ym:s:visit_segment==<segment_id>` or dedicated params.

For ad-hoc reports — `filters`. For reuse — create a segment via Management API.

## Performance

- The more complex the filter, the slower the response and the heavier the sampling at default `accuracy=medium`
- `=~` (regex) is costlier than `=@` (substring) and much costlier than `==`
- `EXISTS()` is costlier than a flat filter inside the same namespace
- `IN(100 values)` ≈ 100 separate `==` joined by `OR`

For heavy filters: `accuracy=full` and accept slower responses, or create a persistent segment via Management API (it is indexed server-side).
