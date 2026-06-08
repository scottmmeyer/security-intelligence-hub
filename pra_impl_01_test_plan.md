# PRA-IMPL-01 Test Plan

Project: Security Intelligence Hub (SIH)  
Issue: PRA-IMPL-01 Typed Recommendation Contract and Card Schema  
Date: 2026-06-08

## Test File

tests/test_pra_impl_01_card_schema.py

## Test Cases

### T01 — card_type field present on PortfolioRecommendation

Verify: dataclasses.asdict(rec) contains key "card_type"

### T02 — card_type default is DIAGNOSTIC

Verify: PortfolioRecommendation constructed without card_type gets card_type="DIAGNOSTIC"

### T03 — ACTION recommendation_types get card_type="ACTION"

Test each: REDUCE_OVERWEIGHT, INCREASE_UNDERWEIGHT, DIVERSIFY_CONCENTRATION,
IMPROVE_RISK_PROFILE, IMPROVE_REPLAY_ALIGNMENT, IMPROVE_SECTOR_EXPOSURE,
STRATEGIC_TRIM_CANDIDATE, TOP_TRIM_CANDIDATES

### T04 — OBSERVATION recommendation_types get card_type="OBSERVATION"

Test: STRATEGIC_RETAIN_SIGNAL

### T05 — NARRATIVE recommendation_types get card_type="NARRATIVE"

Test each: STRATEGIC_RETAIN_NARRATIVE, THEMATIC_SATURATION_NARRATIVE, PORTFOLIO_CONSTRUCTION_NARRATIVE

### T06 — EXPLAINABILITY recommendation_types get card_type="EXPLAINABILITY"

Test each: REPLAY_ALIGNMENT_CONTEXT, CONVICTION_EXPLAINABILITY_CARD

### T07 — execution_state present and defaults to EXECUTABLE

Verify default value on minimal construction.

### T08 — effective_action defaults to empty string

Verify default value on minimal construction.

### T09 — evidence_link defaults to empty string

Verify default value on minimal construction.

### T10 — card_lifecycle_state defaults to OBSERVED

Verify default value on minimal construction.

### T11 — Existing fields unchanged by new fields

Verify a full recommendation dict retains all pre-existing keys with correct values.

### T12 — asdict serialisation includes all five new fields

Verify dataclasses.asdict output contains all five new field keys.

## Regression Requirement

Full test suite (1127+ tests) must pass after implementation.
