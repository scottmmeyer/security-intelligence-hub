# Attribution Validation

## Deterministic Test Coverage

Implemented in `tests/test_pis_performance_attribution_01.py`:

1. Outcome classification thresholds
2. Record generation and latest payload correctness
3. History and aggregate summary correctness
4. CSV contract header validation
5. API route presence in `scripts/run_outcome_ui.py`

Dashboard/API contract coverage extended in `tests/test_pis_ui_phase1_dashboard.py`:

1. Attribution endpoint references in app
2. Attribution section anchors in dashboard HTML
3. Attribution executive card and renderer hook presence

## Focused Regression

Command:

```bash
/Users/scottmmeyer/Projects/security-intelligence-hub/.venv/bin/python -m pytest -q tests/test_pis_performance_attribution_01.py tests/test_pis_ui_phase1_dashboard.py
```

Result:
- `16 passed`

## Broad Regression

Command:

```bash
/Users/scottmmeyer/Projects/security-intelligence-hub/.venv/bin/python -m pytest -q tests/test_pis_governance_stage_a.py tests/test_pis_canonical_daily_004b.py tests/test_pis_change_detection_phase1.py tests/test_pis_recommendation_lineage_01.py tests/test_pis_performance_attribution_01.py tests/test_pis_ui_phase1_dashboard.py
```

Result:
- `41 passed`

## Validation Conclusion

PERFORMANCE-ATTRIBUTION-01 implementation is deterministic, canonical-only, and regression-safe within the covered PIS scope.
