# Q7 — Cash UI Certification
## Workstream B: SPAXX / Cash Equivalent Governance Certification

**Investigation run:** PAR-20260602-1BF2ADA5  
**Generated:** Phase 22D — Workstream B  
**Scope:** All UI panels — SPAXX and cash-equivalent rendering in portfolio_alignment and allocation_intelligence UIs  

---

## Verdict: SPAXX Renders Correctly as Cash at All UI Locations

No UI panel shows SPAXX as an ETF, mutual fund, equity position, security candidate, conviction holding, or deployment target. SPAXX is rendered as:
1. A cash allocation metric (% of portfolio, cash available gauge)
2. A MAINTAIN-labeled holding in the UCF holdings table
3. A funding source narrative ("Excess Cash")

---

## Section 1 — Allocation Intelligence UI (`ui/allocation_intelligence/app.js`)

### 1a — CASH Node Color Assignment
**Line 22:**
```javascript
CASH: "#6b8e77",
```
CASH is mapped to its own color category — separate from EQUITIES, FIXED_INCOME, DIGITAL, COMMODITIES.

### 1b — L1 Allocation Node List
**Line 216:**
```javascript
const l1Keys = ["EQUITIES", "FIXED_INCOME", "DIGITAL", "COMMODITIES", "CASH"];
```
CASH appears as the 5th (last) L1 node. It is enumerated in the same loop as all other L1 nodes but rendered in its own allocation bar segment with the `#6b8e77` color.

### 1c — Strategy Card: Cash Floor
**Line 142:**
```javascript
{ label: "Cash Floor", value: `${sp.cash_floor_pct ?? "—"}%` },
```
The strategy card shows the mandate's cash floor percentage (`sp.cash_floor_pct = 2.0%` for CONCENTRATED_ALPHA). This is a governance display of the minimum cash reserve — not a reference to SPAXX specifically.

### 1d — "CASH (floor check)" Gauge
**Lines 497–500:**
```javascript
{
  label: "CASH (floor check)",
  value: parseFloat(targets.find(t => t.node_key === "CASH")?.target_pct_of_total || 0),
  ceiling: 100,
  floor: sp.cash_floor_pct ?? 2,
  ac: "CASH",
}
```
A dedicated CASH gauge shows the target % vs the mandate floor. SPAXX's market value feeds this gauge through the CASH node alignment (`actual_pct = 8.6592%`). The gauge label is "CASH (floor check)" — not "SPAXX" and not "Money Market Fund."

### 1e — Allocation Target Table
**Lines 451, 538, 544:**
The allocation target table renders `node_key` values from the alignment data. CASH row will show:
```
CASH | actual: 8.66% | target: 7.0% | drift: +1.66%
```
The symbol "SPAXX" never appears in this table. The table deals in node keys, not individual symbols.

---

## Section 2 — Portfolio Alignment UI (`ui/portfolio_alignment/app.js`)

### 2a — ETF Contributors Rendering
**Lines 1349–1357:**
```javascript
// Phase C — ETF contributors
const contributors = r.etf_contributors || [];
const etfBarHtml = contributors.length > 0
  ? `<div class="rec-etf-bar">
       <span class="rec-etf-label">ETF contributors:</span>
       ${contributors.map(s => `<span class="rec-etf-chip">${s}</span>`).join("")}
     </div>`
  : "";
```

In the current run (PAR-20260602-1BF2ADA5), SPAXX does NOT appear in any recommendation's `etf_contributors` array. This was the Phase 6.3D bug — now fixed by the guard in `recommendations.py:1346–1347`.

The `etf_contributors` array for CASH recommendations is empty, so the `ETF contributors:` bar does not render at all for the CASH recommendation card. ✅

### 2b — Cash Impact Gauge (Deployment Planner)
**Line 2212:**
```javascript
<div class="da-cash-val">
  ${pi.cash_before_pct != null ? parseFloat(pi.cash_before_pct).toFixed(1) : "—"}% →
  ${pi.cash_after_pct != null ? parseFloat(pi.cash_after_pct).toFixed(1) : "—"}%
</div>
```
The deployment action card shows "Cash: 8.7% → X.X%", where 8.7% is derived from SPAXX's `percent_of_portfolio`. This is correct: SPAXX is the cash being depleted by equity purchases.

