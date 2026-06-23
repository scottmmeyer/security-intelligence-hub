# PIS-007 — Validation Plan: Allocation Drift Trend Visibility

**Date:** 2026-06-15

---

## 1. Test File

`tests/test_pis_allocation_drift_trends.py`

All tests are deterministic: same inputs → same outputs. No filesystem writes. No external calls.

---

## 2. Test Coverage Domains

### Domain 1 — Historical Reconstruction
| Test ID | Description | Expected |
|---------|-------------|----------|
| T-01 | Empty PAR directory | Returns payload with `dates_available: 0`, empty `nodes` |
| T-02 | Single PAR run, single node | Reconstructs one entry; trend is STABLE; no prior drift |
| T-03 | Multiple PAR runs same date — latest wins | Only most-recent `created_at_utc` contributes |
| T-04 | Multiple PAR runs different dates | All dates represented; ascending order |
| T-05 | Missing `alignment.csv` in a PAR run | That run silently skipped; others retained |
| T-06 | `effective_actual_pct` present | Used as `actual_pct` in history |
| T-07 | `effective_actual_pct` absent, `actual_pct` present | Falls back to `actual_pct` |
| T-08 | `tactical_target_pct` present | Used as `target_pct` in history |
| T-09 | `tactical_target_pct` absent, `target_pct` present | Falls back to `target_pct` |
| T-10 | Node row with empty `effective_actual_pct` AND empty `actual_pct` | Row skipped |
| T-11 | Node appears in 10 of 15 dates | `dates_available = 10` for that node |
| T-12 | Malformed `snapshot_date` in metadata | PAR run skipped |

---

### Domain 2 — Canonical Date Selection
| Test ID | Description | Expected |
|---------|-------------|----------|
| T-13 | Three runs: two same date (diff times), one different | Two dates; same-date uses latest `created_at_utc` |
| T-14 | Dates returned ascending | `canonical_dates` is sorted ascending |
| T-15 | `snapshot_date` with time component (not just date) | First 10 chars used; valid |

---

### Domain 3 — Drift Calculation
| Test ID | Description | Expected |
|---------|-------------|----------|
| T-16 | actual=20.0, target=20.0 | drift_pct=0.0, direction=ON_TARGET |
| T-17 | actual=25.0, target=20.0 | drift_pct=+5.0, direction=OVERWEIGHT |
| T-18 | actual=15.0, target=20.0 | drift_pct=−5.0, direction=UNDERWEIGHT |
| T-19 | drift recomputed from actual/target, not CSV field | Internal consistency ensured |

---

### Domain 4 — Trend Direction
| Test ID | Description | Expected |
|---------|-------------|----------|
| T-20 | OVERWEIGHT: drift grows +2 → +4 | WORSENING (magnitude increased) |
| T-21 | OVERWEIGHT: drift shrinks +4 → +2 | IMPROVING (magnitude decreased) |
| T-22 | UNDERWEIGHT: drift grows −2 → −4 | WORSENING (magnitude increased) |
| T-23 | UNDERWEIGHT: drift shrinks −4 → −2 | IMPROVING (magnitude decreased) |
| T-24 | Drift change < 0.5pp | STABLE |
| T-25 | Only one history entry | STABLE (no prior to compare) |
| T-26 | OVERWEIGHT → ON_TARGET (near zero) | IMPROVING |

---

### Domain 5 — Trend Severity
| Test ID | Description | Expected |
|---------|-------------|----------|
| T-27 | abs(magnitude_delta) = 0.3 | NONE |
| T-28 | abs(magnitude_delta) = 1.2 | MINOR |
| T-29 | abs(magnitude_delta) = 3.5 | MODERATE |
| T-30 | abs(magnitude_delta) = 6.0 | SIGNIFICANT |
| T-31 | No prior drift (single entry) | NONE |

---

### Domain 6 — Drift Velocity
| Test ID | Description | Expected |
|---------|-------------|----------|
| T-32 | Two dates 7 days apart, drift: −2.0 → −3.0 | velocity = −1.0/7 ≈ −0.143 pp/day |
| T-33 | Single entry | velocity = 0.0 |
| T-34 | Oldest and newest same date (edge case) | velocity = 0.0 (days_span=0 handled, min=1) |

---

### Domain 7 — Persistence Score
| Test ID | Description | Expected |
|---------|-------------|----------|
| T-35 | All 5 entries OVERWEIGHT | persistence_score = 1.0 |
| T-36 | 3 of 5 entries OVERWEIGHT (current OVERWEIGHT) | persistence_score = 0.6 |
| T-37 | Single entry UNDERWEIGHT | persistence_score = 1.0 |
| T-38 | Mixed direction: 2 over, 3 under; current UNDERWEIGHT | persistence_score = 0.6 |

---

