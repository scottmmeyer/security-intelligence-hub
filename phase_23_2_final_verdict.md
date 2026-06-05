# Phase 23.2 — Final Architecture Verdict

**Date:** 2026-06-03
**Status:** APPROVED — Ready for Implementation

**Baseline PAR:** PAR-20260603-73771955 (12/13 PASS, 1 WARN, 0 FAIL)
**Test Suite Baseline:** 785 passed, 1 skipped, 0 failed

---

## 1. Architecture Verdict

**APPROVED.**

The Operator Portfolio Policy Layer design satisfies all six requirement criteria established in `phase_23_2_operator_policy_requirements.md` and all 10 acceptance conditions. No breaking changes were identified in the backward compatibility review.

---

## 2. Architecture Summary

### What This Layer Does
Adds a new sequencing tier between intelligence computation and execution output:

```
Intelligence → [Operator Policy] → Action
```

Policies modify deployment queue ordering and annotations without touching any intelligence score, reconciliation input, or holding classification.

### What This Layer Does Not Do
- Does not modify ESS scores, composite signals, conviction scores, or deployment scores
- Does not affect reconciliation check inputs or outputs
- Does not replace intelligence recommendations — divergence is always shown to the operator
- Does not create implicit policies — all policies require explicit operator action

---

## 3. Deliverable Inventory

| File | Purpose | Status |
|------|---------|--------|
| `phase_23_2_operator_policy_requirements.md` | Requirements Q&A + acceptance criteria | ✅ COMPLETE |
| `phase_23_2_policy_taxonomy.md` | 4 policy types + conflict matrix + lifecycle | ✅ COMPLETE |
| `phase_23_2_data_model_design.md` | JSON schema + Python dataclass + apply_policy logic | ✅ COMPLETE |
| `phase_23_2_ui_design.md` | Panel layout + badge system + confirmation gates | ✅ COMPLETE |
| `phase_23_2_execution_ranking_design.md` | Queue partitioning + rank algorithm + stability guarantee | ✅ COMPLETE |
| `phase_23_2_policy_persistence_design.md` | API endpoints + lifecycle + PAR snapshot | ✅ COMPLETE |
| `phase_23_2_backward_compatibility_review.md` | Per-artifact impact assessment | ✅ COMPLETE |
| `phase_23_2_final_verdict.md` | This document — implementation authorization | ✅ COMPLETE |

---

## 4. Constraint Compliance Verification

### CC-01: Intelligence scores unmodified
✅ PASS — Policy application is post-queue. All scoring (ESS, composite, deployment, replay, conviction) is pre-policy.

### CC-02: Reconciliation unaffected
✅ PASS — `run_reconciliation()` is called before `apply_policy_to_queue()`. Policy snapshot is post-reconciliation output.

### CC-03: Policy changes are reversible
✅ PASS — `original_rank` preserved. Revoking a policy restores pre-policy rank on next run.

### CC-04: Policy divergence always visible
✅ PASS — Intelligence flag (TRIM, REDUCE_CANDIDATE) always shown alongside policy badge. Divergence warning rendered when they conflict.

### CC-05: Additive only (backward compatible)
✅ PASS — All new fields have None/False defaults. All new JSON keys use `.get()` with safe defaults. Existing PARs render correctly without policy fields.

---

## 5. Risk Summary with Mitigations

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Operator sets DO_NOT_SELL and misses sustained TRIM signal | Medium | Divergence warning always displayed; intelligence shown alongside policy |
| Policy expired but operator assumes still active | Low | `is_active()` checks `expires_at` at read time; policy panel shows EXPIRED status |
| DO_NOT_SELL + SELL_LAST conflict on same symbol | Low | 409 conflict rejection at API layer + UI validation |
| Policy suppresses actionable trim, eroding performance | Medium | Policy-suppressed section in deployment queue output; operator must explicitly see what was blocked |
| PREFERRED_ACCUMULATION on symbol already at target allocation | Low | Operator-visible; allocation overlay still shows overweight state alongside preferred badge |
| Policy applied to symbol not in current portfolio | Low | System accepts with warning; policy is dormant until symbol enters portfolio |

