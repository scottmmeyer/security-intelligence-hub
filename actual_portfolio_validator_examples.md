# Actual Portfolio Compliance Validator — Examples

Repository: security-intelligence-hub  
Date: 2026-06-09  
Reference PAR: PAR-20260609-42A90186

All examples use actual portfolio values from the latest run. Values are real, not hypothetical.

---

## Example 1: CPV-01 Micro Cap — ADVISORY

**Situation:** Portfolio holds 8.33% in EQUITIES.US.MICRO. Policy ceiling is 5%.

```
Policy ceiling:  5.0%
Actual:          8.33%
Breach:          +3.33pp
Advisory band:   ≤ 2pp (5% + 2pp = 7%)
Warn band:       > 2pp and ≤ 4pp (7%–9%)
Fail band:       > 4pp (> 9%)

Result: ADVISORY
  Breach (3.33pp) exceeds advisory threshold (2pp)
  Breach (3.33pp) does not exceed warn threshold (4pp)
```

**Validator output:**
```json
{
  "rule_id": "CPV-01",
  "name": "Combined Micro Cap",
  "ceiling_pct": 5.0,
  "actual_pct": 8.33,
  "breach_pp": 3.33,
  "status": "ADVISORY",
  "message": "Micro Cap actual 8.33% exceeds 5.0% ceiling by 3.33pp. Within advisory tolerance (2pp–4pp). No action required; note for next rebalancing review."
}
```

**UI display:** Yellow "ADVISORY +3.33pp" badge in Current Portfolio Compliance bars.

---

## Example 2: CPV-06 Single Asset Class — ADVISORY

**Situation:** EQUITIES is 84.86% of portfolio. Policy ceiling for single asset class is 80%.

```
Policy ceiling:  80.0%
Actual:          84.86%
Breach:          +4.86pp
Advisory band:   ≤ 5pp (85%)
Warn band:       > 5pp and ≤ 10pp (85%–90%)

Result: ADVISORY
  Breach (4.86pp) is within advisory threshold (5pp)
```

**Validator output:**
```json
{
  "rule_id": "CPV-06",
  "name": "Single Asset Class Maximum",
  "node": "EQUITIES",
  "ceiling_pct": 80.0,
  "actual_pct": 84.86,
  "breach_pp": 4.86,
  "status": "ADVISORY",
  "message": "EQUITIES actual 84.86% exceeds 80.0% ceiling by 4.86pp. Within advisory tolerance (≤5pp). Equity-heavy portfolio consistent with CONCENTRATED_ALPHA mandate."
}
```

---

## Example 3: CPV-01 Micro Cap — WARN (hypothetical, +5pp breach)

**Situation:** Portfolio shifts to 10% micro-cap exposure.

```
Policy ceiling:  5.0%
Actual:          10.0%
Breach:          +5.0pp
Advisory band:   2pp–4pp
Warn band:       > 4pp (satisfied)
Fail band:       > 4pp (NOT satisfied — same threshold)

Result: WARN
  Breach (5.0pp) exceeds warn threshold (4pp)
```

**Validator output:**
```json
{
  "rule_id": "CPV-01",
  "name": "Combined Micro Cap",
  "ceiling_pct": 5.0,
  "actual_pct": 10.0,
  "breach_pp": 5.0,
  "status": "WARN",
  "message": "Micro Cap actual 10.0% exceeds 5.0% ceiling by 5.0pp. WARN threshold (4pp) exceeded. Operator rebalancing review recommended."
}
```

**UI display:** Orange "WARN +5.0pp" badge. Governance banner appears at page top.

---

## Example 4: CPV-03 Digital Assets — FAIL (hypothetical, +3pp breach)

**Situation:** Digital assets have appreciated to 11% of portfolio.

```
Policy ceiling:  8.0%
Actual:          11.0%
Breach:          +3.0pp
Advisory band:   1pp (9%)
Warn band:       > 1pp and ≤ 2pp (9%–10%)
Fail band:       > 2pp (> 10%)

Result: FAIL
  Breach (3.0pp) exceeds fail threshold (2pp)
  Note: DIGITAL has the tightest tolerances due to its volatility and hard-cap governance design
```

**Validator output:**
```json
{
  "rule_id": "CPV-03",
  "name": "Digital Assets Maximum",
  "ceiling_pct": 8.0,
  "actual_pct": 11.0,
  "breach_pp": 3.0,
  "status": "FAIL",
  "message": "Digital Assets actual 11.0% exceeds 8.0% ceiling by 3.0pp. FAIL threshold (2pp) exceeded. Hard governance cap. Operator acknowledgment required before portfolio changes that worsen this breach."
}
```

**UI display:** Red "FAIL +3.0pp" badge. Prominent governance banner.

---

## Example 5: CPV-04 Cash Floor — OK (today's actual)

**Situation:** Cash is 11.67% (well above 2% floor).

```
Policy floor:    2.0%
Actual:          11.67%
Shortfall:       none (11.67 > 2.0)

Result: OK
```

**Note:** Cash is currently elevated above both floor and target (7%). This would be flagged as a drift opportunity by the recommendation system, but is not a compliance violation.

---

## Example 6: All Rules — Complete Run Summary (Today)

| Rule | Status | Breach | Message |
|---|---|---|---|
| CPV-01 Micro Cap | ADVISORY | +3.33pp | Within advisory tolerance |
| CPV-02 Mega Cap | OK | none | — |
| CPV-03 Digital | OK | none | — |
| CPV-04 Cash Floor | OK | none | — |
| CPV-05 International | OK | none | — |
| CPV-06 Asset Class Max | ADVISORY | +4.86pp | Within advisory tolerance |
| CPV-07 Equities Min | OK | none | — |
| CPV-08 FI Max | OK | none | — |

**Page-level summary:** 2 ADVISORY, 0 WARN, 0 FAIL — No governance banner shown (ADVISORY only does not trigger banner).