### Domain 8 — Summary Computation
| Test ID | Description | Expected |
|---------|-------------|----------|
| T-39 | Most improved = node with most negative magnitude_delta | Correct node identified |
| T-40 | Most deteriorated = node with most positive magnitude_delta | Correct node identified |
| T-41 | All nodes STABLE | `most_improved_node: null`, `most_deteriorated_node: null` |
| T-42 | improving/worsening/stable counts match node list | Count invariants hold |
| T-43 | Empty trends list | All counts 0, most_improved/deteriorated null |

---

### Domain 9 — Observations Generation
| Test ID | Description | Expected |
|---------|-------------|----------|
| T-44 | Node WORSENING MODERATE severity | Observation text contains node label, both drift values |
| T-45 | Node IMPROVING MODERATE severity | Observation text contains "improved" |
| T-46 | Node with persistence_score=1.0 and ≥5 dates | Observation contains "persistently" |
| T-47 | Node nearly on-target (drift < 0.5pp) | Observation contains "on-target" |
| T-48 | Many qualifying nodes | Observations capped at 8 |
| T-49 | No qualifying nodes | Returns empty list `[]` |

---

### Domain 10 — API Payload Integrity
| Test ID | Description | Expected |
|---------|-------------|----------|
| T-50 | `pis_allocation_drift_summary()` with 2+ dates | `generated_at` present, `dates_available` ≥ 2 |
| T-51 | `pis_allocation_drift_latest()` payload | `nodes` list with all trend fields |
| T-52 | `pis_allocation_drift_history()` payload | `nodes` list with `entries` sub-list; ascending by snapshot_date |
| T-53 | History entries ascending by snapshot_date | Ordering guaranteed |
| T-54 | Node key in latest payload matches history payload | Same node_key across all endpoints |

---

### Domain 11 — Worsening/Improving Detection
| Test ID | Description | Expected |
|---------|-------------|----------|
| T-55 | 5-entry sequence: drift magnitude increasing each period | Final trend = WORSENING |
| T-56 | 5-entry sequence: drift magnitude decreasing each period | Final trend = IMPROVING |
| T-57 | 5-entry with last two nearly equal (< 0.5pp change) | STABLE |
| T-58 | Node flips from OVERWEIGHT to UNDERWEIGHT | direction correctly updates; magnitude delta based on abs values |

---

### Domain 12 — Empty / Minimal History
| Test ID | Description | Expected |
|---------|-------------|----------|
| T-59 | Zero canonical dates | `pis_allocation_drift_summary()` returns `dates_available: 0` |
| T-60 | One canonical date | All nodes have `prior_drift_pct: null`, `drift_delta_pp: null` |
| T-61 | `pis_allocation_drift_history()` with zero dates | `dates: []`, `nodes: []` |

---

## 3. Test Fixtures

Tests use in-memory synthetic PAR run data rather than on-disk fixtures. Each test constructs a temporary directory tree matching the PAR artifact structure:

```
{tmp_root}/data/portfolio_ingestion/analysis_runs/
    PAR-TEST-001/
        run_metadata.json
        alignment.csv
    PAR-TEST-002/
        run_metadata.json
        alignment.csv
```

Fixture helpers:

```python
def make_alignment_csv(tmp_path, par_id, snapshot_date, nodes):
    """Write alignment.csv with given node rows."""

def make_run_metadata(tmp_path, par_id, snapshot_date, created_at_utc):
    """Write run_metadata.json."""
```

---

## 4. Isolation Requirements

- Tests do NOT touch `data/` in the project repo
- Tests use `tmp_path` pytest fixture (temp dir, cleaned after test)
- No server process required
- No network calls
- All computations invoked directly on module functions (not via HTTP)

---

## 5. Regression Surface

PIS-007 modifies:
- `scripts/run_outcome_ui.py` (adds new routes; does not change existing routes)
- `ui/pis_dashboard/app.js` (adds new sections; does not change existing sections)
- `ui/pis_dashboard/index.html` (adds new HTML panels; does not change existing panels)

**Regression risk: LOW.**

Existing test suite (1,000+ tests) covers PAR artifact reading, PIS storage, change detection, governance, canonical selection, lineage, and attribution. None of these are touched by PIS-007. Full suite must continue to pass after implementation.

---

## 6. Validation Pass Criteria

| Criteria | Pass Condition |
|----------|---------------|
| All T-01 through T-61 pass | 0 failures |
| Full existing test suite | 0 regressions |
| `pis_allocation_drift_summary()` returns valid JSON | No exceptions on live repo |
| `pis_allocation_drift_latest()` returns ≥ 1 node | Live data present |
| `pis_allocation_drift_history()` returns ≥ 19 dates | Live history present |
| Dashboard renders new sections | No JS errors; sections load |
| No changes to existing PAR artifacts | `git diff data/` shows no changes |
| API response time < 2s on first call | Acceptable for single-threaded server |
