# SIGNAL-GOV-02A Validation — Regression Test Results

**Date:** 2026-06-15  
**Test File:** `tests/test_signal_gov_02a_conflict_classifier.py`  
**Result:** 27/27 PASSED

---

## Test Coverage Map

| # | Test Name | Covers |
|---|-----------|--------|
| 1 | `test_conflicting_signal_from_fmp_sell_votes` | 1 sell + majority buys → CONFLICTING_SIGNAL |
| 2 | `test_conflicting_signal_bearish_zacks_bullish_danelfin` | Bearish Zacks + bullish Danelfin → CONFLICTING_SIGNAL |
| 3 | `test_no_conflicting_signal_all_bullish` | All-bullish → no badge |
| 4 | `test_high_analyst_disagreement_operator_annotation` | Operator annotation → HIGH_ANALYST_DISAGREEMENT |
| 5 | `test_high_analyst_disagreement_auto_detect` | Auto-detect: sell_ratio ≥ 10% + buys present |
| 6 | `test_high_analyst_disagreement_not_when_significant` | Not emitted when SIGNIFICANT_CONFLICT present |
| 7 | `test_hold_consensus_from_consensus_label` | HOLD label → HOLD_CONSENSUS badge |
| 8 | `test_hold_consensus_severity_info` | HOLD_CONSENSUS is INFO severity |
| 9 | `test_no_hold_consensus_when_buy_label` | BUY consensus → no HOLD_CONSENSUS |
| 10 | `test_significant_conflict_above_threshold` | sell_ratio ≥ 15% → SIGNIFICANT_CONFLICT WARN |
| 11 | `test_significant_conflict_severity_warn` | SIGNIFICANT_CONFLICT always WARN |
| 12 | `test_high_hold_ratio_majority_holds` | ≥50% hold + BUY consensus → HIGH_HOLD_RATIO INFO |
| 13 | `test_no_high_hold_ratio_when_hold_consensus` | HOLD_CONSENSUS takes priority |
| **14** | **`test_significant_conflict_exactly_at_threshold`** | **Exactly at 15% → fires (≥ comparison)** |
| **15** | **`test_significant_conflict_below_threshold`** | **Below 15% → does not fire** |
| **16** | **`test_high_hold_ratio_exactly_at_threshold`** | **Exactly at 50% → fires** |
| **17** | **`test_empty_analyst_set_no_crash`** | **Zero analysts → empty list, no crash** |
| **18** | **`test_empty_fmp_with_bullish_other_sources`** | **No FMP, bullish Zacks/Dan → no conflict** |
| **19** | **`test_signal_conflict_to_dict_keys`** | **to_dict() has {type, severity, description}** |
| **20** | **`test_serialization_json_roundtrip`** | **JSON roundtrip preserves all fields** |
| **21** | **`test_no_badges_for_clean_signal`** | **All-bullish symbol → zero badges** |
| **22** | **`test_operator_annotation_triggers_disagreement_even_with_no_sells`** | **Operator annotation fires even with 0 sells** |
| **23** | **`test_significant_conflict_suppresses_conflicting_signal`** | **SIGNIFICANT_CONFLICT prevents CONFLICTING_SIGNAL double-badge** |
| **24** | **`test_significant_conflict_suppresses_high_analyst_disagreement`** | **SIGNIFICANT_CONFLICT prevents HAD double-badge** |
| **25** | **`test_get_conflicts_for_symbols_integration`** | **End-to-end with fake signal CSVs** |
| **26** | **`test_get_conflicts_empty_symbol_list_returns_empty`** | **Empty symbols → {}** |
| **27** | **`test_get_conflicts_missing_signal_files_no_crash`** | **Missing CSV files → graceful empty result** |

---

## Required Coverage Categories (from Issue)

| Required | Test Numbers | Status |
|----------|-------------|--------|
| CONFLICTING_SIGNAL classification | 1, 2, 3 | ✅ PASS |
| HIGH_ANALYST_DISAGREEMENT classification | 4, 5, 6 | ✅ PASS |
| HOLD_CONSENSUS classification | 7, 8, 9 | ✅ PASS |
| SIGNIFICANT_CONFLICT classification | 10, 11 | ✅ PASS |
| Threshold boundary behavior | 14, 15, 16 | ✅ PASS |
| Empty analyst set | 17, 18 | ✅ PASS |
| API payload serialization | 19, 20 | ✅ PASS |
| Dashboard section rendering | (UI — JS, async load) | ✅ Manual verified |

---

## Live Data Validation (2026-06-15)

| Symbol | Expected | Actual Badge | Match |
|--------|---------|-------------|-------|
| VRT | clean | `[]` | ✅ |
| MTZ | clean | `[]` | ✅ |
| NUE | CONFLICTING_SIGNAL (3/32 sells) | `CONFLICTING_SIGNAL WARN` | ✅ |
| PCB | HOLD_CONSENSUS (consensus=HOLD) | `HOLD_CONSENSUS INFO` | ✅ |
| SANM | HAD (2/17=11.8%) + HIGH_HOLD_RATIO | `HIGH_ANALYST_DISAGREEMENT WARN` + `HIGH_HOLD_RATIO INFO` | ✅ |
| TSLA | SIGNIFICANT_CONFLICT (15/81=18.5%) | `SIGNIFICANT_CONFLICT WARN` | ✅ |

All badges match the classifications documented in SIGNAL-GOV-02 design analysis.

---

## No New Regression Failures

Pre-existing test suite failures (5 total) are unchanged from before SIGNAL-GOV-02A:
- `test_pis_phase1::test_pis_registration_uses_canonical_sih_portfolio_object` (PIS-INTEGRITY-01)
- `test_partitioned_history_storage::test_signal_partition_is_immutable...` (pre-existing data state)
- 3× `test_signal_coverage_phase6` (pre-existing signal coverage state)

SIGNAL-GOV-02A introduced **zero new test failures**.

---

## Governance Invariants Confirmed

| Invariant | Verified |
|-----------|---------|
| No change to composite score formula | ✅ |
| No change to CW-DAS signal weights | ✅ |
| No change to deployment queue ranking | ✅ |
| No change to CPV rules | ✅ |
| No change to recommendation counts or types | ✅ |
| Advisory badges are read-only display only | ✅ |
