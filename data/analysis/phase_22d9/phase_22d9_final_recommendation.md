# Phase 22D.9 — Final Recommendation: Settlement-Aware Deployable Cash

**Phase:** 22D.9 — Settlement-Aware Deployable Cash  
**Date:** 2026-06-02  
**Author:** SIH Analysis Pipeline  
**Status:** FINAL

---

## Executive Summary

Phase 22D.8A established that SIH is behaving as designed: PENDING ACTIVITY rows are
correctly classified as `ACCOUNTING_ADJUSTMENT`, excluded from the investable holdings
set, and do not distort the core cash calculation mechanics. However, `cash_mv` is
sourced from SPAXX pre-settlement, which overstates the operator's true deployable
capacity by exactly the pending settlement amount.

This phase completes the design analysis and delivers an actionable recommendation.

**Recommendation: Implement Option B (dual display) in a near-term development sprint.**

---

## Findings by Workstream

### Workstream A — Design Options

Three options were evaluated:

| Option | Behavior | Recommendation |
|--------|----------|----------------|
| A — Warning only | No math change; banner warns of pending activity | Not sufficient; operator must do mental math |
| **B — Dual display** | Advisory `adjusted_deployable_mv` added; reported figure unchanged | **Recommended** |
| C — Change operative calc | `compute_deployable_cash()` uses adjusted cash_mv | Deferred; governance change required |

**Option B is recommended** because it gives the operator the correct deployment figure
while preserving the accounting record, avoiding mandate governance changes, and
presenting minimal regression risk.

### Workstream B — Accounting Adjustment Inventory

57 ACCOUNTING_ADJUSTMENT rows were found across all 57 historical analysis runs that
contain pending activity. 100% of observed adjustments are of a single type:

> **Pending Purchase Settlement** — Fidelity T+1 debit for equity purchase execution

No other adjustment types (dividends, transfers, journal entries) have been observed in
SIH history. All observed adjustments classify as `SAFE_TO_OFFSET_CASH`.

Key observation: The same source CSV is often loaded into multiple run IDs during
exploratory analysis phases. The unique source file timestamps are:

| Fidelity Export Date | Pending Amount | Purchase |
|---------------------|----------------|---------|
| May 22, 2026 | -$4,344.91 | Unknown (pre-PRG) |
| May 28, 2026 | -$4,236.41 | Unknown (brokerage acct) |
| May 29, 2026 | -$1,500.00 | Unknown (individual acct) |
| Jun 02, 2026 | -$3,566.55 | PRG (PROG HOLDINGS) |

Every pending amount has disappeared by the next available export — confirming the T+1
settlement pattern.

### Workstream C — Adjusted Cash Model Validation

For the Phase 22D.9 reference run (PAR-20260602-8CF1CB84):

| Metric | Reported | Adjusted | Delta |
|--------|----------|----------|-------|
| Cash MV | $41,279.15 | $37,712.60 | -$3,566.55 |
| Cash % | 8.59% | 7.85% | -0.74 pp |
| Deployable MV | $7,658.25 | $4,091.70 | -$3,566.55 |

The adjusted model is arithmetically validated. The overstatement ($3,566.55) equals
`|PENDING ACTIVITY|` exactly — no rounding, no hidden factors.

**Mandate floor safety check:** Even the adjusted figure ($4,091.70 > $0) keeps the
portfolio above the 7.0% mandate floor post-settlement. No mandate breach is imminent
from this specific run. However, if the operator deploys the full reported figure
($7,658.25) before settlement, the post-settlement cash would fall to:

$$\$41{,}279.15 - \$3{,}566.55 - \$7{,}658.25 = \$30{,}054.35$$

$$\frac{\$30{,}054.35}{\$480{,}298.55} = 6.26\% < 7.0\% \text{ (mandate breach)}$$

This confirms that deploying the full reported figure creates a mandate breach at T+1.
The adjusted figure ($4,091.70) is the safe deployment amount.

### Workstream D — UI Design Mockup

A conditional settlement panel is designed for `ui/portfolio_alignment/app.js`:
- Triggered only when `pending_settlement_mv < 0` is present in `cash_context`
- Shows: current cash, pending debit, adjusted cash %, reported deployable, adjusted deployable
- Suppressed entirely when no pending activity exists — no UI regression
- Settlement date estimated as T+1 from `snapshot_date` (business days)

