# Phase 23.0B — Q1: Current Sell Framework Audit

**Audit Date:** 2026-06-03  
**Analysis Run:** PAR-20260603-AC8FD5F0  
**Portfolio Holdings:** 81 positions

---

## What the Current Framework Does

The Phase 23.0A `_computeTaxActions()` function drives the sell candidate display. It processes `data.security_overlays` — the JSON array returned by `/api/portfolio/analyze` — using the following logic:

```
isPoorOutlook    = signal === "BEARISH" || flag === "TRIM"
isBuyCandidate   = cwdas === "BUY"     || signal === "BULLISH"
isReduceCandidate = flag === "TRIM"    || flag === "REDUCE_CANDIDATE"
```

Where:
- `signal` reads `ov.ess_direction || ov.signal_direction`
- `flag` reads `ov.recommended_action`
- `cwdas` reads `ov.cw_das_flag`

---

## Field Mapping Reality Check

The `SecurityIntelligenceOverlay` dataclass (`src/portfolio/models.py`) does **not** contain the following fields that `_computeTaxActions()` attempts to read:

| JS Field Read | Overlay Field Actual | Present? | Result |
|---|---|---|---|
| `ov.ess_direction` | Not in dataclass | No | `undefined` → falls through to `signal_direction` |
| `ov.recommended_action` | Not in dataclass (use `opportunity_flag`) | No | `""` always |
| `ov.cw_das_flag` | Not in dataclass | No | `""` always |
| `ov.cost_basis` | Not in dataclass | No | `NaN` → `hasGainData = false` |
| `ov.market_value` | Not in dataclass | No | `NaN` → `hasGainData = false` |
| `ov.holding_days` | Not in dataclass | No | `null` |

**The overlay DOES contain:**
- `signal_direction` → correctly read via fallback
- `opportunity_flag` (TRIM | HOLD | ACCUMULATE | WATCH) → NOT read (wrong field name in JS)
- `is_overweight_vs_target` → NOT read by tax action logic at all

**Consequence:** `flag === "TRIM"` and `isReduceCandidate` can NEVER be true. `hasGainData` is always false. Buckets B, C, D, and E can never fire for an individual holding (they all require `unrealizedGL != null` OR `flag === "TRIM"`).

**Effective behavior:** The framework reduces entirely to:
- Check 5: `isPoorOutlook && unrealizedGL == null` → Bucket A ("cost basis unavailable")
- Which fires when and only when `signal_direction === "BEARISH"`

---

## Why TSLA and PRIM Appear

| Symbol | signal_direction | Trigger | Bucket | Reason Shown |
|---|---|---|---|---|
| TSLA | BEARISH | Check 5: isPoorOutlook && unrealizedGL == null | A (SELL NOW) | "Poor outlook — cost basis unavailable for tax calculation" |
| PRIM | BEARISH | Check 5: isPoorOutlook && unrealizedGL == null | A (SELL NOW) | "Poor outlook — cost basis unavailable for tax calculation" |

Both appear solely because their `signal_direction` is BEARISH. No cost basis, allocation, or strategic context is considered.

**TSLA actual data:**
- Market value: $14,329.98 (2.96% of portfolio)
- Cost basis: $10,698.74 → unrealized gain: +$3,631 (+33.9%)
- Allocation: EQUITIES.US.MEGA.HYPER_MEGA
- EQUITIES.US.MEGA.HYPER_MEGA overweight: +3.58% (MODERATE)

**PRIM actual data:**
- Market value: $4,906.80 (1.01% of portfolio)
- Cost basis: $4,900.00 → unrealized gain: +$6.80 (break-even)
- Allocation: EQUITIES.US.SMALL
- EQUITIES.US.SMALL overweight: +3.19% (LOW)

---

## Why FIS, DODFX, VXUS, VEA, FIGFX, VOO, FXAIX Do NOT Appear

