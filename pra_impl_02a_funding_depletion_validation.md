# PRA-IMPL-02A Funding Depletion Validation

## Objective

Validate that deployment targets consume source proceeds progressively and fall through to alternatives after depletion.

## Test coverage

Updated existing suite:

- `tests/test_pra_impl_02_funding_policy.py`

Added tests:

1. `test_funding_source_capacity_depletes_across_targets`
   - first target consumes top source capacity
   - next target falls to next eligible source
2. `test_depleted_sources_removed_from_alternatives`
   - depleted source is not offered as an alternative for downstream targets

## Capacity trace example (post-02A runtime)

Observed deterministic trace from live function execution:

- `1:VRT amount=20000 source=AAPL alternatives=[MSFT, TSLA]`
- `2:ARW amount=20000 source=MSFT alternatives=[TSLA]`
- `3:NVDA amount=10000 source=TSLA alternatives=[]`

Interpretation:

- Target 1 consumes first-ranked source proceeds.
- Target 2 cannot reuse exhausted capacity and falls through.
- Target 3 receives next remaining source.

## Before vs after behavior

### Before (audit finding)

- Multiple targets could keep selecting the same top source irrespective of cumulative usage.

### After (implemented)

- Source proceeds are consumed cumulatively.
- Subsequent targets only consider remaining capacity.
- Alternatives list reflects post-consumption availability.

## Regression evidence

Full requested run:

`python -m pytest -q tests/test_pra_impl_02_funding_policy.py tests/test_cra_phase_23_6a.py tests/test_cash_semantics.py tests/test_pra_impl_02a_serialization_contracts.py tests/test_pra_impl_02a_api_contract.py tests/test_pra_impl_02a_pap_rationale.py`

Result:

- `136 passed`

## Conclusion

Funding depletion is implemented and validated with deterministic multi-target behavior.