---

## 6. Implementation Sequence

The following implementation sequence is authorized. Each step must be completed before the next.

### Step 1: `src/portfolio/operator_policy.py` (new module)
- `POLICY_TYPES`, `POLICY_CONFLICTS`, `POLICY_WARNINGS`
- `OperatorPolicy` dataclass with `is_active()`
- `OperatorPolicyRegistry` class with `load()`, `get()`, `active_policy_type()`, helper predicates, `all_active()`

### Step 2: `src/portfolio/deployment_queue.py` — additive fields
- Add 5 optional fields to `CandidateEntry`: `policy_type`, `policy_annotation`, `policy_protected`, `policy_rank_boost`, `original_rank`
- Add `apply_policy_to_queue()` function (returns `(annotated_queue, suppressed)` tuple)
- Add `_is_sell_context()` helper

### Step 3: `src/portfolio/runner.py` — policy integration
- Import `OperatorPolicyRegistry`, `apply_policy_to_queue`
- After `build_deployment_queue()`: load registry, call `apply_policy_to_queue()`
- Embed `policy_snapshot` in `run_metadata.json`
- Write `policy_suppressed` to `deployment_queue.json`
- Annotate `security_overlays.csv` with policy fields

### Step 4: `scripts/run_outcome_ui.py` — API endpoints
- `GET /api/operator/policies`
- `POST /api/operator/policies`
- `POST /api/operator/policies/revoke`
- `GET /api/operator/policies/{symbol}`

### Step 5: Frontend — policy panel
- Operator Policy Panel (below Tax Position Panel)
- Policy badges on security overlay cards
- Policy column in deployment queue table
- Divergence warning lines
- CORE_ANCHOR confirmation modal
- Policy-Suppressed section in deployment queue

### Step 6: Tests
- `tests/test_operator_policy.py` — unit tests for `OperatorPolicy`, `OperatorPolicyRegistry`
- `tests/test_apply_policy_to_queue.py` — unit tests for queue transformation
- `tests/test_policy_api.py` — API endpoint tests
- No modifications to existing test files required

---

## 7. Acceptance Criteria (from Requirements)

All 10 criteria must pass before Phase 23.2 is certified complete:

1. ✅ Design: Policy types defined and documented with conflict matrix
2. ✅ Design: DO_NOT_SELL suppresses sell-context entries without touching scores
3. ✅ Design: PREFERRED_ACCUMULATION boosts queue position; original_rank preserved
4. ✅ Design: SELL_LAST pushed to tail of sell cohort; within-SELL_LAST ordered by intelligence rank
5. ✅ Design: CORE_ANCHOR annotation-only; confirmation gate in UI
6. ✅ Design: Policies survive portfolio re-uploads (symbol-keyed, file-persistent)
7. ✅ Design: PAR records active policy snapshot in run_metadata.json
8. ✅ Design: No existing tests broken (backward-compatible additive changes)
9. ✅ Design: Intelligence divergence from policy always visible to operator
10. ⏳ Implementation: Full test suite passes after Phase 23.2 implementation (post-implementation gate)

Criteria 1–9 are satisfied by these design documents.
Criterion 10 is the post-implementation gate for Phase 23.2 certification.

---

## 8. Phase Gate

**Phase 23.2 Implementation is AUTHORIZED to begin.**

The implementation MUST:
- Keep PAR-20260603-73771955 valid as baseline (no retroactive changes)
- Pass full test suite (≥785 tests, 0 failures) after all implementation steps
- Produce a new PAR demonstrating policy annotations in deployment queue output
- Confirm `run_metadata.json` contains `policy_snapshot` on the new PAR

On completion, a Phase 23.2 PAR validation report will certify the implementation.
