# ISSUE-12D — Validation Plan: Dislocation Outcome Review Panel

**Date:** 2026-06-15

---

## 1. Test File
`tests/test_dislocation_outcome_review.py`

All tests deterministic, filesystem-isolated via `tmp_path`. No network calls.

---

## 2. Test Coverage Domains

### Domain 1 — UCF History Loading
| Test ID | Scenario | Expected |
|---------|----------|----------|
| T-01 | Empty PAR directory | Returns empty list, no exception |
| T-02 | Single PAR run with UCF verdicts | Returns one record per verdict |
| T-03 | Multiple dates, canonical selection (latest PAR wins) | One record set per date |
| T-04 | UCF verdict with all source_signals fields | All fields correctly extracted |
| T-05 | UCF verdict missing source_signals | Falls back to empty/zero defaults |
| T-06 | Malformed snapshot_date in metadata | That run skipped |
| T-07 | Non-DIL-eligible labels (MAINTAIN, TACTICAL_GROWTH) | Excluded from DOR records |
| T-08 | DIL-eligible labels (CCL, HCA, DC, TRIM_WATCH) | Included in DOR records |

### Domain 2 — Action Attribution Integration
| Test ID | Scenario | Expected |
|---------|----------|----------|
| T-09 | DIL record with FOLLOWED status in attribution cache | action_status=FOLLOWED |
| T-10 | DIL record with no matching attribution entry | action_status=IGNORED (default) |
| T-11 | Multiple attribution records for same symbol | Highest-status record used |
| T-12 | Attribution cache missing | All records default to IGNORED |

### Domain 3 — Outcome Reconstruction
| Test ID | Scenario | Expected |
|---------|----------|----------|
| T-13 | Attribution record with outcome=WINNER | outcome=WINNER in DOR record |
| T-14 | Attribution record with outcome=LOSER | outcome=LOSER |
| T-15 | No attribution record for symbol | outcome=UNKNOWN |
| T-16 | Benchmark record with excess_return_pct | excess_return_pct populated |
| T-17 | No benchmark record for symbol | excess_return_pct=0.0 |

### Domain 4 — Governance Flag Assignment
| Test ID | Scenario | Expected |
|---------|----------|----------|
| T-18 | IGNORED + WINNER outcome | governance_flags contains MISSED_WINNER |
| T-19 | FOLLOWED + WINNER | no MISSED_WINNER flag |
| T-20 | FOLLOWED + LOSER | governance_flags contains FOLLOWED_LOSER |
| T-21 | Conflict flags present in UCF verdict | governance_flags contains SIGNAL_CONFLICT |
| T-22 | No conflict, FOLLOWED, WINNER | governance_flags is empty |

### Domain 5 — Cohort Analysis
| Test ID | Scenario | Expected |
|---------|----------|----------|
| T-23 | 3 CCL records: 2 FOLLOWED WINNER, 1 IGNORED | follow_rate=66.7%, win_rate=100% |
| T-24 | All records IGNORED | follow_rate=0%, win_rate=0% |
| T-25 | All records FOLLOWED WINNER | follow_rate=100%, win_rate=100% |
| T-26 | Mixed outcomes WINNER/LOSER among followed | win_rate = winners/(w+l)*100 |
| T-27 | Multiple UCF labels present | One CohortSummary per label |
| T-28 | Label with zero records | Omitted or zero counts |
| T-29 | avg_alpha_pct only from followed records | Ignores IGNORED records |

### Domain 6 — Governance Observations
| Test ID | Scenario | Expected |
|---------|----------|----------|
| T-30 | CCL ignored + WINNER | Observation mentions CCL missed winners |
| T-31 | No followed recommendations | Observation notes no follows |
| T-32 | Best performing cohort | Observation names the cohort |
| T-33 | Signal conflict records with low win rate | Observation notes conflict governance |
| T-34 | Observations capped at 6 | len(observations) <= 6 |

### Domain 7 — API Payload Integrity
| Test ID | Scenario | Expected |
|---------|----------|----------|
| T-35 | pis_dor_summary() required fields | all top-level keys present |
| T-36 | pis_dor_cohorts() cohort fields | ucf_label, follow_rate_pct, win_rate_pct all present |
| T-37 | pis_dor_recommendations() record fields | record_id, action_status, outcome, governance_flags present |
| T-38 | record_id unique | no duplicate record_ids |
| T-39 | counts sum: followed + ignored = total | arithmetic invariant holds |

### Domain 8 — Edge Cases
| Test ID | Scenario | Expected |
|---------|----------|----------|
| T-40 | No ucf_verdicts.json files | Empty payload, no exception |
| T-41 | All outcomes UNKNOWN | win_rate=0.0, observations note coverage gap |
| T-42 | Single date of history | Valid output; dates_covered=1 |
| T-43 | MAINTAIN/TACTICAL_GROWTH labels excluded | total_dil_records count correct |

---

## 3. Regression Surface
PIS-12D modifies:
- `scripts/run_outcome_ui.py` — adds 3 new elif branches
- `ui/pis_dashboard/app.js` — adds new subsystem + sections + renders
- `ui/pis_dashboard/index.html` — adds new panels

**Regression risk: LOW.** No existing analytical code is touched.

---

## 4. Validation Pass Criteria

| Criteria | Pass Condition |
|----------|---------------|
| All T-01 through T-43 pass | 0 failures |
| Full existing test suite | 0 regressions |
| `pis_dor_summary()` live | No exceptions, valid JSON |
| `pis_dor_cohorts()` live | ≥ 1 cohort returned |
| `pis_dor_recommendations()` live | ≥ 1 record returned |
| Dashboard sections load | No JS errors |
