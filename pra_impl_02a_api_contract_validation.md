# PRA-IMPL-02A API Contract Validation

## Objective

Validate PRA-IMPL-02 field visibility in the actual CRA API contract consumed by Portfolio Alignment UI:

- Endpoint: `GET /api/cra/proposal`
- Serialization path: endpoint -> `build_proposal_from_manifest` -> `RotationProposal.to_dict()` -> JSON response

## Tests added

File: `tests/test_pra_impl_02a_api_contract.py`

Approach:

- Starts the real HTTP handler (`scripts/run_outcome_ui.py`)
- Calls `/api/cra/proposal` over HTTP
- Asserts JSON payload fields (source + target)
- Validates both populated and empty-field scenarios

## Assertions

### Source payload checks

- `reduction_score`
- `reduction_reason`
- `policy_alignment_reason`

### Target payload checks

- `funding_source_symbol`
- `funding_source_category`
- `funding_source_score`
- `funding_source_reason`
- `funding_source_alternatives`
- `funding_policy_alignment_reason`

### Scenario checks

- populated values preserved in JSON
- empty/default values still present in JSON contract

## Validation run

Command slice:

`python -m pytest -q tests/test_pra_impl_02a_api_contract.py`

Result:

- Included in combined PRA-IMPL-02A run: `16 passed`
- Included in full regression run: `136 passed`

## Conclusion

CRA API payload contract coverage is now explicit at the endpoint boundary used by UI.
