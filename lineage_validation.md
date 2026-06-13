# Lineage Validation (PIS-003)

## Primary tests

- `tests/test_pis_recommendation_lineage_01.py`

Validation requirements covered:

1. high-confidence direct symbol match
2. medium-confidence delayed match
3. low-confidence thematic match
4. unmatched change handling
5. multiple recommendation candidates
6. confidence ranking/tie-break behavior
7. API payload shape checks (latest/detail/summary)
8. empty-history behavior

Additional contract checks:

- route presence for lineage APIs in server
- dashboard sections and endpoint wiring in UI contract test

## Regression command

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/test_pis_recommendation_lineage_01.py tests/test_pis_change_detection_phase1.py tests/test_pis_backfill_01.py tests/test_pis_ui_phase1_dashboard.py -q
```

## Result

- `24 passed`

## Acceptance interpretation

- PIS can now map observed changes to likely recommendation ancestry.
- Confidence assignment is deterministic and persisted.
- Unmatched changes are explicitly visible for operator follow-up.
