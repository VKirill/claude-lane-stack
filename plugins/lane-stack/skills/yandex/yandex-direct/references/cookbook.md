# Yandex Direct API — Cookbook

Practical recipes for `yandex_direct_api` (the generic MCP gateway). Each recipe shows the exact call shape. All calls go through:

```
yandex_direct_api({
  endpoint: "/json/v5/<service>",
  method:   "POST",
  body:     { ... }
})
```

---

## Auth & headers

### Recipe 1 — Bearer auth for a direct advertiser

```
yandex_direct_api({
  endpoint: "/json/v5/clients",
  method: "POST",
  body: {
    method: "get",
    params: {
      FieldNames: ["Login", "ClientId", "Currency", "Restrictions"]
    }
  }
})
```

The gateway injects `Authorization: Bearer <token>` from the configured account. No manual header needed.

### Recipe 2 — Client-Login for agency access

Pass `clientLogin` (or `account`) in the tool options so the gateway adds `Client-Login: <login>` and routes to the correct sub-account. Without it, the call runs against the agency account.

```
yandex_direct_api({
  endpoint: "/json/v5/campaigns",
  method:   "POST",
  clientLogin: "client-login-here",
  body: {
    method: "get",
    params: {
      SelectionCriteria: {},
      FieldNames: ["Id", "Name", "State", "Status"]
    }
  }
})
```

After the call, check `Units-Used-Login` in the response headers. It must match the client, not the agency.

### Recipe 3 — Sandbox vs production

The gateway reads `DIRECT_USE_SANDBOX=true` from the environment:

- `true` → calls go to `api-sandbox.direct.yandex.com`
- absent / `false` → `api.direct.yandex.com`

Same OAuth token works on both. Sandbox data is isolated and synthetic; no real spend.

---

## Campaigns

### Recipe 4 — List campaigns (all active)

```
yandex_direct_api({
  endpoint: "/json/v5/campaigns",
  method:   "POST",
  body: {
    method: "get",
    params: {
      SelectionCriteria: {
        States: ["ON", "SUSPENDED", "OFF"],
        Statuses: ["ACCEPTED"]
      },
      FieldNames: ["Id", "Name", "Type", "Status", "State", "DailyBudget", "StartDate"],
      Page: { Limit: 100, Offset: 0 }
    }
  }
})
```

If the response contains `LimitedBy`, use it as the next `Offset` to page.

### Recipe 5 — Create a text campaign (search only)

```
yandex_direct_api({
  endpoint: "/json/v5/campaigns",
  method:   "POST",
  body: {
    method: "add",
    params: {
      Campaigns: [{
        Name: "Search RU — widgety",
        StartDate: "2026-06-01",
        TextCampaign: {
          BiddingStrategy: {
            Search: {
              BiddingStrategyType: "WB_MAXIMUM_CLICKS",
              WbMaximumClicks: {
                WeeklySpendLimit: 7000000000,
                BidCeiling: 300000000
              }
            },
            Network: { BiddingStrategyType: "SERVING_OFF" }
          }
        }
      }]
    }
  }
})
```

Money fields are in micro-currency (rubles × 1 000 000). `7000000000` = 7 000 ₽/week.
Iterate `result.AddResults[]` — each element is either `{ Id: N }` or `{ Errors: [...] }`.

### Recipe 6 — Suspend / resume / archive a campaign

```
// Suspend
yandex_direct_api({
  endpoint: "/json/v5/campaigns",
  method:   "POST",
  body: { method: "suspend", params: { SelectionCriteria: { Ids: [12345] } } }
})

// Resume
yandex_direct_api({
  endpoint: "/json/v5/campaigns",
  method:   "POST",
  body: { method: "resume", params: { SelectionCriteria: { Ids: [12345] } } }
})

// Archive (use instead of delete when campaign has stats)
yandex_direct_api({
  endpoint: "/json/v5/campaigns",
  method:   "POST",
  body: { method: "archive", params: { SelectionCriteria: { Ids: [12345] } } }
})
```

`delete` only works for campaigns with no impressions (error 5001 otherwise). Default to `archive`.

---

## Ad groups

### Recipe 7 — List ad groups for a campaign

```
yandex_direct_api({
  endpoint: "/json/v5/adgroups",
  method:   "POST",
  body: {
    method: "get",
    params: {
      SelectionCriteria: { CampaignIds: [12345] },
      FieldNames: ["Id", "Name", "CampaignId", "Status", "RegionIds"],
      Page: { Limit: 1000 }
    }
  }
})
```

