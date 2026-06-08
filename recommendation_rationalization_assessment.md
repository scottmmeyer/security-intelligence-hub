# Recommendation Rationalization Assessment

Project: Security Intelligence Hub (SIH)  
Scope: ISSUE-21 implementation planning detail  
Date: 2026-06-08

## Q2-B / Q4) Recommendation Inflation and Surface Rationalization: Implementation Scope

## Q4) Does SIH Currently Have Recommendation Inflation?

Yes. Confirmed by:
1. Reference operator snapshot with headline count of 34 "recommendations."
2. Rationalized decomposition: approximately 6 true actions, 5 observations, 5 explainability artifacts, 18 conviction/narrative items.
3. Result: the headline count overstates actionable workload by approximately 5x.

Should these be separated? Yes.

The operator cannot reliably distinguish between a sell-context action and a "High Conviction Retain" narrative card when all items carry equal visual weight in a single stream.

## Inflation Sources and Remediation

### Source 1: High Conviction Retain Cards

Current behavior: renders in main recommendation stream as recommendation-class card.

Classification by ISSUE-21 taxonomy: OBSERVATION / NARRATIVE. These items assert confidence in current posture; they do not prescribe a portfolio action.

Examples: MSFT High Conviction Retain, ARW High Conviction Retain, VRT High Conviction Retain.

Remediation:
- Move to dedicated Conviction Anchors section.
- Remove from recommendation count.
- Keep visible with supporting UCF tier context.
- Cross-link to any related deployment or reduction action.

### Source 2: Informational Observations

Current behavior: mixed with actionable cards at same rendering level.

Examples: Strategic Retain Signal, Dislocation Observation, Replay Alignment context.

Remediation:
- Classify as OBSERVATION.
- Route to Observation Monitor lane.
- Not counted in Actions total.

### Source 3: Explainability Artifacts

Current behavior: appear inline in recommendation card body, sometimes at card-list level.

Examples: STI Classification trace, Anchor rationale, Replay evidence.

Remediation:
- Keep inline as collapsed detail or drill-down link.
- Do not promote to card-list level.
- Not counted in Actions total.

## Required UI Changes

### Typed Count Header

Replace: "34 Recommendations"

With:
- Actions: 6
- Observations: 5
- Conviction Anchors: 18
- Explainability: 5

### Lane Separation

Required lanes:
1. Action Queue — ACTION class only
2. Observation Monitor — OBSERVATION and DIAGNOSTIC
3. Conviction Anchors — NARRATIVE and conviction-specific OBSERVATION
4. Explainability Workspace — EXPLAINABILITY (collapsed by default)

### Card Metadata Field Required

Each rendered card must carry a `card_type` field:
- card_type: ACTION | OBSERVATION | NARRATIVE | EXPLAINABILITY | DIAGNOSTIC

This field governs which lane and count bucket receives the card.

## Implementation Boundaries

Must not change:
- Intelligence scoring or conviction tier computation
- UCF verdict outputs
- STI profile generation

May change:
- JSON response structure to carry card_type metadata
- UI rendering logic for lane assignment
- Count summary component in portfolio panel header
- Card visual styling per type

## Acceptance Criteria

1. Header shows typed counts, not a single aggregate.
2. High Conviction Retain cards do not appear in Action Queue.
3. Conviction Anchors section renders all observation/narrative conviction cards.
4. Action Queue contains only cards with concrete action verb and execution state.
5. Total card count remains accessible but is not the primary KPI.

## Implementation Complexity Estimate

- card_type field addition to JSON payload: Low
- UI lane rendering: Medium
- Count header component: Low
- Conviction Anchors section: Low-Medium
- Total estimate: 2-3 development sessions; no backend scoring risk

## Recommended Issue Title

PRA-IMPL-03: Recommendation Surface Lane Separation and Typed Counts  
PRA-IMPL-04: Conviction Anchors Section Extraction  

Labels for both: enhancement, ui-ux, governance, recommendation-surface, priority-medium, ready
