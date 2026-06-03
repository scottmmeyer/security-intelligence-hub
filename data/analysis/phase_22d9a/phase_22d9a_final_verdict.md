# Phase 22D.9A — Final Verdict: CW-DAS Settlement-Aware Deployment Audit

**Phase:** 22D.9A  
**Audit Type:** Forensic — no code changes made  
**Reference Run:** PAR-20260602-8CF1CB84  
**Date:** 2026-06-02  
**Mandate:** CONCENTRATED_ALPHA | `mandate_cash_target_pct = 7.0%`

---

## The Five Audit Questions

### Q1: What cash value drives CW-DAS sizing?

**`cash_context.deployable_mv = $7,658.25`**

This value originates from `compute_deployable_cash()` in `deployment_queue.py`
and is passed directly to `build_deployment_plan()` in `deployment_planner.py`.

```
Audit trace (complete):
  ingestion.py:416       → total_market_value = $480,298.55
  deployment_queue.py:427 → cash_mv = $41,279.15 (SPAXX, is_cash_equivalent=True)
  deployment_queue.py:434 → floor_mv = $33,620.90 (7.0% × $480,298.55)
  deployment_queue.py:439 → deployable_mv = $7,658.25 (cash_mv - floor_mv)
  runner.py:784           → build_deployment_plan(deployable_cash=None)
  deployment_planner.py:115 → deployable_cash = float(cash_ctx["deployable_mv"]) = $7,658.25
  deployment_planner.py:195–240 → suggested_add_i = (w_i / total_w) × $7,658.25
```

The number is the reported (pre-settlement) accounting figure. It does not account
for the -$3,566.55 PENDING ACTIVITY row (`operational_state = ACCOUNTING_ADJUSTMENT`).

---

### Q2: Is CW-DAS economically overstating deployable capital?

**YES — by $3,566.55 (1.871×)**

```
PENDING ACTIVITY balance: -$3,566.55
  Source: Fidelity Individual TOD account (Z35123695)
  Classification: ACCOUNTING_ADJUSTMENT (blank symbol, negative MV)
  Meaning: Unsettled equity purchase; cash committed, debit pending T+1

Settlement-adjusted deployable cash:
  adjusted_cash_mv = $41,279.15 - $3,566.55 = $37,712.60
  adjusted_deployable_mv = $37,712.60 - $33,620.90 = $4,091.70

Overstatement:
  reported - adjusted = $7,658.25 - $4,091.70 = $3,566.55
  oversize factor = $7,658.25 / $4,091.70 = 1.871×
```

---

### Q3: Is the defect merely presentational, or does it affect recommendation sizing?

**It affects recommendation sizing. This is not a display defect.**

The allocation formula in `deployment_planner.py` is:

$$\text{suggested\_add}_i = \frac{w_i}{\sum_j w_j} \times \text{deployable\_cash}$$

Because `deployable_cash = $7,658.25` (reported), every `suggested_add` across all
31 recommended positions is oversized by a factor of 1.871×.

This is not merely a label on a card. It is the basis for trade sizing that an
operator would use to place real equity purchases.

---

### Q4: What policy option is recommended?

**Option C (full remediation) — with Option B as an immediate interim.**

The key escalation from Phase 22D.9 to Phase 22D.9A:

| Phase | Finding | Recommendation |
|-------|---------|---------------|
| 22D.9 | Pending settlement not shown in UI | Option B (display both, no sizing change) |
| **22D.9A** | **Pending settlement directly distorts CW-DAS sizing** | **Option C (adjust cash source for CW-DAS)** |

Phase 22D.9 recommended Option B because the defect appeared presentational.
Phase 22D.9A confirms the defect is in the recommendation engine.
Option B (display fix) is insufficient when the `suggested_add` amounts are wrong.
Option C changes the operative cash source for the deployment planner.

**Transition Plan:**
- **Immediate:** Implement Option B — add `adjusted_deployable_mv` to `cash_context`,
  surface both values in UI. Operator can recalculate with the correct figure manually.
- **Next Sprint:** Implement Option C — pass `adjusted_deployable_mv` to
  `build_deployment_plan()` when pending settlement exists.

---

### Q5: Should Phase 22D.9 become Track A (UI Enhancement) or Track B (Engine Remediation)?

**Track B — Recommendation Engine Remediation**

Phase 22D.9 was originally classified as a UI/display enhancement opportunity
because the apparent issue was that settlement-adjusted cash was not visible.