### Recipe 8 — Create an ad group

```
yandex_direct_api({
  endpoint: "/json/v5/adgroups",
  method:   "POST",
  body: {
    method: "add",
    params: {
      AdGroups: [{
        Name: "Brand — RU desktop",
        CampaignId: 12345,
        RegionIds: [225],
        NegativeKeywords: { Items: ["besplatno", "skachat"] },
        TextAdGroup: {}
      }]
    }
  }
})
```

`RegionIds: [225]` = Russia. `213` = Moscow, `2` = Saint Petersburg.
Full region list: `Dictionaries.get` with `DictionaryNames: ["GeoRegions"]`.

---

## Ads

### Recipe 9 — Add a text ad (draft)

```
yandex_direct_api({
  endpoint: "/json/v5/ads",
  method:   "POST",
  body: {
    method: "add",
    params: {
      Ads: [{
        AdGroupId: 67890,
        TextAd: {
          Title:          "Kuplyu vashego tovara",
          Title2:         "Dostavka po Rossii",
          Text:           "Skidka 10% na pervyy zakaz. Garantiya kachestva.",
          Href:           "https://example.com/tovary",
          Mobile:         "NO",
          DisplayUrlPath: "tovary"
        }
      }]
    }
  }
})
```

After `add` the ad is `Status=DRAFT`. Use Recipe 10 to submit to moderation.

### Recipe 10 — Submit ads to moderation

```
yandex_direct_api({
  endpoint: "/json/v5/ads",
  method:   "POST",
  body: {
    method: "moderate",
    params: { SelectionCriteria: { Ids: [555001, 555002] } }
  }
})
```

Status flow: `DRAFT` → `MODERATION` → `ACCEPTED` / `REJECTED`. Any copy update resets to `MODERATION`.

### Recipe 11 — Fetch ads with moderation status

```
yandex_direct_api({
  endpoint: "/json/v5/ads",
  method:   "POST",
  body: {
    method: "get",
    params: {
      SelectionCriteria: { AdGroupIds: [67890] },
      FieldNames: ["Id", "AdGroupId", "Status", "State", "Type"],
      TextAdFieldNames: ["Title", "Title2", "Text", "Href"],
      Page: { Limit: 1000 }
    }
  }
})
```

---

## Keywords

### Recipe 12 — Add keywords to an ad group

```
yandex_direct_api({
  endpoint: "/json/v5/keywords",
  method:   "POST",
  body: {
    method: "add",
    params: {
      Keywords: [
        {
          Keyword:          "kupit vidizhek",
          AdGroupId:        67890,
          NegativeKeywords: { Items: ["besplatno", "skachat"] }
        },
        {
          Keyword:   "+kupit +vidizhek nedorogo",
          AdGroupId: 67890
        }
      ]
    }
  }
})
```

Keyword operators: `!word` (exact form), `+word` (stop-word required), `"phrase"` (only these words), `[phrase]` (fixed order), `(a|b)` (alternatives), `-word` (inline negative).

### Recipe 13 — Fetch keywords and their statuses

```
yandex_direct_api({
  endpoint: "/json/v5/keywords",
  method:   "POST",
  body: {
    method: "get",
    params: {
      SelectionCriteria: { AdGroupIds: [67890] },
      FieldNames: ["Id", "Keyword", "Status", "State", "AdGroupId", "CampaignId"],
      Page: { Limit: 1000 }
    }
  }
})
```

---

## Bids

### Recipe 14 — Set manual keyword bids

```
yandex_direct_api({
  endpoint: "/json/v5/keywordbids",
  method:   "POST",
  body: {
    method: "set",
    params: {
      KeywordBids: [
        { KeywordId: 11111, SearchBid: 50000000, NetworkBid: 20000000 },
        { KeywordId: 11112, SearchBid: 30000000, NetworkBid: 10000000 }
      ]
    }
  }
})
```

`50000000` = 50 ₽. Manual bids are ignored under auto-strategies; effective only with `HIGHEST_POSITION` / `AVERAGE_CPC`.

### Recipe 15 — Apply bid modifier (mobile +50%)

```
yandex_direct_api({
  endpoint: "/json/v5/bidmodifiers",
  method:   "POST",
  body: {
    method: "set",
    params: {
      BidModifiers: [{
        CampaignId: 12345,
        MobileAdjustment: { BidModifier: 150 }
      }]
    }
  }
})
```

`100` = unchanged, `50` = -50%, `200` = +100%, range `[0..1300]`.

### Recipe 16 — Switch campaign to PAY_FOR_CONVERSION strategy

