# CPV Design — AI-001-OPTION-B

**Date:** 2026-06-15  
**Issue:** #40  
**Status:** Design complete; implementation follows

---

## Purpose

The Compliance Portfolio Validator (CPV) evaluates the *actual* portfolio allocation against mandate structural policy ceilings and floors. It produces formal three-tier signals (OK / ADVISORY / WARN / FAIL) per rule so operators have explicit, traceable governance state rather than a display-only bar chart.

CPV is **informational governance only**. It does not mutate targets, scores, recommendations, attribution, or benchmark math.

---

## Q1. What constitutes compliance?

A portfolio is compliant when every CPV rule evaluates to `OK` — meaning every measured actual allocation percentage satisfies the policy ceiling or floor constraint (within a 0.01pp floating-point tolerance).

---

## Q2. What constitutes a violation?

A violation occurs when the measured actual percentage exceeds a policy ceiling or falls below a policy floor. Violations are graded into three bands:

| Band | Condition | Operator Action |
|------|-----------|----------------|
| ADVISORY | Breach ≤ advisory_pp | None required; log |
| WARN | advisory_pp < breach ≤ warn_pp | Review recommended |
| FAIL | breach > warn_pp | Governance acknowledgment recommended |

---

## Q3. How are mandate exceptions handled?

The policy thresholds are read from `config/allocation_policy.yaml` under the new `compliance_tolerance` section. If a `compliance_tolerance` section is absent, hard-coded defaults are used. This allows mandate-specific tolerance overrides without code changes.

CPV does not modify recommendations or targets for any exception.

---

## Q4. How is intentional concentration represented?

CPV reports what the portfolio *is*, not what it *should be*. When a portfolio is intentionally equity-heavy (e.g., CONCENTRATED_ALPHA mandate), CPV-06 (single asset class max 80%) may show ADVISORY because 84% > 80% ceiling — this is expected. The mandate context is included in the rule message: "Equity-heavy portfolio consistent with CONCENTRATED_ALPHA mandate."

CPV does not suppress ADVISORY/WARN/FAIL signals for intentional concentration — operators need to see the actual state. The mandate field on the run informs operator judgment.

---

## Q5. How should compliance interact with governance warnings?

CPV runs after alignment computation. It reads alignment results and writes `portfolio_compliance` to the run result dict. It does not interact with the existing `reconciliation` checks (which evaluate the strategic *target* model, not actual holdings). These are complementary:
- Reconciliation: "Is the target model internally consistent?"
- CPV: "Is the actual portfolio consistent with policy?"

---

## 8 CPV Rules

| Rule | Check | Policy Value | Node(s) | Advisory | Warn |
|------|-------|-------------|---------|---------|------|
| CPV-01 | Combined Micro Cap max | 5.0% | EQUITIES.US.MICRO + EQUITIES.INTERNATIONAL.MICRO | +2pp | +4pp |
| CPV-02 | Mega Cap max | 50.0% | EQUITIES.US.MEGA | +5pp | +10pp |
| CPV-03 | Digital Assets max | 8.0% | DIGITAL | +1pp | +2pp |
| CPV-04 | Cash floor min | 2.0% | CASH | −1pp | −2pp |
| CPV-05 | International min | 10.0% | EQUITIES.INTERNATIONAL + EQUITIES.EMERGING_MARKETS | −2pp | −4pp |
| CPV-06 | Single asset class max | 80.0% | Max L1 node | +5pp | +10pp |
| CPV-07 | Equities min | 40.0% | EQUITIES | −5pp | −10pp |
| CPV-08 | Fixed Income max | 40.0% | FIXED_INCOME | +5pp | +10pp |

---

## Implementation Map

### New File: `src/portfolio/compliance_validator.py`

```
ComplianceTolerance (dataclass)
ComplianceRuleResult (dataclass)
PortfolioComplianceResult (dataclass)

load_compliance_tolerances(config_path)
evaluate_rule_ceiling(rule_id, name, actual_pct, ceiling_pct, tol, node_hint)
evaluate_rule_floor(rule_id, name, actual_pct, floor_pct, tol, node_hint)
validate_portfolio_compliance(alignment_rows, policy, tolerances) -> PortfolioComplianceResult
```

