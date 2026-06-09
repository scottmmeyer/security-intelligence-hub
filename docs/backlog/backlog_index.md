# SIH Backlog Index

Repository: security-intelligence-hub  
Created: 2026-06-09  
Scope: Allocation Intelligence and Portfolio Alignment panels

---

## Allocation Intelligence Backlog

| ID | Title | Priority | Complexity | Status |
|---|---|---|---|---|
| [AI-001](allocation_intelligence/AI-001-allocation-policy-contradiction.md) | Allocation Policy vs Actual Allocation Contradiction | CRITICAL | M | Open |
| [AI-002](allocation_intelligence/AI-002-strategic-allocation-display-ambiguity.md) | Strategic Allocation Display Ambiguity | HIGH | S | Open |
| [AI-003](allocation_intelligence/AI-003-allocation-philosophy-explainability.md) | Allocation Philosophy Explainability Gap | HIGH | M | Open |
| [AI-004](allocation_intelligence/AI-004-allocation-policy-version-diff.md) | Allocation Policy Version Diff Visibility | MEDIUM | M | Open |

---

## Portfolio Alignment Backlog

| ID | Title | Priority | Complexity | Status |
|---|---|---|---|---|
| [PA-001](portfolio_alignment/PA-001-recommendation-stream-overload.md) | Recommendation Stream Overload | CRITICAL | M | Open |
| [PA-002](portfolio_alignment/PA-002-recommendation-ordering-defect.md) | Recommendation Ordering Defect | HIGH | S | Open |
| [PA-003](portfolio_alignment/PA-003-recommendation-count-inflation.md) | Recommendation Count Inflation | HIGH | S | Open |
| [PA-004](portfolio_alignment/PA-004-policy-consistency-failure.md) | Policy Consistency Failure Across Advisory Surfaces | CRITICAL | M | Open |
| [PA-005](portfolio_alignment/PA-005-conviction-explainability-placement.md) | Conviction Explainability Placement Problem | HIGH | M | Open |
| [PA-006](portfolio_alignment/PA-006-allocation-drift-trend-visibility.md) | Allocation Drift Trend Visibility | MEDIUM | L | Open |

---

## Summary Counts

| Priority | Count |
|---|---|
| CRITICAL | 3 (AI-001, PA-001, PA-004) |
| HIGH | 5 (AI-002, AI-003, PA-002, PA-003, PA-005) |
| MEDIUM | 2 (AI-004, PA-006) |

| Complexity | Count |
|---|---|
| S (Small) | 3 (AI-002, PA-002, PA-003) |
| M (Medium) | 6 (AI-001, AI-003, AI-004, PA-001, PA-004, PA-005) |
| L (Large) | 1 (PA-006) |

---

## Related Implementation Issues (PRA Program)

The following PRA-IMPL issues directly address several of the backlog items above:

| PRA Issue | Status | Addresses |
|---|---|---|
| PRA-IMPL-01 Typed Recommendation Contract | COMPLETE (commit 5444689) | Enables PA-001, PA-003 |
| PRA-IMPL-02 Policy-Aware Normalization | COMPLETE (commit 470c511) | Addresses PA-004 for Portfolio Alignment recs |
| PRA-IMPL-03 Surface Lane Separation | OPEN (#26) | Directly implements PA-001, PA-002, PA-003 |
| PRA-IMPL-04 Conviction Anchors Extraction | OPEN (#27) | Directly implements PA-005 |
| PRA-IMPL-05 FVI Advisory Overlay | OPEN (#28) | Future — not in this backlog wave |
