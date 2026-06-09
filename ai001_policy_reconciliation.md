# AI-001 Policy Reconciliation

Repository: security-intelligence-hub  
Issue: AI-001 (#29)  
Date: 2026-06-09

## The Core Contradiction Explained

The system shows "OVER" and "PASS" simultaneously because these two indicators evaluate **different datasets against the same policy ceiling**.

---

## Exact Calculations

### Validator Path (strategic allocation targets)

| Input | Source | Value |
|---|---|---|
| EQUITIES.US.MICRO target_pct_of_total | strategic_allocation_targets.csv | 1.512% |
| EQUITIES.INTERNATIONAL.MICRO target_pct_of_total | strategic_allocation_targets.csv | 0.700% |
| Combined micro-cap target | sum | **2.212%** |
| Policy ceiling | allocation_policy.yaml | 5.0% |
| Validator result | 2.212% < 5.0% | **PASS** |

**The validator PASS is mathematically correct for its inputs.** Strategic targets do not violate the 5% ceiling.

### UI Concentration Display Path (actual portfolio positions)

| Input | Source | Value |
|---|---|---|
| Actual US.MICRO allocation | Portfolio alignment engine | ~6.0% |
| Actual INTL.MICRO allocation | Portfolio alignment engine | ~0.5% |
| Combined actual micro | sum | **~6.5%** |
| Policy ceiling | allocation_policy.yaml | 5.0% |
| UI indicator | 6.5% > 5.0% | **OVER** |

**The UI OVER indicator is also mathematically correct for its inputs.** The actual portfolio holds more micro-cap exposure than the strategic target and exceeds the policy ceiling.

---

## Root Cause Classification

This is **not a bug** in either the validator or the UI. Both are computing correctly against their respective inputs.

The issue is a **governance design gap**: two different calculations (strategic target vs actual allocation) are both compared against the same ceiling in different parts of the UI, but only one of them produces a PASS/FAIL badge visible to the operator. The other produces an OVER indicator but has no corresponding reconciliation check that surfaced as FAIL.

### Why the Contradiction Exists

1. `validate_concentration_ceilings()` runs on **strategic allocation targets** (what we are targeting in the future)
2. The Concentration Risk section in the UI shows actual **portfolio positions** (what we currently hold)
3. The strategic targets are 2.21% combined micro-cap — well below ceiling
4. The actual portfolio holds 6.5% combined micro-cap — above ceiling
5. Both compare against the same 5% ceiling
6. The PASS result refers to the strategic target
7. The OVER indicator refers to actual holdings
8. No reconciliation check crosses these two: "is the actual portfolio in violation of the strategic policy?"

---

## Determining Which Case Applies

| Candidate Root Cause | Status |
|---|---|
| A — Informational ceiling only | No — the ceiling is clearly stated as a governance cap in allocation_policy.yaml and allocation_methodology.yaml |
| B — Validator bug | No — the validator is computing correctly on its input data |
| C — Allocation methodology exception | No — no exception is documented for the concentrated alpha archetype |
| D — Different micro-cap definitions | No — same micro-cap keys used consistently (EQUITIES.*.MICRO) |
| E — Different aggregation logic | **Partially YES** — the validator aggregates strategic targets; the UI display aggregates actual positions |
| F — UI labeling defect | **YES** — the UI does not make clear that PASS refers to strategic targets, not actual portfolio |

**Primary root cause: Governance design gap + UI labeling defect**

---

## The Actual Numbers (verified)

```
Strategic targets:
  EQUITIES.US.MICRO         = 1.512%   (target, from recalculation seed)
  EQUITIES.INTERNATIONAL.MICRO = 0.700%
  Combined strategic target = 2.212%   → validator sees this → PASS (< 5.0%)

Actual portfolio:
  US.MICRO (actual)         ≈ 6.0%     (current holdings classification)
  INTL.MICRO (actual)       ≈ 0.5%
  Combined actual           ≈ 6.5%     → UI concentration bar sees this → OVER (> 5.0%)
```
