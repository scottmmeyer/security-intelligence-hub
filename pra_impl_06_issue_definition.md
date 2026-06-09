# PRA-IMPL-06 Issue Definition

Repository: security-intelligence-hub  
GitHub Issue: #39  
Date: 2026-06-09

## Summary

PRA-IMPL-06 was created at https://github.com/scottmmeyer/security-intelligence-hub/issues/39

Title: PRA-IMPL-06: Conviction Anchor Rationalization  
Priority: Medium  
Complexity: S-M  
Labels: enhancement, ui-ux, priority-medium, ready  
Dependency: PRA-IMPL-03 (COMPLETE)

## Scope

**Top Conviction Anchors (default visible):**
- 5 items visible by default within the Conviction Anchors lane
- Ranking: tier (CCL > HCA > TGC > WTC) → composite score → replay support → portfolio weight
- No backend changes needed

**Full Conviction Registry (collapsed):**
- "Show all N" button reveals complete list
- Uses existing CONVICTION_EXPLAINABILITY_CARD rendering

## Acceptance Criteria

1. Top 5 conviction anchors always visible when Conviction Anchors lane is expanded
2. Ranking by tier → composite → replay → weight
3. "Show all" reveals complete registry
4. CCL and HCA items visually distinguished
5. No scoring or data model changes
