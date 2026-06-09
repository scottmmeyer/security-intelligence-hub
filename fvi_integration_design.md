# FVI Integration Design

Repository: security-intelligence-hub  
Date: 2026-06-09

## Integration Scope

FVI is advisory-only. It provides vehicle quality context to existing recommendation surfaces. It does not alter:
- CW-DAS composite scores
- ESS signal values
- STI profiles or conviction tiers
- Alignment calculations or drift percentages
- Recommendation generation logic

FVI outputs are additive overlays on existing recommendation outputs.

---

## Phase 1: Advisory Overlay (Recommended Initial Scope)

### Allocation Reduction Surface

FVI label is displayed alongside each fund in an REDUCE_OVERWEIGHT recommendation's affected_symbols list.

**Example — Current behavior without FVI:**
> Reduce EQUITIES.INTERNATIONAL.LARGE (+4.2% drift)
> Symbols: SBS, DODFX, VXUS, VEA, FIGFX

**With FVI overlay:**
> Reduce EQUITIES.INTERNATIONAL.LARGE (+4.2% drift)
> SBS — no FVI data (individual equity)
> DODFX — 🟡 FVI: HIGH (75/100) · Foreign Large Value · Retain preferred
> VXUS — 🟢 FVI: ELITE (80/100) · Total International ETF
> VEA — 🟢 FVI: ELITE (82/100) · Foreign Large Blend ETF
> FIGFX — 🟡 FVI: MEDIUM (55/100) · Foreign Large Growth MF (active)

**Decision guidance generated:**
> "International sleeve reduction recommended. Quality assessment suggests reducing FIGFX (MEDIUM) before DODFX (HIGH) if partial reduction is possible."

### Funding Sources Surface

FVI quality label modifies funding source priority ordering.

**Rule:** Within the same funding source category, lower FVI tier = higher liquidation priority.

Example:
- DODFX (HIGH, SELL_LAST): last resort funding source
- FIGFX (MEDIUM): earlier funding candidate if available

### CRA Surface

For CRA capital pool construction, FVI provides a vehicle-quality weighting:
- ELITE/HIGH vehicles: reduce sizing_pct suggestion (preserve quality)
- LOW/WEAK vehicles: increase sizing_pct suggestion (liquidate inferior vehicle)

**Constraint:** CRA does not alter the execution_state or policy logic. FVI is an additive advisory input to the sizing recommendation, not a gate.

### PAP Surface

For PAP Cat 3 (Allocation Reduction), FVI labels appear alongside reduction candidates:
- A SELL_LAST + HIGH fund is shown with "Quality: HIGH — prefer retaining over lower-quality peers"
- A LOW fund is shown with "Quality: LOW — consider as priority reduction candidate"

---

## Phase 2: Policy-Gated Recommendation Influence (Post-Validation Only)

After Phase 1 advisory validation, FVI may be promoted to a soft policy gate:

**Rule proposal for Phase 2:**
> If two funds are both candidates for the same sleeve reduction, prefer reducing the lower-FVI vehicle first, all else equal.

This requires:
1. Phase 1 advisory data validated in production
2. Multi-quarter evidence that FVI labels are stable and accurate
3. Formal governance approval

Phase 2 is NOT in scope for current implementation.

---

## Integration Rule Document

### Rule FVI-R01: Allocation Reduction Vehicle Priority

When a REDUCE_OVERWEIGHT recommendation lists multiple fund vehicles:
- Display FVI tier alongside each fund in the affected_symbols list
- If all other factors equal and FVI data is available, suggest reducing the lowest-FVI vehicle first
- Advisory only — operator retains execution authority

### Rule FVI-R02: Funding Sources Last-Resort