### Modified: `config/allocation_policy.yaml`

Add `compliance_tolerance` section with per-rule advisory_pp and warn_pp.

### Modified: `src/portfolio/runner.py`

Call `validate_portfolio_compliance(alignment, policy, tolerances)` after alignment is computed. Add `portfolio_compliance` key to run result dict and write `compliance.json` to PAR directory.

### Modified: `scripts/run_outcome_ui.py`

Add `GET /api/cpv/latest` endpoint that reads the latest PAR's `compliance.json`.

### Modified: `ui/allocation_intelligence/app.js`

Extend `renderPortfolioCompliance()` to read `portfolio_compliance` from the PAR API response and render severity badges (ADVISORY/WARN/FAIL) alongside existing compliance bars. Add governance banner if any rule is WARN or FAIL.

---

## Data Model

### ComplianceRuleResult

```python
rule_id: str                # "CPV-01"
name: str                   # "Combined Micro Cap"
rule_type: str              # "ceiling" | "floor"
policy_value_pct: float     # 5.0
actual_pct: float           # 8.33
breach_pp: float            # 3.33 (positive = breach magnitude)
status: str                 # "OK" | "ADVISORY" | "WARN" | "FAIL"
advisory_pp: float          # from tolerance config
warn_pp: float              # from tolerance config
node_keys: list[str]        # ["EQUITIES.US.MICRO", "EQUITIES.INTERNATIONAL.MICRO"]
node_hint: str              # "EQUITIES.US.MICRO only (INTL.MICRO=0.0)"
explanation: str            # human-readable
```

### PortfolioComplianceResult

```python
run_id: str
snapshot_date: str
overall_status: str          # "OK" | "ADVISORY" | "WARN" | "FAIL"
compliance_score: int        # 0–100 (display-only)
rule_results: list[ComplianceRuleResult]
violation_count: int
advisory_count: int
warn_count: int
fail_count: int
generated_at_utc: str
```

---

## API Contract

### GET /api/cpv/latest

**Response:**
```json
{
  "run_id": "PAR-20260614-3A8B91DB",
  "snapshot_date": "2026-06-14",
  "overall_status": "ADVISORY",
  "compliance_score": 75,
  "violation_count": 2,
  "advisory_count": 2,
  "warn_count": 0,
  "fail_count": 0,
  "generated_at_utc": "2026-06-14T20:33:00+00:00",
  "rules": [
    {
      "rule_id": "CPV-01",
      "name": "Combined Micro Cap",
      "rule_type": "ceiling",
      "policy_value_pct": 5.0,
      "actual_pct": 9.0,
      "breach_pp": 4.0,
      "status": "ADVISORY",
      "advisory_pp": 2.0,
      "warn_pp": 4.0,
      "node_keys": ["EQUITIES.US.MICRO", "EQUITIES.INTERNATIONAL.MICRO"],
      "node_hint": "EQUITIES.US.MICRO=9.0% EQUITIES.INTERNATIONAL.MICRO=0.0%",
      "explanation": "Micro Cap combined actual 9.00% exceeds 5.0% ceiling by 4.00pp. Within advisory tolerance (≤4.0pp). No action required."
    }
  ]
}
```

---

## Compliance Score Formula

```
score = 100 - (fail_count × 25) - (warn_count × 10) - (advisory_count × 5)
score = max(0, min(100, score))
```

Display-only. Does not affect any computation.

---

## Dashboard Integration

### Existing: `renderPortfolioCompliance()` in `allocation_intelligence/app.js`

Extend to also call `/api/cpv/latest` and:
1. Replace "OVER" badges with ADVISORY/WARN/FAIL with exceedance amount
2. Show a governance banner at top if any rule is WARN or FAIL
3. Add a rule evaluation table below the existing bars

### Historical Compliance Trend

Not feasible in current architecture — `compliance.json` is written per PAR but there is no separate history store for compliance results. CPV history would require a new CSV artifact analogous to `attribution_records.csv`. Deferred to future CPV phase. The current API returns the latest PAR compliance only.

---

## No Changes To

- Recommendation logic
- Attribution scoring
- Benchmark math
- Governance validators (reconciliation checks)
- Allocation target computation
- Lineage matching
- Signal scoring
