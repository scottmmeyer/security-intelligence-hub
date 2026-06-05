# Phase 23.0B — Q3: FIS Case Study

**Analysis Date:** 2026-06-03  
**Analysis Run:** PAR-20260603-AC8FD5F0  
**Subject:** FIS (Fidelity National Information Services, Inc.)

---

## Position Profile

| Field | Value |
|---|---|
| Symbol | FIS |
| Security Type | US Individual Equity |
| Market Value | $23,287.42 |
| Cost Basis | $37,631.72 |
| Unrealized Gain/Loss | **−$14,344.30 (−38.1%)** |
| Portfolio Weight | 4.81% (2nd largest individual equity position) |
| Capital Category | MID cap |
| Geography | US |
| ESS Signal | NEUTRAL |
| Opportunity Flag | HOLD |
| Replay Supported | Unknown — no replay coverage for MID/NEUTRAL range |
| Overweight vs Target | To be evaluated by node |

---

## Why FIS Is a Clear Action Candidate

### Factor 1: Unrealized Loss Magnitude
FIS represents a **−$14,344.30 unrealized loss** — the largest unrealized loss in the entire 81-position portfolio by a significant margin. For context:

- **Available gain capacity:** $24,730 (from `net_realized_ytd = −$24,730`)
- **FIS loss as % of capacity:** 58.0% of available gain capacity could be realized through this one position
- Harvesting FIS's loss partially offsets the operator's accumulated $24,730 negative YTD realized position and rebuilds future capacity

This is a **Category 5 (Loss Harvest)** candidate by definition.

### Factor 2: Former Employer Stock
FIS is a former employer stock position. The operator has no future purchase intent and holds it as a legacy position. This is precisely the profile of a **Category 2 (Strategic Exit)** candidate:

- No business reason to hold
- No conviction in future outperformance (NEUTRAL signal confirms neutral analyst outlook)
- Carrying psychological anchoring risk (hoping to "get back to cost basis")
- Concentration risk: at 4.81% of portfolio, it is a meaningful single-stock position with negative alpha

### Factor 3: NEUTRAL Signal Is Not a Hold Signal
The ESS `signal_direction = NEUTRAL` indicates the analytical consensus is neither optimistic nor pessimistic about FIS. Critically, **NEUTRAL does not mean "hold forever."** It means:

- The security is not screened out as BEARISH
- It is also not flagged for accumulation
- No replay support — FIS is not a replay-validated high-return profile
- No strategic alpha case — the position exists because of its history, not its forward opportunity

A NEUTRAL signal on a −38.1% loss position with no strategic reason to hold is stronger evidence for action than a BEARISH signal on a break-even position.

### Factor 4: No Allocation Need
There is no identified allocation underweight that FIS would fill by being retained. The allocation nodes where FIS resides are not under-allocated. Exiting FIS does not create an allocation gap.

---

## Current Framework Handling of FIS

**FIS does not appear in the Tax-Aware Actions panel.**

Execution trace through `_computeTaxActions()`:

```
signal = ov.ess_direction || ov.signal_direction  → "NEUTRAL"
flag   = ov.recommended_action || ""               → ""
cwdas  = ov.cw_das_flag || ""                      → ""

isPoorOutlook    = ("NEUTRAL" === "BEARISH") || ("" === "TRIM")   → false
isBuyCandidate   = ("" === "BUY") || ("NEUTRAL" === "BULLISH")    → false
isReduceCandidate = ("" === "TRIM") || ("" === "REDUCE_CANDIDATE") → false

hasGainData = !isNaN(costBasis) && !isNaN(marketValue)  → false (fields absent from overlay)

Check 1 (Bucket D — harvest loss):  isPoorOutlook && unrealizedGL < 0  → false (isPoorOutlook = false)
Check 2 (Bucket E — hold gain):     isBuyCandidate && unrealizedGL > 0  → false
Check 3 (Bucket A — gain, poor):    isPoorOutlook && unrealizedGL > 0  → false
Check 4 (Bucket C — reduce):        isReduceCandidate && unrealizedGL != null  → false
Check 5 (Bucket A — fallback):      isPoorOutlook && unrealizedGL == null  → false (isPoorOutlook = false)

RESULT: No bucket assigned → FIS does not appear
```

**The framework does not even reach the loss evaluation step for FIS.** It is filtered out at the signal check before any financial analysis occurs.

---

## Should FIS Appear in Tax-Aware Actions?

**Yes, unambiguously.**

FIS should appear under **two categories** simultaneously:

| Category | Classification | Priority |
|---|---|---|
| Category 2: Strategic Exit | Former employer stock, no forward conviction, legacy position | HIGH |
| Category 5: Loss Harvest | −$14,344 unrealized loss, within available capacity window | HIGH |

**Recommended action:** SELL NOW  
**Tax context:** Harvesting this loss converts $14,344 of potential losses into realized losses, partially offsetting the existing $24,730 negative YTD position and contributing to the $38,966 projected gain capacity.  
**Timing:** No deferral benefit — position is already at a deep loss with no LT/ST distinction that favors deferral.

---

## Validation of the Framework Architectural Gap

FIS is the clearest possible validation that the current framework operates on the wrong dimension.

| Dimension | FIS Value | Current Framework Detection |
|---|---|---|
| Signal quality | NEUTRAL (not poor) | ❌ Framework requires BEARISH |
| Unrealized return | −38.1% (worst in portfolio) | ❌ Framework cannot read cost basis |
| Strategic fit | Former employer, no forward intent | ❌ Framework has no strategic layer |
| Tax opportunity | $14,344 harvestable loss | ❌ Framework cannot detect losses |
| Allocation role | No allocation dependency | ❌ Framework has no allocation layer |

If the framework were working correctly, FIS would be the **highest-priority action candidate** in the Tax-Aware Actions panel. Instead, it is completely invisible.

---

## FIS Before/After Comparison

**Before Phase 23.0B (current state):**
- FIS not present in Tax-Aware Actions panel
- No action recommendation surface
- Operator must manually identify FIS as an action candidate

**After Phase 23.0B (target state):**
- FIS appears in panel with two category tags: Strategic Exit + Loss Harvest
- Priority: HIGH
- Display: FIS | −$14,344 loss | Former employer stock | Harvest now: absorbs 58% of gain capacity
- Tax context: Loss can be applied against existing negative YTD balance; advances projected capacity to $38,966+

---

## Note on Data Availability

The FIS case study depends on `cost_basis` and `market_value` being available per holding. These fields are currently present in `holdings.csv` but not propagated into `SecurityIntelligenceOverlay`. Phase 23.0B implementation will require either:

1. Enriching the overlay with `cost_basis` and `market_value` from `holdings.csv` at build time, OR
2. Having the JS client read a separate holdings data structure alongside the overlay

This is an implementation detail scoped to Phase 23.0C. The Phase 23.0B framework design assumes these fields will be available at render time.
