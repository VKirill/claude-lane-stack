# AdsService + KeywordsService

## AdsService — methods

| Method | Purpose |
|---|---|
| `get` | Fetch ads |
| `add` | Create ads (batch up to 1 000) |
| `update` | Update ads (sends them back to moderation) |
| `delete` | Delete (only if no impressions, otherwise `archive`) |
| `archive` / `unarchive` | Archiving |
| `moderate` | Submit drafts to moderation |
| `suspend` / `resume` | Pause / resume serving |

## Ad types (exactly one field)

| Field | Purpose |
|---|---|
| `TextAd` | Standard text & graphic ad for search and network |
| `MobileAppAd` | Mobile-app ad |
| `DynamicTextAd` | Dynamic ad (generated from feed / site) |
| `ImageAd` | Image banner |
| `CpcVideoAdBuilderAd` | CPC video |
| `SmartAdBuilderAd` | Smart banner (Builder) |
| `CpmBannerAdBuilderAd` | CPM banner (Builder) |
| `MobileAppImageAd` | Image ad for app |
| `MobileAppCpcVideoAdBuilderAd` | CPC video for app (Builder) |
| `CpmVideoAdBuilderAd` | CPM video (Builder) |
| `CpmBannerCreativeAd` | Creative Studio creative |

## TextAd minimum

```json
{
  "method": "add",
  "params": {
    "Ads": [{
      "AdGroupId": 67890,
      "TextAd": {
        "Title": "Headline 1 (max 56 chars)",
        "Title2": "Headline 2 (optional, max 30)",
        "Text": "Ad text (max 81 chars)",
        "Href": "https://example.com/landing",
        "Mobile": "NO",
        "DisplayUrlPath": "season",
        "VCardId": null,
        "SitelinkSetId": null,
        "AdImageHash": null,
        "BusinessId": null
      }
    }]
  }
}
```

### Text limits

- `Title` — up to 56 characters
- `Title2` — up to 30 characters
- `Text` — up to 81 characters (including punctuation)
- `DisplayUrlPath` — up to 20 Latin characters or 9 Cyrillic; no `http` / `/`

## States — Status, State

`Status` (moderation):
- `DRAFT` — after `add`, not yet submitted
- `MODERATION` — under review
- `PREACCEPTED` — pre-accepted (serving, final review pending)
- `ACCEPTED` — accepted
- `REJECTED` — rejected
- `UNKNOWN` — sync edge case

`State`:
- `ON` — serving
- `OFF` — user-off
- `SUSPENDED` — paused
- `ARCHIVED` — archived

## Workflow: create → moderate → activate

```
add (Status=DRAFT) → moderate → MODERATION → {ACCEPTED|REJECTED}
                                                ↓
                                              State=ON (if paid and Group/Campaign ON)
```

`moderate` submits the listed ads to moderation. Without `moderate` they stay `DRAFT`.

## Updates — `Ads.update`

Any change to `TextAd.*` after `ACCEPTED` resets `Status` to `MODERATION`. Changing only `Href` may pass without re-moderation depending on the change.

## `Ads.get`

```json
{
  "method": "get",
  "params": {
    "SelectionCriteria": {
      "CampaignIds": [12345],
      "AdGroupIds": [67890],
      "States": ["ON", "SUSPENDED"],
      "Statuses": ["ACCEPTED"]
    },
    "FieldNames": ["Id", "AdGroupId", "Status", "State", "Type"],
    "TextAdFieldNames": ["Title", "Title2", "Text", "Href", "DisplayUrlPath", "VCardId", "SitelinkSetId"],
    "Page": { "Limit": 1000 }
  }
}
```

Type-specific FieldNames mirror the campaigns convention:
- `TextAdFieldNames`
- `MobileAppAdFieldNames`
- `DynamicTextAdFieldNames`
- `ImageAdFieldNames`
- `CpcVideoAdBuilderAdFieldNames`
- `SmartAdBuilderAdFieldNames`
- ...

## KeywordsService — methods

| Method | Purpose |
|---|---|
| `get` | Fetch keywords |
| `add` | Add keywords (batch up to 1 000) |
| `update` | Update keywords (negatives; bids via `KeywordBids`) |
| `delete` | Delete keywords |
| `resume` / `suspend` | Resume / pause a keyword |

## `Keywords.add`

```json
{
  "method": "add",
  "params": {
    "Keywords": [{
      "Keyword": "buy cheap tv",
      "AdGroupId": 67890,
      "UserParam1": "tv-cheap",
      "UserParam2": "promo",
      "NegativeKeywords": {
        "Items": ["free", "repair"]
      }
    }]
  }
}
```

## Keyword operators

| Operator | Meaning |
|---|---|
| `!word` | Exact form (no morphology) |
| `+word` | Stop-word is required (prepositions, particles) |
| `"phrase"` | Only these words, no extras |
| `[phrase]` | Fixed word order |
| `(a\|b)` | Alternatives |
| `-word` | Negative word (per phrase) |

## Negative keywords — three levels

1. **Campaign-level**: `Campaign.NegativeKeywords` — applies to all groups.
2. **AdGroup-level**: `AdGroup.NegativeKeywords` — applies to all keywords in the group.
3. **Keyword-level**: `Keyword.NegativeKeywords` — applies to a single phrase.

Limits:
- Campaign: up to 20 000 characters total.
- AdGroup: up to 4 096 characters / ~700 phrases.
- Keyword: up to 7 negatives per phrase.

## `NegativeKeywordSharedSets`

Shared negative lists reusable across campaigns:

```json
{
  "method": "add",
  "params": {
    "NegativeKeywordSharedSets": [{
      "Name": "Brand exclusions",
      "NegativeKeywords": { "Items": ["competitor", "review"] }
    }]
  }
}
```

Attach at campaign level via `NegativeKeywordSharedSetIds: [<id>]`.

## Add limits

- Up to 1 000 keywords per `Keywords.add`.
- Recommended max 200 keywords per AdGroup.
- Phrase length up to 4 096 characters / 7 words.

## Ad archiving

`Ads.archive` requires `OFF` / `SUSPENDED` status. Archived ads are not served and are read-only until `unarchive`.

## Sitelinks, VCards, Images

Before `Ads.add` referencing sitelinks / vcards, create them via `SitelinksService.add` / `VCardsService.add`, capture `SitelinkSetId` / `VCardId`, and reference them. Images go through `AdImageHash` (the hash of a pre-uploaded image).
