# Assessment Issue Closure Plan

Project: Security Intelligence Hub (SIH)  
Type: Governance transition document  
Date: 2026-06-08

## Purpose

This document defines when and how ISSUE-19, ISSUE-20, ISSUE-21, and ISSUE-22 should be closed as assessment issues, and what their permanent governance role is.

## Should Assessment Issues Be Closed?

Yes. All four assessment issues should be closed after implementation issues are created and linked.

Rationale:
1. Assessment work is complete and committed to the repository.
2. Implementation work is tracked in PRA-IMPL-00 through PRA-IMPL-05.
3. Keeping assessment issues open creates false "active work" signal in the backlog.
4. Each assessment issue should transition to a permanent design record, not an ongoing tracking ticket.

## Closure Decision Per Issue

### ISSUE-19 — Fund Vehicle Intelligence (FVI) Assessment

Closure decision: Close
Closure timing: After PRA-IMPL-05 is created and linked
Closure comment: "Assessment complete. Phase-1 FVI advisory implementation tracked in PRA-IMPL-05. This issue remains a permanent design record."
Retention: Permanent governance artifact — commit history and linked docs remain

### ISSUE-20 — Policy-Aware Recommendation Engine Assessment

Closure decision: Close
Closure timing: After PRA-IMPL-02 is created and linked
Closure comment: "Assessment complete. Policy engine implementation tracked in PRA-IMPL-02. This issue remains a permanent design record."
Retention: Permanent governance artifact

### ISSUE-21 — Recommendation Surface Rationalization Assessment

Closure decision: Close
Closure timing: After PRA-IMPL-03 and PRA-IMPL-04 are created and linked
Closure comment: "Assessment complete. Surface rationalization implementation tracked in PRA-IMPL-03 (lane separation) and PRA-IMPL-04 (conviction anchors). This issue remains a permanent design record."
Retention: Permanent governance artifact

### ISSUE-22 — Portfolio Recommendation Architecture Assessment

Closure decision: Close
Closure timing: After PRA-IMPL-00 is created and linked
Closure comment: "Assessment complete. Architecture implementation tracked under PRA-IMPL-00 umbrella epic. This issue remains a permanent design record."
Retention: Permanent governance artifact

## Issues That Must Remain Open

| Issue | Reason |
|---|---|
| ISSUE-12D (#17) | Active evidence program; milestone Dec 2026; blocked by data maturity |
| EPIC #2 CRA | Active roadmap container |
| EPIC #3 PAP | Active roadmap container |
| EPIC #5 Signal Intelligence Evolution | Active; contains ISSUE-12D |
| EPIC #6 Governance and Tooling | Permanent ongoing governance epic |
| PRA-IMPL-00 | New parent epic (stays open until all children complete) |

## Label Recommendations for Assessment Issues at Closure

Add label at closure: `assessment-complete`  
Remove label at closure: `needs-design`  
Retain labels: `governance`, `enhancement`

## Governance Rule After Closure

Assessment issues closed under this plan are archived design records.  
They should not be reopened for implementation scope.  
New implementation scope must be filed as new issues with explicit links.
