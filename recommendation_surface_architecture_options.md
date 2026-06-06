# Recommendation Surface Architecture Options

Project: Security Intelligence Hub (SIH)  
Assessment: ISSUE-21 Architecture Options  
Date: 2026-06-06

## Q5) Placement of High Conviction Retain Cards

Examples (MSFT, ARW, VRT, CVE) should not be first-class recommendation cards in the main action stream.

Recommended placement:
- Primary: Conviction summary section
- Secondary: Narrative lane with explainability link
- Optional: drill-down detail in conviction workspace

Reason:
- These items are valuable intelligence but usually do not prescribe immediate execution action.

## Q6) Placement of STI Explainability Output

STI elements:
- classification trace,
- anchor rationale,
- strategic importance,
- downgrade risk,
- replay alignment evidence.

Recommended placement model:
1. Inline compact badge in card header (minimal status only).
2. Collapsed detail panel for quick expansion.
3. Full drill-down workspace for deep evidence review.

Do not default full STI explanation inline in the main action card body.

## Q7) UI Structure Alternatives

### Option A: Single Recommendation Stream (Current)

Strengths:
- Simple to implement and scan in one list.

Weaknesses:
- Semantic mixing,
- inflated recommendation counts,
- weak action salience.

### Option B: Actions + Observations + Conviction Anchors

Strengths:
- Clear lane separation,
- preserves context,
- lowers inflation risk.

Weaknesses:
- Slightly more UI complexity,
- requires typed-card model.

### Option C: Actions in Main Stream, Everything Else in Supporting Panels

Strengths:
- Highest action clarity,
- strongest workload truthfulness,
- best for decision-time focus.

Weaknesses:
- Risk of under-exposing context unless links are strong.

### Option D: Hybrid Workspace Architecture (Recommended)

Structure:
1. Action Queue (execution decisions)
2. Observation Monitor (context states)
3. Conviction and Narrative Summary
4. Explainability Evidence Drawer

Strengths:
- Preserves all intelligence,
- maximizes action clarity,
- scalable for ISSUE-19 and ISSUE-20 integrations.

Weaknesses:
- Requires careful navigation and consistent metadata contract.

Recommendation:
- Use Option D target architecture with Option C as minimum viable transition.
