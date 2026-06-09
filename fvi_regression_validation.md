# FVI Regression Validation

Repository: security-intelligence-hub  
Date: 2026-06-09

## Test Results

| Suite | Tests | Result |
|---|---|---|
| tests/test_pra_impl_05_fvi.py | 18 | ALL PASS |
| Full regression suite | 1192 | ALL PASS (1 skipped, 0 failed) |
| Prior baseline | 1174 | +18 new FVI tests |

## Invariant Confirmation

The following are confirmed unchanged after PRA-IMPL-05 Phase 1:

| Invariant | Status |
|---|---|
| CW-DAS composite scores | UNCHANGED — fvi_loader has no scoring imports (test: TestNoScoringImpact) |
| ESS signal values | UNCHANGED — FVI reads no signal files |
| Zacks / Danelfin / Yahoo values | UNCHANGED — FVI reads no signal files |
| Conviction tier computation | UNCHANGED — fvi_loader makes no UCF calls |
| Recommendation generation | UNCHANGED — FVI data only attached to result dict |
| Recommendation count | UNCHANGED — fvi_data is a separate key, not in recs list |
| Deployment queue ranking | UNCHANGED — FVI makes no queue modifications |
| Policy execution states | UNCHANGED — FVI makes no policy calls |
| Alignment calculations | UNCHANGED — FVI reads alignment data but does not write it |

## Key Regression Tests

- test_all_portfolio_funds_have_fvi: confirms 15 fund vehicles have FVI records
- test_fvi_loader_has_no_scoring_imports: confirms no accidental scoring dependency
- test_missing_file_returns_empty_dict: confirms graceful degradation
- TestNoScoringImpact: AST-based check that fvi_loader imports no scoring modules