Phase 22D.9A confirms that the defect is upstream of the display layer —
the recommendation engine is using the wrong cash figure, and the display
simply reflects that error faithfully.

Implementing Track A (display only) would show the correct number next to the
wrong recommendations, which could increase operator confusion rather than reduce it.

Track B encompasses Track A (the display should still show both values) plus
the engine change that makes the recommendations match the adjusted figure.

---

## Severity Classification

**MATERIAL RECOMMENDATION DEFECT**

| Criterion | Status |
|-----------|--------|
| Affects trade sizing for operator? | YES |
| Affects mandate compliance projection? | YES |
| Mandate breach possible if plan followed? | YES (0.74 pp at T+1) |
| Defect visible to operator in UI? | NO |
| Self-corrects before operator acts? | NO |
| Isolated to display/presentation layer? | NO — engine defect |
| Historical runs affected? | All runs with pending settlement present |

This classification is one level above "display defect" and one level below
"systematic error" (which would require immediate trading halt). The system
should not be used for deployment decisions on settlement-day runs without
applying the manual override workaround (Option B interim).

---

## Limitations of this Audit

1. **Single run analyzed.** PAR-20260602-8CF1CB84 is the primary evidence base.
   The pattern is confirmed across 57 runs with ACCOUNTING_ADJUSTMENT rows,
   but sizing impact calculations are specific to this run.

2. **PENDING ACTIVITY is the only ACCOUNTING_ADJUSTMENT type observed.**
   57/57 instances are Fidelity purchase settlements. If a different type
   of ACCOUNTING_ADJUSTMENT row were ever ingested, Option C would need a
   type-level classification guard to avoid incorrect offsets.

3. **No cases of positive ACCOUNTING_ADJUSTMENT rows observed.**
   If a positive ACCOUNTING_ADJUSTMENT (e.g., pending sale proceeds) were
   present, the question of whether to *increase* deployable cash arises.
   This audit does not address that case; the current formula would correctly
   exclude it from the offset under the proposed design.

4. **Mandate breach only occurs if operator fully follows CW-DAS.**
   Partial deployment (< $4,092) or operator judgment not to follow the plan
   would avoid the breach. However, the entire purpose of CW-DAS is to provide
   trusted deployment guidance — the operator should not need to discount it.

---

## Files Written in This Audit

| File | Covers |
|------|--------|
| [phase_22d9a_deployable_cash_lineage.md](phase_22d9a_deployable_cash_lineage.md) | Q1: Traced cash source from CSV ingestion to `suggested_add` |
| [phase_22d9a_cwdas_cash_source_audit.md](phase_22d9a_cwdas_cash_source_audit.md) | Q2: Code audit confirming reported cash is the sizing basis |
| [phase_22d9a_cash_reconciliation.md](phase_22d9a_cash_reconciliation.md) | Q3: Reported vs adjusted reconciliation with scenario analysis |
| [phase_22d9a_ui_surface_inventory.md](phase_22d9a_ui_surface_inventory.md) | Q4: All 11 UI/API/file surfaces carrying deployable cash values |
| [phase_22d9a_operator_impact_assessment.md](phase_22d9a_operator_impact_assessment.md) | Q5: Capital misallocation, mandate breach scenario, operator risk |
| [phase_22d9a_policy_analysis.md](phase_22d9a_policy_analysis.md) | Q6: Option A/B/C governance analysis, implementation complexity |
| **[phase_22d9a_final_verdict.md](phase_22d9a_final_verdict.md)** | **This document** |

---

## Summary Statement

CW-DAS currently uses **reported** deployable cash ($7,658.25) as the operative
budget for all deployment sizing. This figure overstates actual deployable capital
by $3,566.55 because it does not account for the -$3,566.55 pending equity purchase
settlement in the Fidelity data.

Every `suggested_add` recommendation in the deployment plan is oversized by 1.871×.
An operator who follows the CW-DAS plan in full will breach the 7.0% mandate floor
at T+1 settlement, dropping cash weight to 6.26%.

The defect is not presentational. It originates in the deployment planner's use
of the wrong cash figure. The system's displayed compliance projection (`7.0% after`)
is false and actively misleads the operator into believing the plan is mandate-safe.

**Recommended remedy:** Option C — pass settlement-adjusted deployable cash to the
deployment planner when negative ACCOUNTING_ADJUSTMENT rows exist. Implement Option B
immediately as an interim measure.
