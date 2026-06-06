# ISSUE-21 Final Recommendation

Project: Security Intelligence Hub (SIH)  
Assessment: Recommendation Surface Rationalization (RSR)  
Date: 2026-06-06

## Executive Decision

ISSUE-21 should be created as a high-priority governance and UX architecture initiative to separate true actions from informational intelligence and remove recommendation inflation.

## Required Final Recommendation Answers

1. Should ISSUE-21 exist?
- Yes. The current mixed recommendation stream creates workload distortion and action ambiguity.

2. What priority should it receive?
- High priority. It affects operator decision clarity across the entire portfolio workflow.

3. Is it more valuable than MCI?
- Near-term operationally, yes. ISSUE-21 improves action clarity immediately on existing outputs.

4. Should it precede FVI implementation?
- Yes. A rationalized surface should exist before adding new advisory overlays from FVI.

5. Should it precede ISSUE-20 implementation?
- No, but they should be tightly sequenced.
- ISSUE-20 policy precedence and execution-state standardization should come first or in parallel foundation, then ISSUE-21 surface rationalization should consume that contract.

6. What is the minimum viable implementation?
- Typed card classification and typed counts:
  - ACTION,
  - OBSERVATION,
  - EXPLAINABILITY,
  - NARRATIVE,
  - DIAGNOSTIC.
- Main stream displays ACTION cards only.
- Secondary panels display non-action types.
- Header shows typed counts instead of single inflated recommendation count.

7. What is the mature-state recommendation architecture?
- Four-lane recommendation workspace:
  1. Action Queue (execution decisions)
  2. Observation Monitor
  3. Conviction and Narrative Summary
  4. Explainability Evidence Workspace
- Policy-aware execution states integrated from ISSUE-20.
- FVI advisory overlays integrated from ISSUE-19 without converting advisory data into pseudo-recommendations.

## Proposed Priority Ordering

Recommended sequencing:
1. ISSUE-12D evidence program (existing timeline constraint)
2. ISSUE-20 policy-aware execution contract
3. ISSUE-21 recommendation surface rationalization
4. ISSUE-19 FVI advisory integration into rationalized surface
5. MCI follow-on implementation planning

## Success Criteria Mapping

- Recommendation taxonomy defined: Yes
- Action vs observation distinction defined: Yes
- Recommendation count policy defined: Yes
- Conviction anchor placement defined: Yes
- Explainability placement defined: Yes
- Future extensibility defined: Yes

## Final Outcome

ISSUE-21 is recommended as a governance-critical UX rationalization effort that should make recommendation workload truthful, preserve full intelligence context, and provide a scalable architecture for policy-aware and FVI-aware future expansion.
