# PRA-IMPL-02A Contract Audit

## Scope

PRA-IMPL-02A hardens contract coverage for PRA-IMPL-02 additive fields across:

- CRA model serialization (`RotationProposal.to_dict()`)
- CRA API payload (`GET /api/cra/proposal`)
- PAP recommendation generator output clauses (not parser-only)

Fields in scope:

### CapitalSourceRecord

- `reduction_score`
- `reduction_reason`
- `policy_alignment_reason`

### RotationDeploymentTarget

- `funding_source_symbol`
- `funding_source_category`
- `funding_source_score`
- `funding_source_reason`
- `funding_source_alternatives`
- `funding_policy_alignment_reason`

## What was added

1. Serialization contract suite:
   - `tests/test_pra_impl_02a_serialization_contracts.py`
2. API contract suite (real HTTP endpoint path):
   - `tests/test_pra_impl_02a_api_contract.py`
3. PAP rationale generation E2E suite:
   - `tests/test_pra_impl_02a_pap_rationale.py`
4. Depletion behavior tests added to existing PRA suite:
   - `tests/test_pra_impl_02_funding_policy.py`

## Deterministic acceptance checks

- Field-presence tests for populated and empty scenarios.
- Value checks for correct types/values when populated.
- Empty-value contract checks (no silent field removal/rename).
- API payload tests through `/api/cra/proposal` JSON response, not internal objects only.
- Generator output check for all required funding rationale clauses.

## Result

Contract hardening scope is implemented and passing.

- Targeted new/updated suites: `16 passed`
- Full requested regression set: `136 passed`