### Workstream E — Implementation Impact Assessment

Option B requires changes to two files:

1. **`src/portfolio/runner.py`** — ~15-line block after `compute_deployable_cash()` call;
   computes `pending_settlement_mv`, `adjusted_cash_mv`, `adjusted_cash_pct`,
   `adjusted_deployable_mv`, `adjusted_deployable_pct` and updates `cash_context` dict
2. **`ui/portfolio_alignment/app.js`** — conditional settlement panel after line 2091

Regression risk is **very low**:
- `compute_deployable_cash()` is not modified
- `deployment_plan.deployable_cash` is not changed
- New fields are additive and optional (absent when no pending activity)
- Phase 22D.6 certification run (PAR-20260602-4A83D5BD) is unaffected

---

## Decision Questions and Answers

**Q1: Should SIH remain accounting-correct only?**  
No. The current behavior is technically correct but operationally misleading. An operator
who sees $7,658 of deployable cash and acts on it will breach the mandate floor at T+1
settlement. The system should inform the operator of this risk.

**Q2: Should SIH become settlement-aware?**  
Yes. The T+1 Fidelity settlement pattern has been observed across 4 distinct export dates
and is a structural feature of the data, not a one-time anomaly. Settlement awareness is
a permanent requirement.

**Q3: Which implementation option?**  
Option B (dual display). It satisfies the operator's decision-making need without changing
any governance-operative calculation. Option C is the stronger long-term solution but
requires governance approval and test restructuring before it can be implemented safely.

**Q4: What does the operator see today (without this change) when pending activity is present?**  
A single deployable cash figure of $7,658 with no indication that $3,567 of that cash
is already committed. No warning. No qualification. The operator cannot distinguish
between "cash I own" and "cash I can deploy."

**Q5: What would the operator see after Option B is implemented?**
```
Current Cash:    8.59%  ($41,279)
Pending:        -$3,567 (unsettled activity)
Adjusted Cash:   7.85%  ($37,713)

Deployable (reported):  $7,658   ← pre-settlement balance
Deployable (adjusted):  $4,092   ← accounting for pending settlement
Use adjusted figure for deployment decisions.
Settlement expected Jun 3, 2026.
```

**Q6: Does this improve decision quality?**  
Yes. The gap between reported and adjusted is $3,566.55 on a $480,298 portfolio — 0.74
percentage points of cash. In a mandate-constrained portfolio at 8.59% cash (only 1.59 pp
above the 7.0% floor), this represents a 47% overstatement of deployable capacity.

**Q7: Is Option C safe to implement now?**  
No. It requires: (1) updating all `deployable_mv` assertions in `test_7_5b_deployment_queue.py`,
(2) governance approval for changing the operative cash calculation, (3) classification
guard to ensure only purchase-settlement rows are offset. These conditions are not met
in Phase 22D.9.

---

## Implementation Sequence (If Approved)

1. Implement backend augmentation in `src/portfolio/runner.py` (15 lines)
2. Implement conditional UI panel in `ui/portfolio_alignment/app.js`
3. Write 4 new unit tests (see Workstream E Section 5)
4. Restart server; re-ingest PAR-20260602-8CF1CB84 CSV
5. Verify `adjusted_deployable_mv = $4,092` appears in `cash_context`
6. Verify PAR-20260602-4A83D5BD re-run has no `adjusted_*` fields (no pending activity)
7. Certify as Phase 22D.9 implementation complete

**No governance changes required for Option B.**  
The mandate floor, cash target, and compliance measurement are all unchanged.

---

## Phase 22D.9 Deliverable Register

| Deliverable | Status |
|-------------|--------|
| `settlement_aware_design_options.md` | ✅ Complete |
| `accounting_adjustment_inventory.csv` | ✅ Complete |
| `adjusted_cash_model_validation.md` | ✅ Complete |
| `settlement_aware_ui_mockup.md` | ✅ Complete |
| `settlement_aware_impact_assessment.md` | ✅ Complete |
| `phase_22d9_final_recommendation.md` | ✅ Complete (this document) |

**Phase 22D.9 analysis is complete.**  
Implementation of Option B is ready to proceed on operator/governance approval.
