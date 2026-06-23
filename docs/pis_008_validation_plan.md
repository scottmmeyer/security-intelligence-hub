# PIS-008 — Validation Plan: Recommendation Action Attribution

**Date:** 2026-06-15

---

## 1. Test File

`tests/test_pis_action_attribution.py`

All tests deterministic. Isolated via `tmp_path`. No network calls.

---

## 2. Test Coverage Domains

### Domain 1 — Action Status Classification
| Test ID | Scenario | Expected |
|---------|----------|----------|
| T-01 | BUY recommendation + INCREASED change | FOLLOWED |
| T-02 | BUY recommendation + NEW_POSITION change | FOLLOWED |
| T-03 | REDUCE recommendation + REDUCED change | FOLLOWED |
| T-04 | REDUCE recommendation + EXITED_POSITION change | FOLLOWED |
| T-05 | BUY recommendation + REDUCED change | OPPOSED |
| T-06 | BUY recommendation + EXITED_POSITION change | OPPOSED |
| T-07 | REDUCE recommendation + INCREASED change | OPPOSED |
| T-08 | NONE confidence lineage | IGNORED |
| T-09 | No matching change in window | IGNORED |
| T-10 | days_between > 30 | EXPIRED |
| T-11 | direction match + delta_market_value < $500 + LOW confidence | PARTIALLY_FOLLOWED |
| T-12 | Empty recommended_direction + match exists | FOLLOWED with LOW confidence |

### Domain 2 — Direction Resolution
| Test ID | Scenario | Expected |
|---------|----------|----------|
| T-13 | change_type = NEW_POSITION | direction = BUY |
| T-14 | change_type = INCREASED | direction = BUY |
| T-15 | change_type = EXITED_POSITION | direction = REDUCE |
| T-16 | change_type = REDUCED | direction = REDUCE |
| T-17 | change_type = UNCHANGED | direction = "" |

### Domain 3 — Source Classification
| Test ID | Scenario | Expected |
|---------|----------|----------|
| T-18 | source = "DEPLOYMENT_QUEUE" | source label preserved |
| T-19 | source = "PAP" | PAP |
| T-20 | source = "DIL" | DIL |
| T-21 | source = "CRA" | CRA |
| T-22 | source = "" or unknown | OTHER |

### Domain 4 — Delay Calculation
| Test ID | Scenario | Expected |
|---------|----------|----------|
| T-23 | rec_date 2026-06-01, change_date 2026-06-08 | response_days = 7 |
| T-24 | same-day rec and change | response_days = 0 |
| T-25 | IGNORED record | response_days = None |
| T-26 | days_between = 31 | EXPIRED, response_days = 31 |

### Domain 5 — Source Scorecard Computation
| Test ID | Scenario | Expected |
|---------|----------|----------|
| T-27 | 4 recs: 2 FOLLOWED, 1 IGNORED, 1 OPPOSED | follow_rate=50%, ignore_rate=25%, oppose_rate=25% |
| T-28 | All FOLLOWED | follow_rate=100% |
| T-29 | All IGNORED | follow_rate=0%, ignore_rate=100% |
| T-30 | Zero records for source | Returns empty or omits source |
| T-31 | followed recs with outcomes WINNER/LOSER | win_rate = winners/(winners+losers)*100 |
| T-32 | No outcome data | win_rate = 0.0 |

### Domain 6 — Aggregate Summary
| Test ID | Scenario | Expected |
|---------|----------|----------|
| T-33 | Mix of all statuses | counts sum to total_attribution_records |
| T-34 | follow_rate_pct correct | (followed + partially) / total * 100 |
| T-35 | avg_response_days only from responded records | ignores IGNORED/EXPIRED with no days |
| T-36 | observations generated | list, len >= 0 |
| T-37 | Empty lineage | all counts 0, empty scorecards |

### Domain 7 — Missed Opportunities
| Test ID | Scenario | Expected |
|---------|----------|----------|
| T-38 | IGNORED rec with BUY direction + WINNER outcome | appears in missed opportunities |
| T-39 | FOLLOWED rec | does NOT appear in missed opportunities |
| T-40 | IGNORED with NEUTRAL outcome | does NOT appear in missed |
| T-41 | Multiple missed — capped at 10 | len(missed) <= 10 |

### Domain 8 — API Payload Integrity
| Test ID | Scenario | Expected |
|---------|----------|----------|
| T-42 | summary() has all required fields | all keys present |
| T-43 | recommendations() has records list | each record has attribution_id, status, etc. |
| T-44 | sources() has scorecards list | each scorecard has follow_rate_pct etc. |
| T-45 | attribution_id unique per record | no duplicate attribution_ids |
| T-46 | recommendation_source never null | defaults to "OTHER" |

### Domain 9 — Edge Cases
| Test ID | Scenario | Expected |
|---------|----------|----------|
| T-47 | No lineage file | returns empty payload, no exception |
| T-48 | No change records file | returns empty payload, no exception |
| T-49 | No PAR runs directory | returns empty payload, no exception |
| T-50 | Recommendation date after observed date (negative days) | response_days = 0 (clamped) |
| T-51 | UNCHANGED change_type records excluded | not present in attribution records |

---

## 3. Isolation Requirements

- Tests use `tmp_path` (no writes to `data/`)
- Fixture helpers create minimal CSV/JSON files
- No HTTP calls, no server process
- Direct module function calls only

---

## 4. Regression Surface

PIS-008 modifies:
- `scripts/run_outcome_ui.py` — adds 3 new elif branches (no existing branches changed)
- `ui/pis_dashboard/app.js` — adds new subsystem + sections (no existing sections changed)
- `ui/pis_dashboard/index.html` — adds new HTML panels (no existing panels changed)

**Regression risk: LOW.** No existing analytical code is touched.

---

## 5. Validation Pass Criteria

| Criteria | Pass Condition |
|----------|---------------|
| All T-01 through T-51 pass | 0 failures |
| Full existing test suite | 0 regressions |
| `pis_action_attribution_summary()` live | No exceptions, valid JSON |
| `pis_action_attribution_sources()` live | ≥ 1 scorecard returned |
| `pis_action_attribution_recommendations()` live | ≥ 1 record returned |
| Dashboard sections load | No JS errors in new sections |