```
yandex_direct_api({
  endpoint: "/json/v5/campaigns",
  method:   "POST",
  body: {
    method: "update",
    params: {
      Campaigns: [{
        Id: 12345,
        TextCampaign: {
          BiddingStrategy: {
            Search: {
              BiddingStrategyType: "PAY_FOR_CONVERSION",
              PayForConversion: {
                Cpa:              150000000,
                GoalId:           99887766,
                WeeklySpendLimit: 10000000000
              }
            },
            Network: { BiddingStrategyType: "SERVING_OFF" }
          }
        }
      }]
    }
  }
})
```

`Cpa: 150000000` = 150 ₽/conversion. Requires an active Metrika goal.

---

## Reports lifecycle

The Reports API uses a separate endpoint and a distinct HTTP lifecycle:
`201` = queued, `202` = forming, `200` = body is the finished TSV. There is no "cancel" — ignore stuck jobs; they expire in a few hours.

### Recipe 17 — Submit a campaign performance report (offline mode)

```
yandex_direct_api({
  endpoint: "/json/v5/reports",
  method:   "POST",
  headers: {
    "processingMode":    "offline",
    "returnMoneyInMicros": "false",
    "skipReportHeader":  "true",
    "skipColumnHeader":  "true",
    "skipReportSummary": "true"
  },
  body: {
    params: {
      SelectionCriteria: {
        DateFrom: "2026-05-01",
        DateTo:   "2026-05-15"
      },
      FieldNames: [
        "Date", "CampaignId", "CampaignName",
        "Impressions", "Clicks", "Cost", "Conversions"
      ],
      ReportName:    "campaigns-may2026-v1",
      ReportType:    "CAMPAIGN_PERFORMANCE_REPORT",
      DateRangeType: "CUSTOM_DATE",
      Format:        "TSV",
      IncludeVAT:    "NO",
      IncludeDiscount: "NO"
    }
  }
})
```

Note: Reports use `params` as the top-level key, not `{ method, params }`.

### Recipe 18 — Polling pattern (via yandex_direct_api)

The gateway wraps a single HTTP POST. For offline reports Claude must poll manually — repeat the **identical** call until the response status is 200:

```
1. Call Recipe 17 →
   - HTTP 200: response body is TSV text. Done.
   - HTTP 201 or 202: report is queued / forming.
     Read Retry-After from the response headers (default 60 s).
     Wait that many seconds, then repeat the identical call.
   - HTTP 400: bad params, do not retry. Read the JSON error body.
   - HTTP 5xx: transient, exponential backoff.

2. Repeat the SAME body — any change produces a new job.
3. Max 5 parallel report jobs per account. Exceed → error 8 / 429.
```

Pseudocode for multi-turn conversation with Claude:

```
# Turn 1: submit
response = yandex_direct_api(endpoint="/json/v5/reports", body=PAYLOAD)
if response.status == 200: parse TSV
if response.status in (201, 202): remember PAYLOAD, wait Retry-After

# Turn 2+: poll with identical PAYLOAD
repeat until status == 200
```

### Recipe 19 — Keyword-level report (ad performance)

```
yandex_direct_api({
  endpoint: "/json/v5/reports",
  method:   "POST",
  headers: {
    "processingMode": "offline",
    "returnMoneyInMicros": "false",
    "skipReportHeader":  "true",
    "skipColumnHeader":  "true",
    "skipReportSummary": "true"
  },
  body: {
    params: {
      SelectionCriteria: {
        DateFrom: "2026-05-01",
        DateTo:   "2026-05-15",
        Filter: [{
          Field:    "CampaignId",
          Operator: "IN",
          Values:   ["12345"]
        }]
      },
      FieldNames: [
        "Date", "AdGroupId", "AdId", "Criteria", "CriterionType",
        "Impressions", "Clicks", "Cost", "Ctr", "AvgCpc"
      ],
      ReportName:    "kw-may2026-v1",
      ReportType:    "CRITERIA_PERFORMANCE_REPORT",
      DateRangeType: "CUSTOM_DATE",
      Format:        "TSV",
      IncludeVAT:    "NO"
    }
  }
})
```

### Recipe 20 — Search query performance report

