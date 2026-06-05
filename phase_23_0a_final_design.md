# Phase 23.0A — Tax-Aware Portfolio Actions (MVP)
## Final Design Document

**Date:** 2026-06-02  
**Status:** IMPLEMENTED  
**Scope:** Portfolio Alignment UI enhancement — tax context as a decision modifier

---

## Design Principle

> SIH currently asks: "What should I buy?"
>
> Phase 23.0A adds: "What should I buy, sell, trim, hold, or defer given my current tax position?"
>
> **Taxes are a decision modifier — not a decision driver.**

The primary workflow remains conviction-first:

1. Identify portfolio actions
2. Evaluate conviction deterioration
3. Evaluate mandate alignment
4. Evaluate replay intelligence
5. **Evaluate tax consequences** ← Phase 23.0A
6. Prioritize actions

---

## Delivered Features

### Feature 1 — Tax Context Panel ✓

Collapsible card at the bottom of the Portfolio Upload section.

**Inputs:**
- Net Realized Gain/Loss YTD
- Potential Additional Losses
- Capital Loss Carryforward
- Tax Year

**Computed in real time:**
- Available Gain Capacity = max(0, −Net Realized YTD + Carryforward)
- Projected Gain Capacity = Available + Potential Additional Losses

**Example:**
```
Net Realized YTD:            -$24,730
Potential Additional Losses:  $14,236
Carryforward:                     $0

Available Gain Capacity:     $24,730
Projected Gain Capacity:     $38,966
```

### Feature 2 — Persistent Operator State ✓

Tax inputs persist server-side in:
```
data/operator/portfolio_alignment_state.json
```

Survival guarantees: page refresh ✓ · server restart ✓ · browser restart ✓

API:
- `GET /api/operator/tax-state` — load persisted state
- `POST /api/operator/tax-state` — merge and save state

### Feature 3 — Tax-Aware Action Columns ✓

New table below Security Intelligence Overlay:

| Column | Notes |
|---|---|
| Priority | Integer rank by bucket + impact magnitude |
| Symbol | From security overlays |
| Current Action | SIH recommended action badge |
| Tax Impact | Unrealized G/L from cost basis (optional, shows — when absent) |
| Holding Period | Days held + LT/ST label |
| Tax Category | Long-Term Gain / Short-Term Gain / Capital Loss / N/A |
| Recommended Timing | SELL NOW / WAIT / HARVEST LOSS / HOLD DESPITE GAIN |
| Reason | Plain-English rationale |

### Feature 4 — Action Prioritization Buckets ✓

| Bucket | Name | Primary Criteria |
|---|---|---|
| A | SELL NOW | Poor outlook + gain shielded or LT rate |
| B | SELL WHEN LONG-TERM | Poor outlook + ST gain, no shield |
| C | SELL FOR REBALANCING | Mandate drift / reduce candidate |
| D | HARVEST LOSS | Poor outlook + unrealized loss |
| E | HOLD DESPITE GAIN | High conviction / bullish signal + gain |

### Feature 5 — Tax-Aware Sell Candidates Table ✓

Full-width table in results area, grouped by bucket with colored timing badges.
Shown automatically when actionable holdings are present.

---

## Implementation Details

### Files Modified

| File | Change |
|---|---|
| `scripts/run_outcome_ui.py` | Added `GET /api/operator/tax-state` and `POST /api/operator/tax-state` endpoints |
| `ui/portfolio_alignment/index.html` | Tax Position Panel HTML + CSS, Tax Action Section HTML, cache bump v5→v6 |
| `ui/portfolio_alignment/app.js` | `_taxState`, `loadTaxState()`, `saveTaxState()`, `updateTaxComputed()`, `_computeTaxActions()`, `renderTaxActionTable()`, `toggleTaxPanel()` |

### Files Created

| File | Purpose |
|---|---|
| `tax_position_panel.md` | Feature 1 design spec |
| `tax_state_persistence.md` | Feature 2 persistence spec |
| `tax_aware_action_framework.md` | Bucket logic + classification spec |
| `portfolio_alignment_tax_columns.md` | Column definitions + badge styles |
| `phase_23_0a_final_design.md` | This document |

---

## Non-Goals (Confirmed Out of Scope)

- Import tax returns
- Calculate tax liability
- Optimize tax lots
- Perform wash-sale analysis
- Create a separate Tax Intelligence workspace

---

## Data Dependency Notes

**Cost basis and holding period are optional inputs.**  
The standard Fidelity CSV export includes `cost_basis` in the holdings data.
Generic CSV format accepts `cost_basis` as an optional column.

When cost basis is absent:
- Tax Impact shows "—"
- Tax Category shows "N/A"
- Bucket assignment falls back to signal/flag logic only (Bucket A or C)

---

## Future Enhancement Candidates

- Short-term → long-term countdown (days to LT threshold)
- Portfolio-level tax impact summary card
- Wash-sale warning flag (28/30-day rule flagging)
- Scheduled harvest recommendations by projected year-end position
