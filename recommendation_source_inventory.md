# Recommendation Source Inventory

Project: Security Intelligence Hub (SIH)  
Assessment: ISSUE-22 Source Role Inventory  
Date: 2026-06-06

## Q2) Recommendation-Producing Systems and Intended Roles

| System | Primary Output Role | Typical Class | Decision Authority | Notes |
|---|---|---|---|---|
| CRA | Capital rotation and reduction prioritization | Recommendation | High for action sequencing | Produces direct reduce/reallocate pathways |
| PAP | Portfolio action planning and execution queueing | Recommendation | High for execution order | Operational action lane backbone |
| STI | Strategic conviction interpretation | Observation / Explainability / Narrative | Medium (context authority) | Should inform decisions; not always direct action |
| Dislocation | Regime stress and dislocation context | Observation / Diagnostic | Medium (risk context authority) | Primarily context unless explicit action trigger exists |
| Policy Engine | Execution constraints and ordering transforms | Recommendation modifier / Execution governance | Highest for execution override on constrained actions | Does not mutate underlying scores |
| FVI (future) | Vehicle quality and replacement suitability | Observation in phase 1; Recommendation gate in phase 2 | Medium-High after evidence gates | Advisory first, policy-gated influence later |

## Source Interaction Intent

1. CRA/PAP generate base action candidates.
2. STI/Dislocation provide contextual evidence and confidence framing.
3. Policy Engine applies execution constraints and precedence.
4. FVI overlays vehicle-quality context and replacement economics.

## Source Classification Policy

- Not every source output is a recommendation.
- Each output must be classified by semantic type before counting and ranking.

## Inventory Conclusion

SIH is a multi-source recommendation environment and requires a unifying architecture layer to prevent semantic drift, double-counting, and cross-surface inconsistency.
