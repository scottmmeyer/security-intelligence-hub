# Explainability Validation

## Deterministic Coverage

Implemented tests:
- `tests/test_allocation_explainability_01.py`
- `tests/test_wp04_1_ui_prototype.py`

Covered behaviors:
1. policy mapping
2. signal mapping
3. funding-driver extraction
4. multiple-driver recommendations
5. missing-driver handling
6. API payload contract presence
7. dashboard explainability contract presence

## Focused Regression

Command:

```bash
/Users/scottmmeyer/Projects/security-intelligence-hub/.venv/bin/python -m pytest -q tests/test_allocation_explainability_01.py tests/test_wp04_1_ui_prototype.py
```

Result:
- `12 passed`

## Broad Regression

Command:

```bash
/Users/scottmmeyer/Projects/security-intelligence-hub/.venv/bin/python -m pytest -q tests/test_allocation_explainability_01.py tests/test_wp04_1_ui_prototype.py tests/test_pis_performance_attribution_01.py tests/test_pis_ui_phase1_dashboard.py
```

Result:
- `28 passed`

## Validation Conclusion

The explainability layer is deterministic, additive, persisted, and visible through both APIs and the Portfolio Alignment UI.
