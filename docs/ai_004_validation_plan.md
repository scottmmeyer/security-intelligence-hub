# AI-004 — Validation Plan: Allocation Policy Version Diff Engine

**Date:** 2026-06-15

---

## 1. Test File
`tests/test_policy_version_diff.py`

All tests deterministic, filesystem-isolated. No network calls. venv python.

---

## 2. Test Coverage Domains

### Domain 1 — Policy Snapshot Collection
| Test ID | Scenario | Expected |
|---------|----------|----------|
| T-01 | Empty PAR directory | Returns empty list, no exception |
| T-02 | Single PAR run with alignment.csv | Returns one snapshot entry |
| T-03 | Two dates, canonical selection (latest PAR wins) | One snapshot per date |
| T-04 | Malformed snapshot_date skipped | Only valid dates included |
| T-05 | Missing alignment.csv → PAR run skipped | Only runs with alignment included |
| T-06 | node_key extracted from alignment.csv | All non-empty node_keys captured |
| T-07 | target_pct and tactical_target_pct both extracted | Both fields populated |

### Domain 2 — Policy Version Registry
| Test ID | Scenario | Expected |
|---------|----------|----------|
| T-08 | All snapshots same recalculation_id | One PolicyVersion |
| T-09 | Two distinct recalculation_ids | Two PolicyVersions |
| T-10 | Three runs same recalc_id | run_count = 3 |
| T-11 | first_seen_date is earliest date for that recalc_id | Correct date |
| T-12 | last_seen_date is latest date for that recalc_id | Correct date |
| T-13 | node_targets from most recent snapshot in group | Most recent wins |
| T-14 | fingerprint_id = recalc_id + content hash | Deterministic format |

### Domain 3 — Policy Diff Computation
| Test ID | Scenario | Expected |
|---------|----------|----------|
| T-15 | Identical targets → no changes | total_changes = 0 |
| T-16 | One node target increased | INCREASED direction, correct delta |
| T-17 | One node target decreased | DECREASED direction, correct delta |
| T-18 | Node added in new version | ADDED in added_nodes |
| T-19 | Node removed in new version | REMOVED in removed_nodes |
| T-20 | Multiple changes simultaneously | All changes in changed_targets |
| T-21 | Delta < 0.001pp treated as no change | Not included in changed_targets |
| T-22 | Changed targets sorted by abs(delta) descending | Largest change first |

### Domain 4 — Governance Observations
| T-23 | Single version | Observation mentions single version and run count |
| T-24 | Two versions | Observation mentions transition |
| T-25 | Structural constraints present | Observation includes constraint values |
| T-26 | Policy_id and effective_date in config | Observation includes both |
| T-27 | Observations capped at 6 | len(observations) <= 6 |

### Domain 5 — API Payload Integrity
| T-28 | pis_policy_current() required fields | all keys present |
| T-29 | pis_policy_history() versions list | version count correct |
| T-30 | pis_policy_diff() with no changes | has_changes=False |
| T-31 | pis_policy_diff() with changes | has_changes=True, diffs populated |
| T-32 | node_targets in current payload | dict with node_key keys |

### Domain 6 — Edge Cases
| T-33 | No config files | Returns defaults, no exception |
| T-34 | Two recalc_ids same targets | diff shows no changes |
| T-35 | Single PAR run date | Valid payload, dates_covered=1 |

---

## 3. Validation Pass Criteria

| Criteria | Pass Condition |
|----------|---------------|
| All T-01 through T-35 pass | 0 failures |
| Full existing test suite | 0 regressions |
| `pis_policy_current()` live | No exceptions, valid JSON |
| `pis_policy_history()` live | ≥ 1 version returned |
| `pis_policy_diff()` live | Valid response (no changes = OK) |
