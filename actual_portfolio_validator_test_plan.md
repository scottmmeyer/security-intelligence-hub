# Actual Portfolio Compliance Validator — Test Plan

Repository: security-intelligence-hub  
Date: 2026-06-09

## Test Coverage Requirements

All tests must be written in Python (pytest). No code changes until implementation; this is the test plan only.

---

## Test Module: `tests/test_portfolio_compliance_validator.py`

### Group 1: validate_portfolio_compliance() — basic rule evaluation

**T01 — CPV-01 OK: micro cap within ceiling**
- Input: micro_cap_actual = 4.0, ceiling = 5.0
- Expected: status = OK

**T02 — CPV-01 ADVISORY: micro cap in advisory band**
- Input: micro_cap_actual = 7.0, ceiling = 5.0, advisory_pp = 2.0
- Expected: status = ADVISORY, breach_pp = 2.0

**T03 — CPV-01 WARN: micro cap in warn band**
- Input: micro_cap_actual = 8.5, ceiling = 5.0, advisory_pp = 2.0, warn_pp = 4.0
- Expected: status = WARN, breach_pp = 3.5

**T04 — CPV-01 FAIL: micro cap beyond warn threshold**
- Input: micro_cap_actual = 10.0, ceiling = 5.0, advisory_pp = 2.0, warn_pp = 4.0
- Expected: status = FAIL, breach_pp = 5.0

**T05 — CPV-04 Cash Floor — OK**
- Input: cash_actual = 5.0, floor = 2.0
- Expected: status = OK (actual > floor)

**T06 — CPV-04 Cash Floor — ADVISORY (below floor)**
- Input: cash_actual = 1.5, floor = 2.0, advisory_pp = 1.0
- Expected: status = ADVISORY, shortfall_pp = 0.5

**T07 — CPV-04 Cash Floor — FAIL (severely below floor)**
- Input: cash_actual = 0.0, floor = 2.0, advisory_pp = 1.0, warn_pp = 2.0
- Expected: status = FAIL, shortfall_pp = 2.0

**T08 — CPV-06 at ceiling boundary — exactly at ceiling**
- Input: equities_actual = 80.0, ceiling = 80.0
- Expected: status = OK (no breach, boundary inclusive)

**T09 — CPV-06 ADVISORY just above ceiling**
- Input: equities_actual = 80.01, ceiling = 80.0, advisory_pp = 5.0
- Expected: status = ADVISORY

**T10 — CPV-05 International — combined node sum**
- Input: EQUITIES.INTERNATIONAL = 8.0, EQUITIES.EMERGING_MARKETS = 3.0, floor = 10.0
- Expected: combined = 11.0, status = OK

**T11 — CPV-05 International — below floor**
- Input: EQUITIES.INTERNATIONAL = 5.0, EQUITIES.EMERGING_MARKETS = 0.5, floor = 10.0, advisory_pp = 2.0
- Expected: combined = 5.5, shortfall = 4.5, status = FAIL

**T12 — CPV-02 Mega Cap — far below ceiling (OK)**
- Input: mega_actual = 18.54, ceiling = 50.0
- Expected: status = OK

---

### Group 2: Threshold configuration

**T13 — Default thresholds are applied when none configured**
- Input: no compliance_tolerance in policy
- Expected: function uses hard-coded defaults without error

**T14 — YAML-configured thresholds override defaults**
- Input: compliance_tolerance.CPV-01_micro_cap.advisory_pp = 3.0
- Expected: ADVISORY only when breach > 3pp (not 2pp)

**T15 — Invalid threshold config (advisory > warn) raises ValueError**
- Input: advisory_pp = 5.0, warn_pp = 3.0 (advisory > warn)
- Expected: ValidationError or ValueError

---

### Group 3: Full run integration

**T16 — run_all_portfolio_compliance_checks() returns list of results**
- Input: alignment_results with 8 CPV-relevant nodes
- Expected: list with one result per CPV rule, all status fields populated

**T17 — Results are PASS when all actual values within policy**
- Input: perfect portfolio (all within ceilings/floors)
- Expected: all statuses = OK

**T18 — Results do not mutate alignment_results**
- Input: any alignment_results
- Expected: identical alignment_results object after validator runs

**T19 — Missing node in alignment (e.g., no DIGITAL in portfolio)**
- Input: alignment_results with no DIGITAL node
- Expected: CPV-03 result has status = OK (actual = 0%, within 8% ceiling)

**T20 — Empty alignment_results**
- Input: []
- Expected: all CPV results = OK (0% actuals are within all ceilings)

---

### Group 4: Today's actual portfolio (PAR-20260609-42A90186)

**T21 — CPV-01 Micro Cap today = ADVISORY**
- Input: EQUITIES.US.MICRO = 8.33%, EQUITIES.INTERNATIONAL.MICRO = 0%
- Expected: status = ADVISORY, breach_pp ≈ 3.33

**T22 — CPV-06 Asset Class today = ADVISORY**
- Input: EQUITIES = 84.86%
- Expected: status = ADVISORY, breach_pp ≈ 4.86

**T23 — CPV-02 Mega Cap today = OK**
- Input: EQUITIES.US.MEGA = 18.54%
- Expected: status = OK

**T24 — No WARN or FAIL in today's portfolio**
- Input: full alignment from PAR-20260609-42A90186
- Expected: no result has status WARN or FAIL

---

### Group 5: Serialisation

**T25 — Each result serialises to dict with required fields**
- Required fields: rule_id, name, ceiling_pct (or floor_pct), actual_pct, breach_pp, status, message
- Expected: all fields present and correctly typed

**T26 — Badge state summary computed correctly**
- Input: results with 2 ADVISORY, 1 WARN
- Expected: summary = {"ok": 5, "advisory": 2, "warn": 1, "fail": 0, "overall": "WARN"}

---

## Estimated Test Count

26 planned tests (minimum). Actual count may increase during implementation as edge cases emerge.

## Test File Location

`tests/test_portfolio_compliance_validator.py`

## Test Execution

```
python -m pytest tests/test_portfolio_compliance_validator.py -v
```

Must achieve: 100% pass, 0 failures, no scoring/ranking changes confirmed by running full suite after implementation.
