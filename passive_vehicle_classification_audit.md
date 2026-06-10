# ETF-CONVICTION-01: Passive Vehicle Classification Audit

**Date:** 2026-06-10

---

## Portfolio-Wide ETF/Fund Inventory

| Symbol | Vehicle Type | FVI Tier | CRA Label | CRA Reason Code | DQ Eligible? | Funding Source? | Reduction Queue? |
|---|---|---|---|---|---|---|---|
| VOO | Broad US Passive ETF | ELITE | Low Conviction Reduction | HOLD + no replay + no ESS | No | Yes (Cat 4) | Yes (rank ~6) |
| VB | US Small Cap Passive ETF | ELITE | Low Conviction Reduction | HOLD + no replay + no ESS | No | Yes (Cat 4) | Yes (rank ~5) |
| VO | US Mid Cap Passive ETF | ELITE | Low Conviction Reduction | HOLD + no replay + no ESS | No | Yes (Cat 4) | Yes (~rank 10) |
| FXAIX | US Large Cap Passive Mutual Fund | ELITE | Low Conviction Reduction | HOLD + no replay + no ESS | No | Yes (Cat 4) | Yes (~rank 11) |
| VEA | Intl Developed Passive ETF | ELITE | Overweight Reduction | In OW INTERNATIONAL node | No | Yes (Cat 4) | Yes (rank ~14) |
| VWO | Emerging Markets Passive ETF | ELITE | Tax-Aware Exit | Unrealized loss position | No | Yes | Yes |
| BND | US Bond Passive ETF | ELITE | Tax-Aware Exit | Unrealized loss | No | No (fixed income) | Yes |
| BNDX | Intl Bond Passive ETF | ELITE | Tax-Aware Exit | Unrealized loss | No | No (fixed income) | Yes |
| DODFX | Intl Active Mutual Fund | HIGH | Overweight Reduction | In OW INTERNATIONAL node | No | Yes (SELL_LAST) | Yes (⏸ deferred) |
| FBTC | Bitcoin ETF | HIGH | Tax-Aware Exit | Unrealized loss | No | Yes | Yes |
| FETH | Ethereum ETF | HIGH | Tax-Aware Exit | Unrealized loss | No | Yes | Yes |
| FMCSX | US Mid Cap Active Mutual Fund | MEDIUM | Not in CRA pool (de minimis weight) | Below 1% threshold | No | Marginal | No |
| FCPGX | US Small Cap Growth Active Fund | MEDIUM | Not in CRA pool (de minimis) | Below 1% threshold | No | No | No |
| FSOL | Solana Fund | LOW | Tax-Aware Exit (suppressed) | <$500 proceeds | No | No | No (suppressed) |
| FIGFX | Intl Growth Active Fund | MEDIUM | Not found in current PAR | Not held or not overweight | No | Marginal | No |

---

## CW-DAS Eligibility Analysis

**Universal result: ALL ETFs and mutual funds are ineligible for the Deployment Queue.**

The three-gate failure:

| Gate | Requirement | ETF Reality | Result |
|---|---|---|---|
| Signal | `signal_direction == "BULLISH"` | UNKNOWN (no ESS scoring) | FAIL |
| Classification | `strategic_classification == "HIGH_CONVICTION_RETAIN"` | TACTICAL_GROWTH | FAIL |
| Tier | `narrative_tier in {CCL, HCA}` | TACTICAL_GROWTH_CANDIDATE | FAIL |

This is architecturally correct. The CW-DAS was designed to rank individual equity securities for capital deployment under the Concentrated Alpha mandate. Passive vehicles serve allocation completion functions, not point-of-conviction functions.

---

## Conviction Classification Logic

### What "Low Conviction" Actually Means in Code

