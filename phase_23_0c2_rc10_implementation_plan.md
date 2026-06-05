# Phase 23.0C.2 — RC-10 Implementation Plan
**PAR Run:** PAR-20260603-B66B00E3  
**Check:** RC-10 — Portfolio Philosophy Consistency  
**Current Status:** FAIL  
**Corrected Status:** PASS  
**Source:** `src/portfolio/reconciliation.py` lines 844–915  
**Phase:** 23.0C.2 — PAP Validation + Reconciliation Governance Corrections  
**Scope:** Implementation plan for rule correction. No code changes in this phase.

---

## 1. Current Rule Definition

`_rc10_philosophy_consistency(recommendations, mandate_type)` checks every recommendation for three conditions:

```python
# Mandate consistency
if rec_mandate and rec_mandate != active_mandate:
    row_violations.append(f"mandate_type={rec_mandate!r} ≠ run mandate {active_mandate!r}")

# PMI fields present
if mandate_sev is None or mandate_sev == "":
    row_violations.append("mandate_severity missing")
if mandate_urg is None or mandate_urg == "":
    row_violations.append("mandate_urgency missing")
if mandate_label is None or mandate_label == "":
    row_violations.append("mandate_drift_label missing")
```

The rule iterates **all 33 recommendations** and requires `mandate_drift_label` to be present on every one.

---

## 2. The Violation

**Current reconciliation output for RC-10:**
```
Status: FAIL
Active mandate: CONCENTRATED_ALPHA
Recommendations checked: 33
Violations: 27
Actual: 6/33 PASS
```

27 recommendations are flagged for "mandate_drift_label missing."

---

## 3. Root Cause Analysis

### 3.1 Recommendation Type Distribution

From `recommendations.json` (PAR-20260603-B66B00E3):

| recommendation_type | Count | Has mandate_drift_label | Has drift_pct |
|--------------------|-------|------------------------|---------------|
| CONVICTION_EXPLAINABILITY_CARD | 20 | 0 | 0 |
| REDUCE_OVERWEIGHT | 3 | 3 (INTENTIONAL_OVERWEIGHT) | 3 |
| INCREASE_UNDERWEIGHT | 2 | 2 (INTENTIONAL_UNDERWEIGHT) | 2 |
| IMPROVE_REPLAY_ALIGNMENT | 1 | 1 (INTENTIONAL_UNDERWEIGHT) | 1 |
| STRATEGIC_RETAIN_NARRATIVE | 3 | 0 | 0 |
| STRATEGIC_RETAIN_SIGNAL | 2 | 0 | 0 |
| PORTFOLIO_CONSTRUCTION_NARRATIVE | 1 | 0 | 0 |
| REPLAY_ALIGNMENT_CONTEXT | 1 | 0 | 0 |
| **TOTAL** | **33** | **6** | **6** |

**All 6 allocation-type recommendations have `mandate_drift_label` correctly populated.** All 27 non-allocation recommendations have neither `mandate_drift_label` nor `drift_pct`. This is not a missing-field defect — these fields do not apply to non-allocation recommendation types.

### 3.2 Semantic Scope of `mandate_drift_label`

`mandate_drift_label` is an allocation governance field. Its values (`INTENTIONAL_OVERWEIGHT`, `INTENTIONAL_UNDERWEIGHT`) describe the mandate's position on whether a portfolio's deviation from target allocation is deliberate or problematic. This field is only meaningful for recommendations that involve allocation drift measurement:
- `INCREASE_UNDERWEIGHT` — portfolio is below mandate target
- `REDUCE_OVERWEIGHT` — portfolio is above mandate target
- `IMPROVE_REPLAY_ALIGNMENT` — portfolio replay performance deviates from mandate

Non-allocation recommendation types do not carry allocation context:
- `CONVICTION_EXPLAINABILITY_CARD` — explains why a holding is held at its current weight
- `PORTFOLIO_CONSTRUCTION_NARRATIVE` — narrative about portfolio construction philosophy
- `REPLAY_ALIGNMENT_CONTEXT` — contextual explanation of replay vs. benchmark performance
- `STRATEGIC_RETAIN_NARRATIVE` — rationale for retaining a strategic hold
- `STRATEGIC_RETAIN_SIGNAL` — signal supporting a strategic retain decision

None of these types carry `drift_pct` because they are not about allocation deviation. The absence of `mandate_drift_label` on these types is structurally correct, not a data quality defect.

### 3.3 Rule Design Assumption

RC-10's original design assumed uniform PMI field population across all recommendation types — treating all recs as "philosophy-consistency-relevant" for mandate fields. The `mandate_drift_label` check was included alongside `mandate_severity` and `mandate_urgency` without distinguishing field applicability by recommendation type.

The 27 flagged recommendations DO have `mandate_type = CONCENTRATED_ALPHA`, `mandate_severity`, and `mandate_urgency` populated (only the label check fails). This confirms the mandate consistency purpose of RC-10 is satisfied; only the label applicability assumption is incorrect.

---

## 4. Phase 23.0C.1 Verdict Established

As established in `phase_23_0c1_reconciliation_rule_review.md`, RC-10 is a **false positive** with no analytical impact. The corrected status is **PASS**.

---

## 5. Implementation Plan

### 5.1 Restrict Label Check to Allocation Types

Define a constant set of recommendation types for which `mandate_drift_label` is applicable:

