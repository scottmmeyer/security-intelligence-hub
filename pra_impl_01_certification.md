# PRA-IMPL-01 Implementation Certification

Project: Security Intelligence Hub (SIH)  
Issue: PRA-IMPL-01 Typed Recommendation Contract and Card Schema  
Date: 2026-06-08  
Status: CERTIFIED

## Implementation Summary

Added five additive fields to `PortfolioRecommendation` frozen dataclass and set
`card_type` at all recommendation construction call sites.

## Files Changed

| File | Change Type | Description |
|---|---|---|
| src/portfolio/models.py | Additive | Five new fields with safe defaults added to PortfolioRecommendation |
| src/portfolio/recommendations.py | Additive | card_type and execution_state set at 5 construction sites |
| src/portfolio/phase_e_synthesis.py | Additive | card_type and execution_state set at 6 construction sites |

## Files Added

| File | Description |
|---|---|
| tests/test_pra_impl_01_card_schema.py | 15 new tests for PRA-IMPL-01 contract |
| pra_impl_01_implementation_plan.md | Implementation planning document |
| pra_impl_01_schema_mapping.md | Schema mapping table |
| pra_impl_01_test_plan.md | Test plan document |

## Fields Added to PortfolioRecommendation

| Field | Default | Canonical Values |
|---|---|---|
| card_type | "DIAGNOSTIC" | ACTION, OBSERVATION, NARRATIVE, EXPLAINABILITY, DIAGNOSTIC |
| execution_state | "EXECUTABLE" | EXECUTABLE, BLOCKED_BY_POLICY, DEFERRED_BY_POLICY, INFORMATIONAL_ONLY |
| effective_action | "" | (empty until PRA-IMPL-02 policy pass) |
| evidence_link | "" | (empty; reference ID for supporting artifact) |
| card_lifecycle_state | "OBSERVED" | OBSERVED, ACTION_QUALIFIED, POLICY_ADJUSTED, DECISION_PENDING, EXECUTED |

## Construction Site card_type Assignment

| Location | recommendation_type | card_type assigned |
|---|---|---|
| recommendations.py REDUCE/INCREASE | REDUCE_OVERWEIGHT, INCREASE_UNDERWEIGHT | ACTION |
| recommendations.py concentration | DIVERSIFY_CONCENTRATION | ACTION |
| recommendations.py trim fallback | IMPROVE_RISK_PROFILE | ACTION |
| recommendations.py replay | IMPROVE_REPLAY_ALIGNMENT | ACTION |
| recommendations.py thematic | IMPROVE_SECTOR_EXPOSURE | ACTION |
| recommendations.py STI trim | STRATEGIC_TRIM_CANDIDATE | ACTION |
| recommendations.py STI retain signal | STRATEGIC_RETAIN_SIGNAL | OBSERVATION |
| phase_e_synthesis.py thematic | THEMATIC_SATURATION_NARRATIVE | NARRATIVE |
| phase_e_synthesis.py retain | STRATEGIC_RETAIN_NARRATIVE | NARRATIVE |
| phase_e_synthesis.py trim cluster | TOP_TRIM_CANDIDATES | ACTION |
| phase_e_synthesis.py construction | PORTFOLIO_CONSTRUCTION_NARRATIVE | NARRATIVE |
| phase_e_synthesis.py replay context | REPLAY_ALIGNMENT_CONTEXT | EXPLAINABILITY |
| phase_e_synthesis.py conviction cards | CONVICTION_EXPLAINABILITY_CARD | EXPLAINABILITY |

## Test Results

New tests: 15 passed, 0 failed  
Full regression suite: 1142 passed, 1 skipped, 0 failed  
(Prior baseline: 1127 passed, 1 skipped — 15 new tests added)

## Invariants Confirmed

- CW-DAS composite scores: unchanged
- ESS / Zacks / Danelfin signal values: unchanged
- UCF verdict computation: unchanged
- STI profile generation: unchanged
- Reconciliation inputs: unchanged
- Recommendation generation logic: unchanged (fields are additive only)
- Existing JSON serialisation via dataclasses.asdict(): fully backwards-compatible (additive fields auto-included)

## Limitations of This Implementation

- effective_action remains "" for all cards — will be populated in PRA-IMPL-02
- BLOCKED_BY_POLICY and DEFERRED_BY_POLICY execution states not yet set — PRA-IMPL-02 scope
- card_lifecycle_state defaults to OBSERVED for all cards — lifecycle transitions are PRA-IMPL-02+ scope
- No UI rendering changes — PRA-IMPL-03 scope

## Certification Decision

CERTIFIED — PRA-IMPL-01 is complete and ready for PRA-IMPL-02.
