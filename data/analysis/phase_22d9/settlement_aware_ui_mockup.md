# Phase 22D.9 — Workstream D: Settlement-Aware UI Design Mockup

**Phase:** 22D.9 — Settlement-Aware Deployable Cash  
**Date:** 2026-06-02  
**Design Option:** Option B (dual display; recommended)  
**Reference:** `ui/portfolio_alignment/app.js`

---

## 1. Current State: Cash Deployment Panel (No Pending Activity)

When no `ACCOUNTING_ADJUSTMENT` rows are present, the current panel renders correctly.
No changes are needed for the no-pending case:

```
┌─────────────────────────────────────────────────────┐
│  CASH DEPLOYMENT                                     │
├─────────────────────────────────────────────────────┤
│  Cash Position                                       │
│    Current Cash:         8.62%    ($41,530)          │
│    Mandate Target:       7.00%                       │
│    Cash Floor:                    ($33,621)          │
│                                                      │
│  Deployable Cash:                 $7,909             │
└─────────────────────────────────────────────────────┘
```

**Trigger condition for settlement-aware display:** `adjusted_deployable_mv` is present
in `cash_context` AND `adjusted_deployable_mv !== deployable_mv`.

---

## 2. Proposed State: Cash Deployment Panel (Pending Activity Present)

When negative `ACCOUNTING_ADJUSTMENT` rows are detected, the panel adds a settlement
section below the cash position block:

```
┌─────────────────────────────────────────────────────┐
│  CASH DEPLOYMENT                                     │
├─────────────────────────────────────────────────────┤
│  Cash Position                                       │
│    Current Cash:         8.59%    ($41,279)          │
│    Mandate Target:       7.00%                       │
│    Cash Floor:                    ($33,621)          │
│                                                      │
│  ⚠  PENDING SETTLEMENT                               │
│    Pending Activity:             -$3,567             │
│    Settled Cash (est.):  7.85%   ($37,713)           │
├─────────────────────────────────────────────────────┤
│  Deployable Cash                                     │
│    Reported:             $7,658   (pre-settlement)   │
│    Adjusted:             $4,092   (post-settlement)  │
│                                                      │
│  ← Use Adjusted figure for deployment decisions.     │
│    Pending activity will settle by Jun 3, 2026.      │
└─────────────────────────────────────────────────────┘
```

---

## 3. Annotated Field Map

| UI Label | Data Source | Calculation |
|----------|-------------|-------------|
| Current Cash % | `cash_context.cash_pct` | SPAXX / total_mv × 100 |
| Current Cash ($) | `cash_context.cash_mv` | SPAXX balance |
| Mandate Target | `cash_context.mandate_cash_target_pct` | From archetype config |
| Cash Floor | `cash_context.floor_mv` | total_mv × target_pct |
| Pending Activity | `cash_context.pending_settlement_mv` | Sum of negative ACCOUNTING_ADJUSTMENT MVs |
| Settled Cash % | `cash_context.adjusted_cash_pct` | adjusted_cash_mv / total_mv × 100 |
| Settled Cash ($) | `cash_context.adjusted_cash_mv` | cash_mv + pending_settlement_mv |
| Deployable (reported) | `cash_context.deployable_mv` | max(0, cash_mv − floor_mv) |
| Deployable (adjusted) | `cash_context.adjusted_deployable_mv` | max(0, adjusted_cash_mv − floor_mv) |

All `pending_settlement_*` and `adjusted_*` fields are NEW additions to `cash_context`.
They are absent when no pending activity exists; the settlement section is suppressed.

---

## 4. Suppression Logic

The settlement section should be shown if and only if:

```javascript
const hasPendingSettlement = cashCtx.pending_settlement_mv != null
                              && cashCtx.pending_settlement_mv < 0;
```

When `hasPendingSettlement === false`, render the current single-figure panel unchanged.

This ensures zero UI regression for runs without pending activity.

---

## 5. Color / Icon Guidance

| Element | Style | Rationale |
|---------|-------|-----------|
| `⚠ PENDING SETTLEMENT` header | Amber/orange | Non-blocking caution; settlement is expected |
| Pending Activity row | Amber text | Same caution level; not an error |
| Reported Deployable | Gray / muted | Secondary figure; not the primary action number |
| Adjusted Deployable | Bold / primary | This is the number the operator acts on |
| "Use Adjusted figure" note | Italic, secondary | Guidance, not a warning |

---

## 6. Settlement Date Estimation

The panel shows "Pending activity will settle by [date]." The settlement date should be
estimated as T+1 from `snapshot_date`:

```javascript
const settlementDate = new Date(snapshot.snapshot_date);
settlementDate.setDate(settlementDate.getDate() + 1);
// Skip weekends (Fidelity T+1 is business days)
while (settlementDate.getDay() === 0 || settlementDate.getDay() === 6) {
  settlementDate.setDate(settlementDate.getDate() + 1);
}
```

If `snapshot_date` is not available, omit the settlement date line entirely.

---

## 7. Behavior When Adjusted > Reported (Future Edge Case)

It is theoretically possible for a positive `ACCOUNTING_ADJUSTMENT` row to exist
(e.g., a pending dividend credit). In this case, `adjusted_deployable_mv > deployable_mv`.

In that scenario, the labeling should change:
- "Reported: $X (pre-settlement)"
- "Adjusted: $Y (includes pending credit)"

The suppression logic should key on `pending_settlement_mv != null && pending_settlement_mv !== 0`
(handle both positive and negative pending activity symmetrically).

For the current SIH data set, only negative (debit) adjustments have been observed.
This edge case is forward-looking only.

---

## 8. Relationship to Existing UI Code

| Existing code location | Change needed |
|------------------------|---------------|
| `app.js` line 2050: `const cashCtx = dq.cash_context \|\| {}` | No change needed |
| `app.js` lines 2062–2091: renders `mandate_cash_target_pct`, `cash_pct`, `deployable_mv` | No change to existing rendering |
| New block after line 2091 | Add settlement section conditional on `hasPendingSettlement` |
| `app.js` line 2204: renders `cashCtx.deployable_mv` in summary | Optionally annotate "(reported)" if pending exists |
