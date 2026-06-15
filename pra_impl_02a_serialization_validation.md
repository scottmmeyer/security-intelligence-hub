# PRA-IMPL-02A Serialization Validation

## Objective

Validate that PRA-IMPL-02 fields serialize deterministically from CRA models via `RotationProposal.to_dict()` and fail loudly if fields disappear/rename/change semantics.

## Tests added

File: `tests/test_pra_impl_02a_serialization_contracts.py`

### Covered assertions

1. `CapitalSourceRecord` populated serialization:
   - `reduction_score`
   - `reduction_reason`
   - `policy_alignment_reason`
2. `CapitalSourceRecord` empty serialization:
   - fields present when values are default/empty
3. `RotationDeploymentTarget` populated serialization:
   - `funding_source_symbol`
   - `funding_source_category`
   - `funding_source_score`
   - `funding_source_reason`
   - `funding_source_alternatives`
   - `funding_policy_alignment_reason`
4. `RotationDeploymentTarget` empty serialization:
   - all fields present with expected empty/default values

## Validation run

Command:

`python -m pytest -q tests/test_pra_impl_02a_serialization_contracts.py`

Result:

- Included in combined PRA-IMPL-02A run: `16 passed`
- Included in full regression run: `136 passed`

## Conclusion

Serialization contracts for all PRA-IMPL-02 CRA fields are now explicitly protected by deterministic tests.
