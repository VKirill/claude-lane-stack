# BidsService — bids and strategies

## Endpoints / methods

- `bids` service: `set`, `setAuto`, `get` — legacy keyword-level entry point.
- `keywordbids` service: `get`, `set`, `setAuto` — **current** entry point for per-keyword bids.
- `bidmodifiers` service: `set`, `get`, `delete` — bid adjustments.

In modern campaigns bids are usually **managed by the campaign-level strategy** (`Campaigns.update.BiddingStrategy`); manual per-keyword bids work only with `HIGHEST_POSITION` / `AVERAGE_CPC`.

## Campaign strategies (BiddingStrategy)

### Search

| Type | Behavior | Fields |
|---|---|---|
| `HIGHEST_POSITION` | Highest available position, manual CPC | — |
| `WB_MAXIMUM_CLICKS` | Weekly budget, maximize clicks | `WbMaximumClicks.WeeklySpendLimit`, `.BidCeiling` |
| `WB_MAXIMUM_CONVERSION_RATE` | Weekly budget, maximize conversions | `.WeeklySpendLimit`, `.BidCeiling`, `.GoalId` |
| `AVERAGE_CPC` | Hold target average CPC | `AverageCpc.AverageCpc`, `.WeeklySpendLimit` |
| `AVERAGE_CPA` | Target cost per action | `AverageCpa.AverageCpa`, `.GoalId`, `.WeeklySpendLimit` |
| `WEEKLY_CLICK_PACKAGE` | Weekly click package | `WeeklyClickPackage.ClicksPerWeek`, `.AverageCpc`, `.BidCeiling` |
| `AVERAGE_ROI` | Average ROI | `AverageRoi.ReserveReturn`, `.RoiCoef`, `.GoalId` |
| `PAY_FOR_CONVERSION` | Pay only on conversion | `PayForConversion.Cpa`, `.GoalId`, `.WeeklySpendLimit` |
| `SERVING_OFF` | Serving off | — |

### Network (RSYA)

Same strategies plus `NETWORK_DEFAULT` (network mirrors the search-level setting).

## Money fields — micro-currency

**All** money fields use **minimum units** (micro-rubles). Divide by 1 000 000 for rubles.

| Field | Type | Example (1 000 ₽) |
|---|---|---|
| `MaxCpc` (per keyword) | int64 | `1000000000` |
| `Bid` | int64 | `1000000000` |
| `ContextBid` (network) | int64 | `500000000` (= 500 ₽) |
| `WeeklySpendLimit` | int64 | `7000000000` (= 7 000 ₽) |
| `AverageCpc` | int64 | `30000000` (= 30 ₽) |
| `BidCeiling` | int64 | bid ceiling in micros |
| `Cpa` | int64 | target CPA in micros |

**Critical**: the error is 6 orders of magnitude. Confusing rubles and micros = 1 000 000× wrong bid. Wrap the conversion behind a typed boundary with tests.

## `KeywordBids.set` — manual

```json
{
  "method": "set",
  "params": {
    "KeywordBids": [{
      "KeywordId": 11111,
      "SearchBid": 5000000,
      "NetworkBid": 2000000
    }]
  }
}
```

- `SearchBid` — search bid (micros).
- `NetworkBid` — network bid (micros).
- Only effective with `HIGHEST_POSITION` / `AVERAGE_CPC` and other manual strategies. On auto-strategies the value is **ignored**.

## `KeywordBids.setAuto`

```json
{
  "method": "setAuto",
  "params": {
    "KeywordBidsAuto": [{
      "KeywordId": 11111,
      "StrategyPriority": "HIGH"  // HIGH | NORMAL | LOW
    }]
  }
}
```

— a keyword priority hint for the auto-strategy. Not a CPC value.

## `KeywordBids.get`

```json
{
  "method": "get",
  "params": {
    "SelectionCriteria": {
      "KeywordIds": [11111, 22222]
    },
    "FieldNames": [
      "KeywordId", "AdGroupId", "CampaignId",
      "ServingStatus", "StrategyPriority",
      "SearchBid", "NetworkBid", "ContextCoverage",
      "AuctionBids"
    ]
  }
}
```

`AuctionBids` — recommended bids to land different traffic volumes (5, 9, 15, 30, 62, 75, 85, 100).

## BidModifiersService — adjustments

Adjustments multiply the base bid based on a condition:

| Type | Applies to |
|---|---|
| `MobileAdjustment` | Mobile devices |
| `DesktopAdjustment` | Desktop |
| `DemographicsAdjustment` | Gender / age |
| `RetargetingAdjustment` | Retargeting lists |
| `RegionalAdjustment` | Regions |
| `VideoAdjustment` | Video placements |
| `IncomeAdjustment` | Audience income level |
| `HourlyAdjustment` | Time of day |

### `BidModifiers.set`

```json
{
  "method": "set",
  "params": {
    "BidModifiers": [{
      "CampaignId": 12345,
      "MobileAdjustment": {
        "BidModifier": 150
      }
    }]
  }
}
```

Value is an integer percentage. `100` = unchanged. `50` = -50%. `200` = +100%. Allowed range typically `[0..1300]` (varies by type).

## Strategy recommendations

- **Start manual** (`HIGHEST_POSITION` / `AVERAGE_CPC`) to understand the auction.
- Switch to **auto-strategy** only after enough Metrika conversion data (typically 200+ conversions over 4 weeks).
- **`PAY_FOR_CONVERSION`** is the safest entry — pay only for the conversion event.
- **Split search and network** into separate campaigns — auctions and behavior differ. Avoid `NETWORK_DEFAULT` until network traffic is profiled.

## Strategy lifecycle

- Strategy changes apply within **about an hour**, not instantly.
- Switching to an auto-strategy **preserves** manual bids but **ignores** them until you switch back.
- Auto-strategies need a **learning period** (~1–2 weeks). First few days are noisy.

## Spend guardrails

To avoid overshoots:
1. Campaign level — `DailyBudget` with `Mode` `STANDARD` or `DISTRIBUTED`.
2. Strategy level — `WeeklySpendLimit` and `BidCeiling`.
3. Application level — kill switch that suspends all writes.
4. Audit table logging every bid change with before/after, `RequestId`, operator.

## Confirming large changes

Any bulk bid change (>50 keywords or >100% delta) must run through a preview:
1. `get` current bids.
2. Compute a diff and show the operator the total ruble-per-day delta (using CTR from Reports).
3. Apply `set` only after explicit confirmation.