### FIS
| Field | Value | Check | Outcome |
|---|---|---|---|
| `signal_direction` | NEUTRAL | `signal === "BEARISH"` | false |
| `opportunity_flag` | HOLD (not read) | `flag === "TRIM"` | false (field not mapped) |
| `isPoorOutlook` | false | — | No bucket |

**FIS is not appearing despite being the most actionable position in the portfolio:**
- Market value: $23,287.42 (4.81% of portfolio — 2nd largest holding)
- Cost basis: $37,631.72
- Unrealized loss: **−$14,344.30 (−38.1%)**
- No plans to buy more (former employer stock)
- Known operator exit candidate
- Signal: NEUTRAL (not deteriorating enough to trigger BEARISH; loss is permanent capital destruction, not signal-driven)

### DODFX, VXUS, VEA, FIGFX

| Symbol | signal_direction | Why UNKNOWN | MV | Cost | Unrealized |
|---|---|---|---|---|---|
| DODFX | UNKNOWN | Mutual fund — no ESS score | $15,310.10 | $12,558.51 | +$2,751 |
| VXUS | UNKNOWN | ETF — no ESS score | $3,975.76 | $3,106.80 | +$869 |
| VEA | UNKNOWN | ETF — no ESS score | $3,610.75 | $3,015.00 | +$596 |
| FIGFX | UNKNOWN | Mutual fund — no ESS score | $1,219.26 | $1,068.36 | +$151 |

**These are not appearing despite all four being part of the EQUITIES.INTERNATIONAL overweight (+6.63%, MODERATE)** and EQUITIES.INTERNATIONAL.LARGE overweight (+4.10%, MODERATE). ETFs and mutual funds do not have individual ESS scores, so they are permanently UNKNOWN signal. The current framework has no ETF/fund candidate path.

### VOO, FXAIX

| Symbol | signal_direction | MV | Cost | Unrealized | Allocation Role |
|---|---|---|---|---|---|
| VOO | UNKNOWN | $17,453.00 | $13,687.95 | +$3,765 | EQUITIES.US.MEGA index fund |
| FXAIX | UNKNOWN | $6,307.37 | $5,005.18 | +$1,302 | EQUITIES.US.MEGA index fund |

UNKNOWN signal → not appearing. Both are index funds with no ESS scores. EQUITIES.US.MEGA is overweight +1.13% (LOW). Also relevant to consider for funding new purchases of individual high-conviction names.

---

## Root Cause Summary

The current framework has **one functional detection mechanism:** BEARISH `signal_direction`.

**Blind spots in the current implementation:**

| Blind Spot | Impact | Affected Holdings |
|---|---|---|
| ETFs/funds have UNKNOWN signal permanently | Can never generate action candidates | DODFX, VXUS, VEA, FIGFX, VOO, FXAIX, BND, BNDX, BSVN, etc. |
| `recommended_action` field not in overlay (should be `opportunity_flag`) | Bucket C (TRIM/REDUCE) never fires | Any TRIM-flagged holding |
| No allocation-drift-based candidacy | Overweight nodes don't generate candidates | EQUITIES.INTERNATIONAL.LARGE, HYPER_MEGA |
| No strategic/operator-intent layer | Former employer stock, legacy positions invisible | FIS |
| No funding-source logic | Cannot answer "what do I sell to fund X?" | Full portfolio |
| `cost_basis`/`market_value` not in overlay | No actual gain/loss context | All 81 holdings |

---

## Answer: Does the current framework match operator workflow?

**No.** The operator workflow begins with portfolio-level questions:
1. What should I reduce or exit?
2. What am I overweight in?
3. What can I sell to fund higher-conviction positions?
4. What can I harvest for tax benefit?
5. What bearish signals need action?

The current framework answers only question 5, and even then incompletely (it misses `opportunity_flag = "TRIM"` holdings and has no cost basis context).

**TSLA and PRIM are not wrong answers. They are the only answers, which is wrong.**