```python
_ALLOCATION_REC_TYPES = frozenset({
    "INCREASE_UNDERWEIGHT",
    "REDUCE_OVERWEIGHT",
    "IMPROVE_REPLAY_ALIGNMENT",
})
```

**Updated RC-10 logic** (`src/portfolio/reconciliation.py`, `_rc10_philosophy_consistency`):

```python
# PMI fields present
if mandate_sev is None or mandate_sev == "":
    row_violations.append("mandate_severity missing")
if mandate_urg is None or mandate_urg == "":
    row_violations.append("mandate_urgency missing")

# mandate_drift_label only applicable to allocation recommendation types
rec_type = str(_fld(rec, "recommendation_type", "") or "").upper()
if rec_type in _ALLOCATION_REC_TYPES:
    if mandate_label is None or mandate_label == "":
        row_violations.append("mandate_drift_label missing")
```

This change restricts the label check to exactly the 6 recommendation types where it is semantically applicable. All 27 non-allocation recs are exempted. The mandate_type, mandate_severity, and mandate_urgency consistency checks continue to apply to all 33 recommendations.

### 5.2 Detail Enhancement (Optional)

Update the sub-check status output to distinguish "not applicable" from "PASS" for the label field:

```python
sub_checks.append({
    "recommendation_id": rec_id,
    "recommendation_type": rec_type,
    "mandate_type": rec_mandate,
    "mandate_severity": mandate_sev,
    "mandate_urgency": mandate_urg,
    "mandate_drift_label": mandate_label,
    "label_applicable": rec_type in _ALLOCATION_REC_TYPES,  # ← new field
    "status": "PASS" if not row_violations else "FAIL",
    "violations": row_violations,
})
```

This makes the governance intent visible in reconciliation output: operators can see which recs are allocation-type and expected to carry a drift label.

---

## 6. Expected Post-Fix Results

### 6.1 RC-10 Check Counts

| Category | Before | After |
|----------|--------|-------|
| Recommendations checked | 33 | 33 |
| With label check applicable | 33 | 6 (allocation types only) |
| Violations (mandate_drift_label missing) | 27 | 0 |
| Violations (other PMI fields) | 0 | 0 |
| Violations (mandate consistency) | 0 | 0 |
| **Overall status** | **FAIL** | **PASS** |

### 6.2 Post-Fix Sub-Check Breakdown

```
PASS (6): REDUCE_OVERWEIGHT × 3, INCREASE_UNDERWEIGHT × 2, IMPROVE_REPLAY_ALIGNMENT × 1
PASS (27): All narrative types (label not applicable — not checked)
```

### 6.3 Verified Allocation Type Labels

All 6 allocation-type records are confirmed to carry correct labels:

| Rec ID | Type | mandate_drift_label | drift_pct |
|--------|------|---------------------|-----------|
| REC-4A1A | INCREASE_UNDERWEIGHT | INTENTIONAL_UNDERWEIGHT | -5.4011 |
| REC-A5B3 | REDUCE_OVERWEIGHT | INTENTIONAL_OVERWEIGHT | +4.8123 |
| REC-8529 | INCREASE_UNDERWEIGHT | INTENTIONAL_UNDERWEIGHT | -4.1647 |
| REC-9F4A | REDUCE_OVERWEIGHT | INTENTIONAL_OVERWEIGHT | +4.1494 |
| REC-A6C6 | IMPROVE_REPLAY_ALIGNMENT | INTENTIONAL_UNDERWEIGHT | -5.4011 |
| REC-C9C4 | REDUCE_OVERWEIGHT | INTENTIONAL_OVERWEIGHT | +6.761 |

Post-fix: All 6 pass. Zero violations across all 33 recommendations.

---

## 7. Affected Files

| File | Change | Type |
|------|--------|------|
| `src/portfolio/reconciliation.py` | Add `_ALLOCATION_REC_TYPES` constant; restrict `mandate_drift_label` check to these types in `_rc10_philosophy_consistency()` | Logic change |

No YAML or data file changes required. No test data changes required — the fix causes existing valid data to pass correctly.

---

## 8. Testing Requirements

After implementing the fix:

1. `test_reconciliation.py`: RC-10 status = `PASS` for PAR-20260603-B66B00E3
2. Introduce a synthetic `REDUCE_OVERWEIGHT` recommendation with `mandate_drift_label = null` → RC-10 still fires FAIL
3. Introduce a synthetic `CONVICTION_EXPLAINABILITY_CARD` with `mandate_drift_label = null` → RC-10 does NOT fire
4. Introduce a synthetic recommendation with wrong `mandate_type` (e.g., "GROWTH" in a CONCENTRATED_ALPHA run) → mandate consistency check still fires

---

## 9. Verdict

**RC-10 root cause confirmed: false positive.** The rule incorrectly treats `mandate_drift_label` as universally applicable across all 33 recommendation types. The field is architecturally defined only for allocation deviation recommendations. All 6 allocation-type records carry the correct label. The fix is a targeted 4-line logic change that preserves mandate consistency checking while restricting label applicability to the semantically correct set of recommendation types. Post-fix result: RC-10 → PASS (33/33, 0 violations).

---

*Phase 23.0C.2 — RC-10 Implementation Plan*  
*Run: PAR-20260603-B66B00E3 | Generated: Phase 23 governance hardening*
