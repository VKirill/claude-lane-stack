# CampaignsService + AdGroupsService

## CampaignsService — methods

| Method | Purpose |
|---|---|
| `get` | Fetch campaigns by filter |
| `add` | Create campaigns (batch up to 10) |
| `update` | Update campaigns |
| `delete` | Delete campaigns (only without stats; otherwise `archive`) |
| `suspend` | Pause campaigns (reversible via `resume`) |
| `resume` | Resume suspended campaigns |
| `archive` | Archive (terminal state, reversible via `unarchive`) |
| `unarchive` | Unarchive |

## Campaign types (`Type` field)

| Type | Purpose | Param body |
|---|---|---|
| `TEXT_CAMPAIGN` | Text & graphic ads | `TextCampaign` |
| `UNIFIED_CAMPAIGN` | Unified Performance Campaign (Master of Campaigns) | `UnifiedCampaign` |
| `MOBILE_APP_CAMPAIGN` | Mobile app ads | `MobileAppCampaign` |
| `DYNAMIC_TEXT_CAMPAIGN` | Dynamic ads (feed / URL) | `DynamicTextCampaign` |
| `CPM_BANNER_CAMPAIGN` | CPM banner display | `CpmBannerCampaign` |
| `SMART_CAMPAIGN` | Smart banners (e-commerce) | `SmartCampaign` |
| `CPM_VIDEO_CAMPAIGN` | CPM video | `CpmVideoCampaign` |
| `CPM_PRICE_CAMPAIGN` | Auction display (Outdoor / other inventory) | `CpmPriceCampaign` |

Exactly one of `TextCampaign / UnifiedCampaign / MobileAppCampaign / ...` must be set.

## States — Status vs State

`Status` — moderation / lifecycle status:
- `DRAFT` — draft, not yet sent to moderation
- `MODERATION` — under review
- `ACCEPTED` — moderation passed
- `REJECTED` — rejected by moderation

`State` — operational state:
- `ON` — active, impressions running
- `OFF` — turned off by the user
- `SUSPENDED` — paused (via API / UI; temporary)
- `ENDED` — past `EndDate`
- `CONVERTED` — converted to a different type
- `ARCHIVED` — archived (read-only fields, requires `unarchive`)

`StatusPayment` — payment status:
- `DISALLOWED` — unpaid / no funds
- `ALLOWED` — paid, impressions allowed

## Minimal `Campaigns.add` — TextCampaign

```json
{
  "method": "add",
  "params": {
    "Campaigns": [{
      "Name": "Search RU desktop",
      "StartDate": "2026-01-15",
      "ClientInfo": "Optional client info",
      "TextCampaign": {
        "BiddingStrategy": {
          "Search": {
            "BiddingStrategyType": "WB_MAXIMUM_CLICKS",
            "WbMaximumClicks": {
              "WeeklySpendLimit": 1000000000,
              "BidCeiling": 100000000
            }
          },
          "Network": {
            "BiddingStrategyType": "SERVING_OFF"
          }
        },
        "Settings": [
          { "Option": "ADD_METRICA_TAG", "Value": "YES" },
          { "Option": "ADD_OPENSTAT_TAG", "Value": "NO" }
        ]
      }
    }]
  }
}
```

**Money fields**: `WeeklySpendLimit`, `BidCeiling`, `MaxCpc`, etc. are in **micro-currency** (rubles × 1 000 000). `1000000000` = 1 000 ₽.

## BiddingStrategy types

### Search

- `HIGHEST_POSITION` — highest available position
- `WB_MAXIMUM_CLICKS` — weekly budget, maximize clicks
- `WB_MAXIMUM_CONVERSION_RATE` — weekly budget, maximize conversions (needs Metrika + goals)
- `AVERAGE_CPC` — target average CPC
- `AVERAGE_CPA` — target average cost per action
- `WEEKLY_CLICK_PACKAGE` — weekly click package
- `AVERAGE_ROI` — target average ROI
- `PAY_FOR_CONVERSION` — pay per conversion
- `SERVING_OFF` — serving off

### Network (RSYA)

Same strategies plus `NETWORK_DEFAULT` (network applies the search-level strategy).

## Add limits

- **Max 10 campaigns** per `Campaigns.add` call. More → `error 5004` (or similar).
- Name — up to 255 characters.
- `StartDate` — today or in the future.

## `Campaigns.get` — typical query

```json
{
  "method": "get",
  "params": {
    "SelectionCriteria": {
      "Ids": [12345, 12346],            // optional, max 10 000
      "States": ["ON", "SUSPENDED"],
      "Statuses": ["ACCEPTED"],
      "Types": ["TEXT_CAMPAIGN"]
    },
    "FieldNames": [
      "Id", "Name", "Type", "Status", "State", "StatusPayment",
      "DailyBudget", "Funds", "StartDate", "EndDate", "ClientInfo"
    ],
    "TextCampaignFieldNames": [
      "BiddingStrategy", "PriorityGoals", "Settings", "CounterIds"
    ],
    "Page": { "Limit": 100, "Offset": 0 }
  }
}
```

Type-specific `FieldNames` come as separate arrays per type:
- `TextCampaignFieldNames`
- `UnifiedCampaignFieldNames`
- `MobileAppCampaignFieldNames`
- `DynamicTextCampaignFieldNames`
- `SmartCampaignFieldNames`
- `CpmBannerCampaignFieldNames`
- `CpmVideoCampaignFieldNames`

## `Campaigns.update`

