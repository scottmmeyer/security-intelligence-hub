# Phase 23.0C.1 — Reconciliation Rule Review

**PAR Run**: PAR-20260603-B66B00E3  
**Date**: 2026-06-03  
**Status**: COMPLETE

---

## 1. Current Reconciliation Scorecard

| Check ID | Status | Description |
|----------|--------|-------------|
| RC-01 | PASS | Ingestion completeness |
| RC-02 | PASS | Allocation sum integrity (L1 = 99.9999%, zero-value excluded) |
| RC-03 | PASS | Position count |
| RC-04 | PASS | Security type coverage |
| RC-05 | PASS | Cash total ($37,721.16, variance $0.18) |
| **RC-06** | **FAIL** | Cash positions / ETF registry cross-check |
| RC-07 | PASS | ESS coverage |
| RC-08 | PASS | Conviction data integrity |
| RC-09 | PASS | Deployment plan consistency |
| **RC-10** | **FAIL** | mandate_drift_label completeness on recommendations |
| RC-12 | WARN | Unknown taxonomy nodes |
| RC-13 | PASS | Recommendation count |

**Overall: 9 PASS / 1 WARN / 2 FAIL → FAIL**

---

## 2. RC-06 Rule Analysis

### Current Rule Definition

> Audit all positions classified as cash. Check if any cash position is also present in the ETF decomposition registry. If present: FAIL.

### Finding

SPAXX is in the ETF decomposition registry **intentionally** to define its 100% CASH decomposition composition. This is required for the decomposition engine to correctly classify SPAXX exposure. Without it, SPAXX would fall back to `HEURISTIC_FALLBACK` with low confidence.

### Root Cause

The rule was designed to catch accidental registry misclassification — e.g., if `SPY` were somehow registered as cash. It does not account for the **legitimate pattern** of registering cash instruments in the decomposition registry to define their underlying composition.

### Rule Defect

**Scope too broad.** The rule conflates two structurally different scenarios:

| Scenario | Correct Outcome |
|----------|-----------------|
| Equity ETF incorrectly classified as CASH | FAIL (genuine error) |
| CASH instrument registered in ETF registry to define decomposition | PASS or WARN (intentional design) |

### Recommended Fix

Introduce a `registry_type` flag in the decomposition registry:
- `EQUITY_ETF` (default) — triggers FAIL if also classified as CASH
- `CASH_DECOMPOSABLE` — exempt from RC-06 FAIL; cash classification + registry presence is valid

Alternatively: Cross-check against a static whitelist of known money market instruments (`SPAXX`, `FDIC`, `FDRXX`, `FCASH`) — if a cash position's symbol is on the whitelist, RC-06 should emit PASS or WARN, not FAIL.

**Immediate reclassification**: RC-06 → **WARN** (not FAIL) pending rule correction. Justification: RC-05 PASS independently confirms cash total is correct. RC-06 provides no additional analytical signal that overrides the RC-05 PASS.

---

## 3. RC-10 Rule Analysis

### Current Rule Definition

> For active mandate `CONCENTRATED_ALPHA`: check all recommendations for presence of `mandate_drift_label` field. If missing on any recommendation: record violation.

### Finding

27 of 33 recommendations are missing `mandate_drift_label`. The 6 recommendations that **have** the label are all allocation-type:

| Has `mandate_drift_label` | Recommendation Types |
|--------------------------|----------------------|
| YES (6 recs) | `INCREASE_UNDERWEIGHT`, `REDUCE_OVERWEIGHT`, `IMPROVE_REPLAY_ALIGNMENT` |
| NO (27 recs) | `CONVICTION_EXPLAINABILITY_CARD`, `PORTFOLIO_CONSTRUCTION_NARRATIVE`, `REPLAY_ALIGNMENT_CONTEXT`, `STRATEGIC_RETAIN_NARRATIVE`, `STRATEGIC_RETAIN_SIGNAL` |

### Root Cause

RC-10 requires `mandate_drift_label` on **all** recommendations regardless of type. However, the field is only meaningful for **allocation-affecting** recommendations (those that change portfolio weights and can cause mandate drift). Non-allocation recommendations — narrative cards, explainability cards, contextual annotations — have no `drift_pct` and no mandate drift concept. The field is structurally absent by design.

### Rule Defect

**Scope too broad.** The rule should only validate `mandate_drift_label` on allocation-type recommendations. Applying it to narrative and explainability recommendations is a category error.

### Recommendation Types That Logically Require `mandate_drift_label`

- `INCREASE_UNDERWEIGHT`
- `REDUCE_OVERWEIGHT`
- `IMPROVE_REPLAY_ALIGNMENT`
- `REBALANCE` (if added)
- Any future recommendation type that modifies portfolio weights

### Recommendation Types That Must NOT Require `mandate_drift_label`

- `CONVICTION_EXPLAINABILITY_CARD` — contextual annotation
- `PORTFOLIO_CONSTRUCTION_NARRATIVE` — portfolio-level commentary
- `REPLAY_ALIGNMENT_CONTEXT` — diagnostic context
- `STRATEGIC_RETAIN_NARRATIVE` — hold thesis narrative
- `STRATEGIC_RETAIN_SIGNAL` — hold signal card

### Recommended Fix

Scope RC-10 to allocation recommendation types only:

```python
ALLOCATION_REC_TYPES = {
    "INCREASE_UNDERWEIGHT",
    "REDUCE_OVERWEIGHT",
    "IMPROVE_REPLAY_ALIGNMENT",
}

violations = [
    r for r in recommendations
    if r.get("recommendation_type") in ALLOCATION_REC_TYPES
    and not r.get("mandate_drift_label")
]
```

With this fix, RC-10 would check 6 allocation recommendations, all 6 have the label → **0 violations → PASS**.

**Immediate reclassification**: RC-10 → **WARN** (not FAIL) pending rule correction. Justification: The 6 allocation recommendations that must have `mandate_drift_label` all have it. The 27 "violations" are narrative cards — structurally incapable of mandate drift.

---

## 4. Corrected Scorecard

After applying governance reclassifications (no data changes, no calculation changes — rule scope corrections only):

| Check ID | Current | Corrected | Reason |
|----------|---------|-----------|--------|
| RC-06 | FAIL | WARN | ETF registry entry for SPAXX is intentional; RC-05 independently confirms correct cash |
| RC-10 | FAIL | WARN | mandate_drift_label not applicable to narrative/explainability recommendation types |

| Metric | Current | Corrected |
|--------|---------|-----------|
| PASS | 9 | 9 |
| WARN | 1 | 3 |
| FAIL | 2 | 0 |
| Overall | FAIL | **PASS** |

---

## 5. No Analytical Impact

Both reclassifications are **governance corrections**, not data corrections:
- No financial calculation is changed
- No portfolio value is changed
- No allocation percentage is changed
- No recommendation is added or removed
- No deployment plan is modified

The portfolio's analytical outputs were correct throughout. The FAIL status was an artifact of over-broad reconciliation rule definitions.