When a fund vehicle has FVI tier HIGH or ELITE:
- Display advisory: "Quality vehicle — consider as last-resort funding source"
- This is advisory context, not an execution gate (execution gates are the policy system's domain)

### Rule FVI-R03: Policy + FVI Combined Display

When a fund carries both a policy annotation and an FVI tier:
- Display both as independent, non-conflicting advisory elements
- Example: DODFX · ⏸ Sell Last · 🟡 FVI: HIGH
- Do not merge or compound these signals

### Rule FVI-R04: No FVI for Individual Equities

FVI is not applied to individual equities (TSLA, DODFX's holdings, etc.). It applies only to fund vehicles: mutual funds, ETFs, CEFs, digital asset funds.

---

## Governance Model

| Can FVI Influence | Yes/No | Mechanism |
|---|---|---|
| Display in allocation reduction cards | Yes | Advisory label overlay |
| Funding source display ordering suggestion | Yes | Advisory recommendation text |
| PAP Cat 3 ordering suggestion | Yes | Advisory label |
| CRA sizing advisory | Yes | Advisory input |
| CW-DAS composite score | **No** | Not permitted |
| ESS signal | **No** | Not permitted |
| STI conviction tier | **No** | Not permitted |
| Portfolio alignment calculations | **No** | Not permitted |
| Recommendation generation logic | **No** | Not permitted |
| Execution blocking | **No** | Policy system only |

---

## Scenario Analysis

### Scenario A: Two funds, same sleeve, one ELITE, one LOW, sleeve reduction needed

**Portfolio:** FIGFX (MEDIUM, 0.27%) and DODFX (HIGH, 3.21%) both in INTERNATIONAL.LARGE

**Sleeve:** INTERNATIONAL.LARGE overweight +4.2pp

**FVI advisory output:**
- FIGFX: MEDIUM quality — candidate for priority reduction
- DODFX: HIGH quality — prefer to retain; last resort only

**Combined with policy:** DODFX also has SELL_LAST — double deferral signal.

**SIH advisory:** "International Large reduction needed. FIGFX (MEDIUM quality) is the preferred reduction candidate over DODFX (HIGH quality, SELL_LAST)."

### Scenario B: All funds same FVI tier

**Portfolio:** VEA (ELITE) and VXUS (ELITE) both in INTERNATIONAL.LARGE

**FVI advisory output:** Both ELITE — no vehicle-quality basis for preferring one over the other. Reduce by portfolio weight or drift contribution.

### Scenario C: No FVI data available for a fund

**Policy:** Graceful degradation. If FVI data is unavailable for a symbol, no FVI label is shown and no FVI-based advisory is generated. The existing recommendation is presented unchanged.

---

## Data Contract for FVI Output

Each fund vehicle in the portfolio will have an optional FVI record:

```json
{
  "symbol": "DODFX",
  "fvi_score": 75,
  "fvi_tier": "HIGH",
  "peer_group": "Foreign Large Value",
  "peer_percentile_estimate": 30,
  "expense_ratio_pct": 0.63,
  "data_source": "MANUAL_ADVISORY_ESTIMATE",
  "data_as_of": "2026-06-09",
  "confidence": "MEDIUM",
  "retain_advisory": true,
  "advisory_text": "Retain as preferred vehicle. HIGH quality in peer group. Prefer over lower-quality International Large exposure."
}
```

`data_source` values:
- `MANUAL_ADVISORY_ESTIMATE` — Phase 1 manual configuration
- `MORNINGSTAR_API` — Phase 2 live data integration
- `LIPPER_API` — Phase 2 alternative

---

## Implementation Prerequisites

| Prerequisite | Status | Notes |
|---|---|---|
| PRA-IMPL-01 card_type contract | COMPLETE | FVI data will ride on existing card fields |
| PRA-IMPL-02 policy-aware surfaces | COMPLETE | FVI + policy display on same card is already supported |
| PRA-IMPL-03 lane separation | COMPLETE | FVI overlay on ACTION lane cards |
| Peer group configuration file | PENDING | Must be created before implementation |
| FVI data source (Phase 1 manual) | PENDING | Manual YAML or JSON for 15 portfolio funds |
