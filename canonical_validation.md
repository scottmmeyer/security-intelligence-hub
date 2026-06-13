# Canonical Validation

## Validation Goals
- Verify governance-gated canonical selection rules
- Verify deterministic tie-breaking behavior
- Verify canonical persistence and API payloads
- Verify dashboard contract integration
- Verify downstream change/lineage pipeline compatibility

## New Deterministic Tests
Added: tests/test_pis_canonical_daily_004b.py

Coverage:
1. PASS preferred over WARNING
2. REJECT excluded
3. WARNING selected when no PASS exists
4. Latest PASS selected
5. Deterministic lexical tie-break
6. Canonical persistence output file creation
7. Canonical API payload shape validation

## Updated Existing Tests
Updated: tests/test_pis_ui_phase1_dashboard.py

Coverage:
1. Canonical API calls present in dashboard app contract
2. Canonical dashboard section markup presence
3. Timeline fixture aligned to governance-gated canonical selection

Updated: tests/test_pis_change_detection_phase1.py

Coverage:
1. Fixtures now satisfy governance gate for canonical change computation
2. Canonical preference behavior validated in date-pair change detection scenario

Updated: tests/test_pis_recommendation_lineage_01.py

Coverage:
1. Candidate override is passed through lineage read APIs under canonical recompute flow
2. Confidence and ranking assertions remain deterministic

## Regression Execution
Command:
- PYTHONPATH=. .venv/bin/pytest -q tests/test_pis_canonical_daily_004b.py tests/test_pis_change_detection_phase1.py tests/test_pis_recommendation_lineage_01.py tests/test_pis_ui_phase1_dashboard.py

Result:
- 23 passed

## Runtime Endpoint Verification
Verified HTTP 200:
- /api/pis/canonical/latest
- /api/pis/canonical/history
- /api/pis/canonical-summary
- /api/pis/summary
- /api/pis/changes/latest
- /api/pis/lineage/latest
