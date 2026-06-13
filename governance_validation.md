# Governance Validation

## Validation Objectives
- Verify deterministic PASS, WARNING, and REJECT outcomes
- Verify account contamination is classifiable as REJECT
- Verify warning vs reject precedence
- Verify API payload contract for governance endpoints
- Verify dashboard contract for governance UI section

## Test Coverage Added
New tests in tests/test_pis_governance_stage_a.py:
- expected scope pass
- contaminated scope reject
- value warning
- value reject
- source artifact warning
- combined rule evaluation with reject precedence
- configurable threshold behavior
- governance latest and summary API payload validation

Updated tests in tests/test_pis_ui_phase1_dashboard.py:
- governance endpoint references in dashboard app
- governance section presence in dashboard HTML

## Deterministic Behavior Verification
Determinism checks validated by:
- explicit fixed inputs with fixed outputs
- stable reason codes
- stable status precedence ordering
- repeated API-style evaluation over same input producing same counts

## Preservation Validation
Governance writes only to:
- data/history/pis/governance/snapshot_governance.csv

Historical snapshot index and partitions are read-only inputs.
