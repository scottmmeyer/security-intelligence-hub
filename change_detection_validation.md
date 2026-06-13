# Change Detection Validation (PIS-002)

## Test suite

Primary test file:

- `tests/test_pis_change_detection_phase1.py`

Coverage includes:

1. new position detection
2. exited position detection
3. increased position detection
4. reduced/no-change semantics by quantity delta
5. cash change calculation
6. multi-account date aggregation
7. snapshot-date ordering correctness
8. API payload shape for latest/detail/summary readers
9. empty-history behavior
10. route wiring presence for PIS change endpoints

UI/API contract extension in:

- `tests/test_pis_ui_phase1_dashboard.py`

Additional checks include:

- new dashboard section labels for change detection
- `app.js` fetch wiring for `/api/pis/changes/latest` and `/api/pis/change-summary`

## Regression command

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/test_pis_change_detection_phase1.py tests/test_pis_backfill_01.py tests/test_pis_ui_phase1_dashboard.py -q
```

## Result

- `17 passed`

## Acceptance interpretation

- Engine computes deterministic N vs N-1 changes.
- Persisted outputs are generated and queryable.
- UI has dedicated sections for latest changes and summary history.
- No regressions observed in adjacent PIS backfill/UI suites.