```
yandex_direct_api({
  endpoint: "/json/v5/reports",
  method:   "POST",
  headers: {
    "processingMode": "offline",
    "returnMoneyInMicros": "false",
    "skipReportHeader": "true",
    "skipColumnHeader": "true",
    "skipReportSummary": "true"
  },
  body: {
    params: {
      SelectionCriteria: {
        DateFrom: "2026-05-01",
        DateTo:   "2026-05-15"
      },
      FieldNames: [
        "Date", "CampaignId", "Query",
        "Impressions", "Clicks", "Cost"
      ],
      ReportName:    "sqr-may2026-v1",
      ReportType:    "SEARCH_QUERY_PERFORMANCE_REPORT",
      DateRangeType: "CUSTOM_DATE",
      Format:        "TSV",
      IncludeVAT:    "NO"
    }
  }
})
```

---

## Wordstat / Keyword research

> **Context**: the standalone `wordstat_keywords` tool was removed in v0.5. Yandex Direct provides keyword volume data through two mechanisms: the `keywordsresearch` service (synchronous for small batches) and the `KeywordsResearchReport` report type (async, larger batches). For competition scoring, `mutagen_competition` is faster and caches results for 30 days — prefer it.

### Recipe 21 — Check search volume for keywords (hasSearchVolume)

```
yandex_direct_api({
  endpoint: "/json/v5/keywordsresearch",
  method:   "POST",
  body: {
    method: "hasSearchVolume",
    params: {
      Keywords: [
        "kupit diletant",
        "kupit vidizhek nedorogo",
        "vidizhek optom"
      ],
      GeoIDs: [225]
    }
  }
})
```

Returns `Keywords[]` with `Keyword` and `SearchVolume: true|false`. Use to filter out zero-volume phrases before adding them to campaigns.

`GeoIDs`: `225` = Russia, `213` = Moscow, `2` = Saint Petersburg.

### Recipe 22 — Keyword frequency via async Wordstat report

For bulk volume data (hundreds of keywords) use the async report lifecycle:

**Step 1 — Create the report:**

```
yandex_direct_api({
  endpoint: "/json/v5/keywordsresearch",
  method:   "POST",
  body: {
    method: "CreateNewWordstatReport",
    params: {
      Phrases: [
        "kupit vidizhek",
        "vidizhek nedorogo",
        "vidizhek internet-magazin"
      ],
      GeoID: [225]
    }
  }
})
```

Returns `result` with a numeric report ID (e.g. `{ result: 42 }`).

**Step 2 — Poll for completion:**

```
yandex_direct_api({
  endpoint: "/json/v5/keywordsresearch",
  method:   "POST",
  body: {
    method: "GetWordstatReportList",
    params: {}
  }
})
```

Returns array of jobs with `StatusReport: "Done" | "Pending"`. When `StatusReport == "Done"`, proceed to Step 3.

**Step 3 — Fetch results:**

```
yandex_direct_api({
  endpoint: "/json/v5/keywordsresearch",
  method:   "POST",
  body: {
    method: "GetWordstatReport",
    params: { ReportID: 42 }
  }
})
```

Returns `result[]` with `Phrase`, `SearchedWith` (monthly search count), and `SearchedAlso` (related phrases).

**Step 4 — Delete the report when done:**

```
yandex_direct_api({
  endpoint: "/json/v5/keywordsresearch",
  method:   "POST",
  body: {
    method: "DeleteWordstatReport",
    params: { ReportID: 42 }
  }
})
```

Max 5 concurrent wordstat report jobs per account.

### Recipe 23 — Get keyword suggestions (related phrases)

```
yandex_direct_api({
  endpoint: "/json/v5/keywordsresearch",
  method:   "POST",
  body: {
    method: "hasSearchVolume",
    params: {
      Keywords: ["vidizhek"],
      GeoIDs: [213]
    }
  }
})
```

The response `SearchedAlso` field (in GetWordstatReport) carries related phrases with their own volumes — useful for keyword expansion.

---

## Dictionaries

### Recipe 24 — Fetch geo regions

```
yandex_direct_api({
  endpoint: "/json/v5/dictionaries",
  method:   "POST",
  body: {
    method: "get",
    params: {
      DictionaryNames: ["GeoRegions"]
    }
  }
})
```

Returns a tree of regions with `GeoRegionId`, `GeoRegionName`, `GeoRegionType`, `ParentId`.

### Recipe 25 — Fetch available currencies and timezone info

```
yandex_direct_api({
  endpoint: "/json/v5/dictionaries",
  method:   "POST",
  body: {
    method: "get",
    params: {
      DictionaryNames: ["Currencies", "TimeZones"]
    }
  }
})
```

---

## Agency clients

### Recipe 26 — List agency sub-accounts

