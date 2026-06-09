# PRA-IMPL-06 Assessment

Repository: security-intelligence-hub  
Date: 2026-06-09  
Question: Should PRA-IMPL-06 (Conviction Anchor Rationalization) be created?

## Recommendation: YES

PRA-IMPL-06 should be created as a medium-priority implementation issue.

## Rationale

PRA-IMPL-03 successfully moved all 25 conviction anchor cards to a dedicated section. However, 25 items in a flat list creates a usability wall when the operator expands the section. The section solves the inflation problem but creates a density problem.

The usability review (conviction_anchor_usability_review.md) identifies a clear and bounded improvement:
- Show 5 top conviction anchors by default (CCL tier, composite-score ranked)
- Provide a "Show all" expansion for the full conviction registry
- No new data required — all needed fields already present (narrative_tier, composite_score, replay_supported, percent_of_portfolio)

## Proposed Scope for PRA-IMPL-06

**Title:** Conviction Anchor Rationalization — Top Anchors + Full Registry

**Deliverables:**
1. Top Conviction Anchors sub-section: renders top 5 by tier → composite → replay → weight
2. "Show all" expansion revealing full conviction registry
3. Visual distinction between CCL and HCA tier entries
4. Collapsed full registry with item count badge ("Show all 25")

**Out of scope:**
- New data fields (all needed fields exist)
- Backend changes (pure UI rendering)
- Scoring changes

## Relationship to Existing Issues

| Issue | Relationship |
|---|---|
| PA-005 Conviction Explainability Placement (#37) | PRA-IMPL-06 completes what PRA-IMPL-03 started for PA-005 |
| PRA-IMPL-04 Conviction Anchors Section Extraction (#27) | PRA-IMPL-04 is now superseded — PRA-IMPL-03 already delivered the section; PRA-IMPL-06 should be created in its place |

**Recommendation on PRA-IMPL-04 (#27):** Close PRA-IMPL-04 as superseded by PRA-IMPL-03. PRA-IMPL-06 is the correct forward vehicle.

## Priority and Complexity

Priority: Medium  
Complexity: S-M  
Dependencies: PRA-IMPL-03 (COMPLETE)  
Labels: enhancement, ui-ux, recommendation-surface, priority-medium, ready

## Q5 — What Should Be the Next Implementation Target?

Recommended sequence post-PRA-IMPL-03:

1. **PA-004 / PAP Policy Normalization** (CRITICAL — TSLA still shows as TRIM in PAP)
   - Extend `apply_policy_to_recommendations()` pattern to PAP queue output
   - Highest remaining trust-critical issue
   
2. **PRA-IMPL-06 Conviction Anchor Rationalization** (Medium — clean UX improvement)
   - S-M complexity, no dependencies

3. **AI-001 Investigation** (CRITICAL governance contradiction)
   - Requires governance decision before any code

4. **PRA-IMPL-05 FVI Advisory Overlay** (after data config created)
   - Still requires peer group configuration file

5. **AI-002 Allocation Display Labels** (S complexity quick win)
