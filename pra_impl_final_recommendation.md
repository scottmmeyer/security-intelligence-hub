# PRA Implementation Final Recommendation

Project: Security Intelligence Hub (SIH)  
Type: Final implementation planning recommendation  
Date: 2026-06-08

## Recommended First Implementation Target

**PRA-IMPL-01: Typed Recommendation Contract and Card Schema**

Why this first:
1. Zero scoring risk — purely additive JSON fields.
2. No data dependencies.
3. Enables every other PRA-IMPL child; nothing else can proceed cleanly without it.
4. Bounded and completable in a single focused session.
5. Immediately verifiable by existing test suite with no regression risk.

---

## Recommended Implementation Issues to Create

| ID | Title | Priority | Status |
|---|---|---|---|
| PRA-IMPL-00 | Portfolio Recommendation Architecture (epic) | High | Create immediately |
| PRA-IMPL-01 | Typed Recommendation Contract and Card Schema | High | Create immediately |
| PRA-IMPL-02 | Policy-Aware Funding Sources and Allocation Reduction | High | Create immediately |
| PRA-IMPL-03 | Recommendation Surface Lane Separation and Typed Counts | Medium | Create immediately |
| PRA-IMPL-04 | Conviction Anchors Section Extraction | Medium | Create immediately |
| PRA-IMPL-05 | FVI Advisory Overlay for Allocation Reduction | Medium | Create; mark needs-data |

---

## Recommended Labels Per Issue

| Issue | Labels |
|---|---|
| PRA-IMPL-00 | epic, governance, recommendation-engine, priority-high |
| PRA-IMPL-01 | enhancement, governance, recommendation-engine, priority-high, ready |
| PRA-IMPL-02 | enhancement, governance, ui-ux, policy-engine, priority-high, ready |
| PRA-IMPL-03 | enhancement, ui-ux, governance, recommendation-surface, priority-medium, ready |
| PRA-IMPL-04 | enhancement, ui-ux, sti, recommendation-surface, priority-medium, ready |
| PRA-IMPL-05 | enhancement, governance, fvi, recommendation-engine, priority-medium, needs-data |

---

## Recommended Sequencing

```
Now:        PRA-IMPL-01 (typed schema — first target)
Then:       PRA-IMPL-02 (policy normalization)
Then:       PRA-IMPL-03 + PRA-IMPL-04 in tandem (surface + anchors)
Then:       PRA-IMPL-05 (FVI — after peer data config exists)
Parallel:   ISSUE-12D evidence program throughout
```

---

## Recommended Parent/Child Structure

```
PRA-IMPL-00 (parent epic)
├── PRA-IMPL-01  (child — foundation)
├── PRA-IMPL-02  (child — policy normalization)
├── PRA-IMPL-03  (child — surface lanes + counts)
├── PRA-IMPL-04  (child — conviction anchors)
└── PRA-IMPL-05  (child — FVI advisory overlay)
```

---

## Recommended Assessment Issue Actions

| Assessment Issue | Action After PRA-IMPL Issues Created |
|---|---|
| ISSUE-19 (FVI Assessment) | Close — link PRA-IMPL-05 in closing comment |
| ISSUE-20 (Policy Engine Assessment) | Close — link PRA-IMPL-02 in closing comment |
| ISSUE-21 (RSR Assessment) | Close — link PRA-IMPL-03/04 in closing comment |
| ISSUE-22 (PRA Assessment) | Close — link PRA-IMPL-00 in closing comment |

---

## Implementation Risk Summary

| Issue | Risk | Mitigation |
|---|---|---|
| PRA-IMPL-01 | Low | Additive fields only |
| PRA-IMPL-02 | Low-Medium | Extends existing policy gate pattern |
| PRA-IMPL-03 | Medium | UI rendering change; no backend scoring risk |
| PRA-IMPL-04 | Low-Medium | Card reclassification and section creation |
| PRA-IMPL-05 | Low-Medium | Advisory only; data gated by config |

---

## What This Program Does Not Change

- CW-DAS composite scoring
- ESS, Zacks, Danelfin signal values
- UCF verdict computation
- STI profile generation
- Dislocation intelligence scores
- Reconciliation inputs
- ISSUE-12D evidence program timeline