```
yandex_direct_api({
  endpoint: "/json/v5/agencyclients",
  method:   "POST",
  body: {
    method: "get",
    params: {
      SelectionCriteria: { Archived: "NO" },
      FieldNames: ["Login", "ClientId", "Name", "Currency", "Restrictions"],
      Page: { Limit: 500 }
    }
  }
})
```

---

## Autotargeting

### Recipe 29 — Disable autotargeting categories on a search ad group

Autotargeting lives in the Keywords service as a special `---autotargeting` keyword, not on the AdGroup object. To reconfigure it:

**Step 1 — Find the autotargeting keyword Id:**
```
yandex_direct_api({
  endpoint: "/json/v5/keywords",
  method:   "POST",
  body: {
    method: "get",
    params: {
      SelectionCriteria: { AdGroupIds: [<groupId>] },
      FieldNames: ["Id", "Keyword", "AutotargetingCategories"]
    }
  }
})
```
Locate the row where `Keyword == "---autotargeting"`. GET returns `AutotargetingCategories: { Items: [{Category, Value}] }`.

**Step 2 — Update with a bare array (no `Items` wrapper on write):**
```
yandex_direct_api({
  endpoint: "/json/v5/keywords",
  method:   "POST",
  body: {
    method: "update",
    params: {
      Keywords: [{
        Id: <autotargetingKeywordId>,
        AutotargetingCategories: [
          { Category: "BROADER",     Value: "NO" },
          { Category: "ACCESSORY",   Value: "NO" },
          { Category: "ALTERNATIVE", Value: "NO" }
        ]
      }]
    }
  }
})
```
This leaves `EXACT` and `COMPETITOR` on (omitted = unchanged). You cannot set all five to `NO` — **error 5005**.

**Read/write asymmetry:** GET wraps the array in `{ Items: [...] }`; UPDATE takes the bare `[...]` directly.

---

## Operational safety

### Recipe 30 — Throwaway-draft canary before irreversible mutations

Before any irreversible live change (delete+recreate campaigns, bulk keyword replacement, strategy switch), run a throwaway **DRAFT canary**:

1. Create the object with the exact payload (campaign, keyword, etc.) targeting a throwaway name or sandbox.
2. Immediately `get` it back and verify all fields read correctly.
3. Then `delete` or `archive` the canary object.
4. Only if the canary succeeds → apply to production.

This pattern caught **error 6000** (DailyBudget + auto strategy), **error 8000** (autotargeting on AdGroup), and **error 5005** (all categories off) in account ki.vech before any live damage.

---

## Error handling

### Recipe 27 — Detect partial batch errors

HTTP 200 does not mean the batch succeeded. Always iterate `AddResults`, `UpdateResults`, etc.:

```
const results = response.result.AddResults  // or UpdateResults, DeleteResults
for (const item of results) {
  if (item.Errors) {
    console.error("Item failed:", item.Errors)
  } else {
    console.log("Created:", item.Id)
  }
  if (item.Warnings) {
    console.warn("Warnings on", item.Id, item.Warnings)
  }
}
```

### Recipe 28 — Units accounting

Every response carries `Units: consumed/remaining/daily-limit` in response headers. Throttle writes when `remaining / daily-limit < 0.2` to avoid `error 153` (UnitsLimitExceeded).

Common retry guide:
- Codes `1`, `9`, `12`: exponential backoff, max 3–5 attempts.
- Codes `2`, `8`, `17`, `52`, `53`, `54`, `56`, `152`, `506`: do not retry, log and alert.
- Code `153`: pause all writes until 00:00 UTC reset.
- Code `506` / `1002`: OAuth token revoked — refresh immediately.

---

## Migration from v0.4

| Deleted tool | Replacement | Notes |
|---|---|---|
| `wordstat_keywords` | `yandex_direct_api({ endpoint: "/json/v5/keywordsresearch", method: "POST", body: { method: "hasSearchVolume", params: { Keywords: [...], GeoIDs: [...] } } })` | Recipe 21: fast, synchronous, boolean volume check |
| `wordstat_keywords` (bulk) | CreateNewWordstatReport → poll GetWordstatReportList → GetWordstatReport → DeleteWordstatReport (Recipes 22–23) | Async, returns numeric volumes + related phrases |
| `wordstat_keywords` (competition) | `mutagen_competition` tool | Faster, 30-day cache, competition score 1–25 |

When migrating:
1. Replace `wordstat_keywords({ keywords: [...], geo: "..." })` with Recipe 21 for a quick existence check.
2. For full volume data (monthly impressions), use the async flow in Recipe 22.
3. For keyword competition scoring, use `mutagen_competition` — it is faster and cached, requiring no polling.
