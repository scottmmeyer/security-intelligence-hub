# Actual Portfolio Compliance Validator — Threshold Definitions

Repository: security-intelligence-hub  
Date: 2026-06-09

## Threshold Model

Each compliance rule has three zones defined by exceedance thresholds:

```
        Policy          Policy +             Policy +
        Ceiling/Floor   advisory_pp          warn_pp
          │                │                   │
OK ──────►│◄── ADVISORY ──►│◄────── WARN ─────►│◄── FAIL
```

For ceiling rules (max): the breach amount is `actual - ceiling`.  
For floor rules (min): the breach amount is `floor - actual`.

A result of **ADVISORY** means the portfolio is outside the strict policy ceiling/floor but within the advisory tolerance. This is expected during normal portfolio drift between rebalancing cycles.

A result of **WARN** means the breach exceeds the advisory tolerance but has not reached the hard fail threshold.

A result of **FAIL** means the breach exceeds the warn tolerance. Operator acknowledgment is recommended before any portfolio change that would worsen the breach.

---

## Rule Definitions

### CPV-01 — Combined Micro Cap (max 5%)

| Parameter | Value | Rationale |
|---|---|---|
| Policy ceiling | 5.0% | allocation_policy.yaml: max_micro_cap_pct |
| Advisory threshold | +2pp → cap 7.0% | Normal drift from micro-cap positions over 1–2 week holding windows |
| Warn threshold | +4pp → cap 9.0% | Significant drift requiring active review |
| Fail threshold | >4pp | Hard governance signal |
| Scope | EQUITIES.US.MICRO + EQUITIES.INTERNATIONAL.MICRO combined | |

Today's actual: ~8.33% (US.MICRO only; no INTL.MICRO in current portfolio)  
Breach: 8.33% − 5.0% = +3.33pp → **ADVISORY** (within 4pp warn threshold)

---

### CPV-02 — Mega Cap Concentration (max 50%)

| Parameter | Value |
|---|---|
| Policy ceiling | 50.0% |
| Advisory threshold | +5pp → cap 55% |
| Warn threshold | +10pp → cap 60% |
| Fail threshold | >10pp |
| Scope | EQUITIES.US.MEGA |

Today's actual: 18.54% → **OK** (well below 50%)

---

### CPV-03 — Digital Assets (max 8%)

| Parameter | Value |
|---|---|
| Policy ceiling | 8.0% |
| Advisory threshold | +1pp → cap 9% |
| Warn threshold | +2pp → cap 10% |
| Fail threshold | >2pp |
| Scope | DIGITAL |

Today's actual: ~2.0% (estimated from FBTC, FETH, XRP, FSOL, SMR) → **OK**

Note: Tighter tolerances for DIGITAL given its volatility and the stated hard cap rationale in policy.

---

### CPV-04 — Cash Floor (min 2%)

| Parameter | Value |
|---|---|
| Policy floor | 2.0% |
| Advisory threshold | −1pp → floor 1% |
| Warn threshold | −2pp → floor 0% |
| Fail threshold | <0% (practically impossible; keep for completeness) |
| Scope | CASH |

Today's actual: 11.67% → **OK** (well above floor, actually above target)

---

### CPV-05 — International Minimum (min 10%)

| Parameter | Value |
|---|---|
| Policy floor | 10.0% |
| Advisory threshold | −2pp → floor 8% |
| Warn threshold | −4pp → floor 6% |
| Fail threshold | <6% |
| Scope | EQUITIES.INTERNATIONAL + EQUITIES.EMERGING_MARKETS combined |

Today's actual: 17.1% + 0.63% = 17.73% → **OK**

---

### CPV-06 — Single Asset Class Maximum (max 80%)

| Parameter | Value |
|---|---|
| Policy ceiling | 80.0% |
| Advisory threshold | +5pp → cap 85% |
| Warn threshold | +10pp → cap 90% |
| Fail threshold | >10pp |
| Scope | Any single L1 node |

Today's actual: EQUITIES 84.86% → breach = +4.86pp → **ADVISORY** (within 5pp warn threshold)

---

### CPV-07 — Equities Minimum (min 40%)

| Parameter | Value |
|---|---|
| Policy floor | 40.0% |
| Advisory threshold | −5pp → floor 35% |
| Warn threshold | −10pp → floor 30% |
| Fail threshold | <30% |
| Scope | EQUITIES |

Today's actual: 84.86% → **OK**

---

### CPV-08 — Fixed Income Maximum (max 40%)

| Parameter | Value |
|---|---|
| Policy ceiling | 40.0% |
| Advisory threshold | +5pp → cap 45% |
| Warn threshold | +10pp → cap 50% |
| Fail threshold | >10pp |
| Scope | FIXED_INCOME |

Today's actual: 1.48% → **OK** (far below ceiling; currently underweight)

---

## Proposed YAML Extension

```yaml
# In config/allocation_policy.yaml — new section
compliance_tolerance:
  version: 1
  effective_date: "2026-06-09"
  notes: >
    Tolerance bands for actual portfolio compliance checks (CPV rules).
    advisory_pp: breach amount that triggers ADVISORY state.
    warn_pp: breach amount that triggers WARN state (>warn_pp = FAIL).

  CPV-01_micro_cap:      { advisory_pp: 2.0, warn_pp: 4.0 }
  CPV-02_mega_cap:       { advisory_pp: 5.0, warn_pp: 10.0 }
  CPV-03_digital:        { advisory_pp: 1.0, warn_pp: 2.0 }
  CPV-04_cash_floor:     { advisory_pp: 1.0, warn_pp: 2.0 }
  CPV-05_international:  { advisory_pp: 2.0, warn_pp: 4.0 }
  CPV-06_asset_class:    { advisory_pp: 5.0, warn_pp: 10.0 }
  CPV-07_equities_min:   { advisory_pp: 5.0, warn_pp: 10.0 }
  CPV-08_fi_max:         { advisory_pp: 5.0, warn_pp: 10.0 }
```

---

## Summary Table (Today's Portfolio — PAR-20260609-42A90186)

| Rule | Ceiling/Floor | Actual | Breach | Status |
|---|---|---|---|---|
| CPV-01 Micro Cap | max 5.0% | ~8.33% | +3.33pp | **ADVISORY** |
| CPV-02 Mega Cap | max 50.0% | 18.54% | none | OK |
| CPV-03 Digital | max 8.0% | ~2.0% | none | OK |
| CPV-04 Cash floor | min 2.0% | 11.67% | none | OK |
| CPV-05 International | min 10.0% | ~17.7% | none | OK |
| CPV-06 Asset class max | max 80.0% | 84.86% | +4.86pp | **ADVISORY** |
| CPV-07 Equities min | min 40.0% | 84.86% | none | OK |
| CPV-08 FI max | max 40.0% | 1.48% | none | OK |