In `capital_source_builder.py`, the LOW_CONVICTION_REDUCTION category is assigned when:
1. `opportunity_flag == "HOLD"` (no ESS deterioration signal)
2. Symbol is not in any higher-priority reduction category (not SIGNAL_DETERIORATION, STRATEGIC_EXIT, OVERWEIGHT_REDUCTION, TAX_AWARE_EXIT)
3. Not in the deployment queue (no buy signal)
4. Portfolio weight ≥ 1% (above de minimis)
5. `replay_supported == False` (no historical outcome evidence)
6. `signal_direction != "BULLISH"` (no buy signal)

**The label captures the ENGINE'S OBSERVATION** that:
- No strong buy signal exists (gates 3, 6)
- No historical replay evidence exists (gate 5)
- No negative signal exists either (gate 1 — still HOLD, not TRIM)

This does NOT mean:
- The vehicle is a poor investment
- The operator should distrust the fund
- The vehicle has underperformed

It means: **the SIH conviction engine has no individual security conviction data for this holding, and the holding sits outside all other categorization buckets.**

---

## The FVI vs. LOW_CONVICTION Contradiction

VOO has:
- **FVI Tier: ELITE** — "Best-in-class passive US equity vehicle"
- **CRA Category: LOW_CONVICTION_REDUCTION** — "Low Conviction"

These two signals are NOT contradictory within their own domains:

| Signal | Dimension | What it measures |
|---|---|---|
| FVI = ELITE | **Vehicle quality** | Is VOO the best vehicle for gaining US equity exposure? |
| LOW_CONVICTION | **Security conviction** | Does the Concentrated Alpha engine have a strong buy/hold conviction on this specific position? |

The FVI says: "If you need a broad US equity passive vehicle, VOO is the best one."  
The LOW_CONVICTION label says: "Compared to direct-conviction equity positions like VRT or ARW, this passive vehicle has no individual alpha thesis backing it."

Both statements are simultaneously true. The problem is that the label "Low Conviction" — presented without context — causes the operator to **conflate vehicle conviction with investment conviction**.

---

## Why These Specific ETFs Are NOT in Higher Categories

### VOO / VB / VO / FXAIX → LOW_CONVICTION (not OVERWEIGHT_REDUCTION)

These vehicles are NOT in an overweight allocation node per the current PAR. If EQUITIES.US or EQUITIES.US.LARGE were MODERATE+ overweight, they would appear as OVERWEIGHT_REDUCTION instead.

### DODFX / VEA → OVERWEIGHT_REDUCTION

These vehicles ARE in the EQUITIES.INTERNATIONAL node which is overweight. They get a more specific reduction reason, which is correct.

### BND / BNDX / VWO / FBTC / FETH → TAX_AWARE_EXIT

These have unrealized losses (cost_basis > market_value). They are categorized for tax harvesting opportunity, not conviction. This is a more accurate and less ambiguous label.

---

## Recommended Operator Interpretation (per vehicle)

| Symbol | Recommended Interpretation |
|---|---|
| VOO | "Elite-quality broad US ETF. Held as allocation completion vehicle. No individual ESS conviction data — passive exposure only. Reducible to fund a higher-conviction direct position." |
| VB | "Elite-quality US small cap ETF. Allocation completion for EQUITIES.US.SMALL. No ESS conviction — passive." |
| VO | "Elite-quality US mid cap ETF. Allocation completion. Reducible when direct mid-cap names are available." |
| FXAIX | "Elite-quality Fidelity 500 equivalent. Passive. Reducible in favor of direct large cap conviction plays." |
| VEA | "Elite-quality international developed ETF. Currently in overweight international node → reduction priority elevated." |
| BND / BNDX | "Tax-loss harvesting candidate. Elite vehicles. Reduction is for tax efficiency, not conviction deficit." |
| DODFX | "High quality active international fund. In overweight INTERNATIONAL node. SELL_LAST policy active — reduce after other international sources." |
| FBTC / FETH | "Quality digital asset vehicles. Held as thematic positions. Tax-loss candidates." |