```json
{
  "method": "update",
  "params": {
    "Campaigns": [{
      "Id": 12345,
      "Name": "Renamed campaign",
      "DailyBudget": {
        "Amount": 5000000000,
        "Mode": "STANDARD"
      },
      "TextCampaign": {
        "BiddingStrategy": {
          "Search": { "BiddingStrategyType": "HIGHEST_POSITION" }
        }
      }
    }]
  }
}
```

Unspecified fields are not modified. Clearing optional fields uses `null` or a field-specific sentinel value.

## suspend / resume / archive

```json
{ "method": "suspend", "params": { "SelectionCriteria": { "Ids": [12345] } } }
```

- `suspend`: state → `SUSPENDED`. All ads inside stop serving. Reversible via `resume`.
- `resume`: state → `ON` (if previously `SUSPENDED`).
- `archive`: state → `ARCHIVED`, fields become read-only. Reversible via `unarchive` (state usually returns to `OFF`).
- `delete`: terminal delete — allowed **only** when the campaign has no statistics / impressions. Otherwise → error. **Default**: `archive`, not `delete`.

## AdGroupsService — methods

`get`, `add`, `update`, `delete`. Conceptually an ad group is a container for ads (`Ads`), keywords (`Keywords`), and targetings (`AudienceTargets`, `DynamicTextAdTargets`).

## `AdGroups.add` — TEXT

```json
{
  "method": "add",
  "params": {
    "AdGroups": [{
      "Name": "Brand search RU",
      "CampaignId": 12345,
      "RegionIds": [225],
      "NegativeKeywords": {
        "Items": ["free", "torrent"]
      },
      "TrackingParams": "utm_source=yandex&utm_medium=cpc",
      "TextAdGroup": {}
    }]
  }
}
```

AdGroup types (exactly one):
- `TextAdGroup` (for TextCampaign)
- `MobileAppAdGroup`
- `DynamicTextAdGroup` (requires `Source` — Domain or Feed)
- `DynamicTextFeedAdGroup`
- `SmartAdGroup`
- `MobileAppCpcVideoAdGroup`
- `CpmBannerAdGroup`
- `CpmVideoAdGroup`

## RegionIds

Numeric region IDs from the dictionary. `225` — Russia, `213` — Moscow, `2` — Saint Petersburg. Full list: `Dictionaries.get` with `DictionaryNames: ["GeoRegions"]`.

## Limits

- Up to 1 000 groups per `AdGroups.add`.

## Idempotency for `add`

Direct does **not** support an idempotency key. Mitigations:
1. Before `add`, `get` by `(CampaignId, Name)` or another business key.
2. Persist returned `Id` values with a unique external index in your DB.
3. Never blindly retry `add` on network failures — `get` first.

## Autotargeting for search TEXT_AD_GROUP

Autotargeting is **not** an AdGroup field. It is a special system keyword with phrase `---autotargeting` that Yandex auto-creates for each search ad group. Sending `TextAdGroupAutoTargeting` or `TextAdGroup.AutoTargeting` in an AdGroup payload is rejected with **error 8000** ("unknown parameter").

### Configuring autotargeting categories

1. Fetch the keyword Id:
```json
{ "method": "get", "params": {
    "SelectionCriteria": { "AdGroupIds": [<groupId>] },
    "FieldNames": ["Id", "Keyword", "AutotargetingCategories"]
}}
```
The `---autotargeting` row has `AutotargetingCategories: { Items: [{Category, Value}] }` — note the `Items` wrapper on **read**.

2. Update — pass a **bare array** (no `Items` wrapper on write):
```json
{ "method": "update", "params": {
    "Keywords": [{
      "Id": <autotargetingKeywordId>,
      "AutotargetingCategories": [
        { "Category": "BROADER",     "Value": "NO" },
        { "Category": "ACCESSORY",   "Value": "NO" },
        { "Category": "ALTERNATIVE", "Value": "NO" }
      ]
    }]
}}
```
Omitted categories (e.g. `EXACT`, `COMPETITOR`) keep their current value (effectively stay ON).

### Category name mapping

| API name | UI name (ru) |
|---|---|
| `EXACT` | Целевые |
| `ALTERNATIVE` | Альтернативные |
| `COMPETITOR` | Конкурентные |
| `BROADER` | Широкие |
| `ACCESSORY` | Сопутствующие |

**Note:** the field name is `BROADER`, not `BROAD_MATCH`.

**Constraint:** you cannot disable ALL five categories — **error 5005** "Запрещено выключать все категории в автотаргетинге". At least one must be `YES`.

### Ad group naming convention

Name a search ad group by its **marker phrase** — the cluster query with the highest exact-match frequency ("Частотность «[!]»"), which equals the KeyCollector "Маркерный запрос" column. This makes the group name uniquely identify its semantic intent across campaigns.

## DailyBudget vs auto strategies

`DailyBudget` on a campaign is **incompatible with auto strategies** (e.g. `WB_MAXIMUM_CLICKS`, `WB_MAXIMUM_CONVERSION_RATE`, `PAY_FOR_CONVERSION`). Setting it alongside an auto strategy produces **error 6000** ("Inconsistent object state — Daily budget can only be used in conjunction with manual strategies").

- **Auto strategies**: set the budget inside the strategy as `WeeklySpendLimit`.
- **Manual strategies** (`HIGHEST_POSITION`, `AVERAGE_CPC`): `DailyBudget` is valid.

## Archiving — best practice

- Campaigns with statistics cannot be deleted, only `archive`.
- Archived campaigns can be `unarchive`d — fields become editable again.
- Archived campaigns are not auto-deleted and still appear in selections.
- To exclude them from listings: filter `States: ["ON", "SUSPENDED", "OFF"]` (omit `ARCHIVED`).
