# CPV Validation Plan

**Date:** 2026-06-15

---

## Test File: `tests/test_portfolio_compliance_validator.py`

### Group 1: Rule Evaluation — Ceiling Rules

**T01 — CPV-01 OK (micro cap within ceiling)**
- actual = 4.0%, ceiling = 5.0%
- Expected: status=OK, breach_pp=0.0

**T02 — CPV-01 ADVISORY (micro cap in advisory band)**
- actual = 7.0%, ceiling = 5.0%, advisory=2.0, warn=4.0
- breach = 2.0pp; advisory threshold = 2.0pp
- Expected: status=ADVISORY, breach_pp=2.0

**T03 — CPV-01 WARN (micro cap in warn band)**
- actual = 8.5%, ceiling = 5.0%, advisory=2.0, warn=4.0
- breach = 3.5pp; > advisory (2pp), ≤ warn (4pp)
- Expected: status=WARN, breach_pp=3.5

**T04 — CPV-01 FAIL (micro cap beyond warn threshold)**
- actual = 10.0%, ceiling = 5.0%, advisory=2.0, warn=4.0
- breach = 5.0pp; > warn (4pp)
- Expected: status=FAIL, breach_pp=5.0

**T05 — Boundary: exactly at ceiling**
- actual = 5.0%, ceiling = 5.0%
- Expected: status=OK (no breach; boundary inclusive)

**T06 — Boundary: 0.001pp above ceiling (float tolerance)**
- actual = 5.001%, ceiling = 5.0%
- Expected: status=ADVISORY (above ceiling by 0.001pp > 0, within advisory)

### Group 2: Rule Evaluation — Floor Rules

**T07 — CPV-04 OK (cash above floor)**
- actual = 5.0%, floor = 2.0%
- Expected: status=OK

**T08 — CPV-04 ADVISORY (cash slightly below floor)**
- actual = 1.5%, floor = 2.0%, advisory=1.0
- shortfall = 0.5pp; ≤ advisory (1pp)
- Expected: status=ADVISORY, breach_pp=0.5

**T09 — CPV-04 WARN (cash moderately below floor)**
- actual = 0.5%, floor = 2.0%, advisory=1.0, warn=2.0
- shortfall = 1.5pp; > advisory (1pp), ≤ warn (2pp)
- Expected: status=WARN, breach_pp=1.5

**T10 — CPV-04 FAIL (cash severely below floor)**
- actual = 0.0%, floor = 2.0%, advisory=1.0, warn=2.0
- shortfall = 2.0pp; exactly at warn threshold
- Expected: status=FAIL, breach_pp=2.0

**T11 — Boundary: exactly at floor**
- actual = 2.0%, floor = 2.0%
- Expected: status=OK

### Group 3: Combined Node Rules

**T12 — CPV-01 combined (US micro + INTL micro)**
- US.MICRO=6.0, INTL.MICRO=2.0, combined=8.0, ceiling=5.0
- Expected: combined=8.0, breach=3.0, status=ADVISORY

**T13 — CPV-05 international combined**
- EQUITIES.INTERNATIONAL=8.0, EQUITIES.EMERGING_MARKETS=3.0, floor=10.0
- combined=11.0, no shortfall
- Expected: status=OK

**T14 — CPV-05 international combined below floor**
- EQUITIES.INTERNATIONAL=5.0, EQUITIES.EMERGING_MARKETS=0.5, floor=10.0, advisory=2.0, warn=4.0
- combined=5.5, shortfall=4.5pp; > warn (4pp)
- Expected: status=FAIL

**T15 — CPV-06 single asset class max (finds max L1 node)**
- alignment has EQUITIES=84%, FIXED_INCOME=10%, DIGITAL=5%, CASH=1%
- Max L1 = EQUITIES at 84%; ceiling=80%, advisory=5%, warn=10%
- breach = 4pp; ≤ advisory (5pp)
- Expected: status=ADVISORY, node="EQUITIES"

### Group 4: Full Validate Function

**T16 — validate_portfolio_compliance returns correct overall_status**
- All rules OK → overall_status=OK
- One ADVISORY → overall_status=ADVISORY
- Mix ADVISORY+WARN → overall_status=WARN
- Any FAIL → overall_status=FAIL

**T17 — compliance_score calculation**
- 0 violations → score=100
- 2 ADVISORY → score=90
- 1 WARN → score=90
- 1 FAIL → score=75

**T18 — validate with empty alignment rows returns graceful result**
- Input: []
- Expected: all rules show actual_pct=0, status reflects defaults

### Group 5: Tolerance Configuration

**T19 — default tolerances applied when no compliance_tolerance in YAML**
- Input: policy without compliance_tolerance section
- Expected: CPV-01 uses advisory_pp=2.0, warn_pp=4.0 (defaults)

**T20 — YAML-configured tolerances override defaults**
- Input: compliance_tolerance.CPV-01_micro_cap.advisory_pp=3.0
- With actual=7.0, ceiling=5.0 → breach=2.0pp; < new advisory (3pp)
- Expected: status=OK (not ADVISORY)

**T21 — Invalid tolerance config raises ValueError**
- Input: advisory_pp=5.0, warn_pp=3.0 (advisory > warn)
- Expected: ValueError raised

### Group 6: Live Portfolio Test

**T22 — Live alignment data produces expected CPV results**
- Load actual PAR alignment from PAR-20260614-3A8B91DB or latest
- Run validate_portfolio_compliance()
- CPV-01 should be ADVISORY (~9% micro cap vs 5% ceiling)
- CPV-06 should be ADVISORY (~87% EQUITIES vs 80% ceiling)
- All others should be OK
- Expected: overall_status=ADVISORY

---

## Edge Cases

| Scenario | Expected Behavior |
|----------|-----------------|
| Missing alignment node (node not in alignment) | Treat as 0%; log missing node in node_hint |
| Negative actual_pct | Treat as 0% (normalization artifact) |
| Portfolio with zero total value | All rules OK (no breach of any ceiling) |
| Policy with digital max=0% | CPV-03 FAIL if any DIGITAL holding exists |
| CONCENTRATED_ALPHA mandate | CPV-06 shows ADVISORY for equity concentration; this is expected |
| Weekend portfolio (Jun 14 = Sunday) | CPV evaluates normally; date is informational only |