**Line 2594:**
```javascript
<div class="dp-impact-val">
  ${pct(impact.cash_before_pct)} → <span class="dp-green">${pct(impact.cash_after_pct)}</span>
</div>
```
Second render location (deployment plan card) shows the same cash impact. Both locations display SPAXX's value as an aggregate cash metric, not a security symbol.

---

## Section 3 — UCF Dashboard (`ui/ucf_operator_dashboard/index.html`)

SPAXX appears in the UCF holdings table with the following rendering:

| Field | Rendered Value | Notes |
|-------|---------------|-------|
| Symbol | SPAXX | Symbol column |
| UCF Label | MAINTAIN | Green/neutral badge |
| UCF Score | 0.0 | Numeric score column |
| UCF Rank | 73 | Rank = last (lowest priority) |
| Deployment Eligible | — / None | No deployment badge |
| CW-DAS Score | — / None | No scoring value |

SPAXX is NOT shown with:
- A conviction tier badge (DEPLOYMENT_CANDIDATE, HIGH_CONVICTION_ANCHOR, etc.)
- A deployment priority indicator
- An ESS signal bar
- A replay indicator

---

## Section 4 — No Direct Symbol Reference in UI

A search across all UI JS files confirms:
- `SPAXX` does not appear as a hardcoded string in any UI JavaScript
- `VMFXX`, `FZFXX`, `FDRXX`, `SPRXX`, `FCASH` do not appear as hardcoded strings in any UI JavaScript
- Cash symbols are never directly referenced in UI code — they flow through as data from `holdings.csv` / `security_overlays.csv`

The UI renders cash purely based on:
1. `node_key = "CASH"` from alignment data
2. `cash_before_pct / cash_after_pct` from `portfolio_impact` (computed from `is_cash_equivalent` flag)
3. `ucf_label = "MAINTAIN"` from UCF verdicts

---

## Section 5 — Certification Items

| UI Panel | SPAXX/Cash Rendering | ETF Risk | Status |
|----------|---------------------|----------|--------|
| Allocation Intelligence — L1 allocation bar | CASH node segment | None | ✅ PASS |
| Allocation Intelligence — Strategy card | "Cash Floor: 2.0%" | None | ✅ PASS |
| Allocation Intelligence — CASH gauge | Gauge with actual/target/floor | None | ✅ PASS |
| Portfolio Alignment — ETF contributors | NOT rendered (etf_contributors empty) | None | ✅ PASS |
| Portfolio Alignment — Cash impact gauge | "8.7% → X.X%" (aggregate) | None | ✅ PASS |
| Portfolio Alignment — Deployment plan cash | "8.7% → X.X%" (aggregate) | None | ✅ PASS |
| UCF Dashboard — Holdings table | MAINTAIN, 0.0, rank 73 | None | ✅ PASS |
| Conviction overlay table | Does not appear (no composite score) | None | ✅ PASS |
| Signal profile panels | HOLD flag, no signal data shown | None | ✅ PASS |

---

## Section 6 — Known Open Item (UI Risk Registry)

**Item:** SPAXX still appears in `config/etf_exposure_decomposition.yaml`.

If the behavioral guard in `recommendations.py:1346-1347` were ever removed or bypassed, SPAXX could reappear in `etf_contributors` arrays, causing the `ETF contributors: SPAXX` label to render in the Portfolio Alignment recommendation card.

**Current risk:** NONE — guard is in place and regression-tested (see `test_cash_as_etf_contributor_detected` in `tests/test_reconciliation.py:458`).

**Mitigation:** Remove SPAXX, VMFXX, FZFXX from `etf_exposure_decomposition.yaml` in a future cleanup pass. This would eliminate the REGISTRY-sourced stale metadata and remove the dependency on the behavioral guard.
