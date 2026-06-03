# Deployment Recalculation Validation — Phase 22D.6A
**Audit Date:** 2026-06-02  
**Run Audited:** PAR-20260602-A991571C  
**Mandate Profile:** CONCENTRATED_ALPHA

---

## 1. Portfolio Inputs (from latest run artifact)

| Parameter | Value | Source |
|---|---|---|
| Total Portfolio MV | $479,347.59 | `deployment_queue.json → total_market_value` |
| SPAXX Cash MV | $41,279.15 | `deployment_queue.json → cash_context.cash_mv` |
| Current Cash Weight | 8.6115% | `cash_mv / total_mv × 100` |
| Mandate Cash Target | 7.0% | `concentrated_alpha_profile.yaml → nodes.CASH` |
| Governance Min Floor | 2.0% | `MIN_CASH_PCT` constant in `deployment_queue.py` |

---

## 2. Correct Deployable Cash Calculation

### Step 1: Determine operative floor

```
effective_floor_pct = max(MIN_CASH_PCT, mandate_cash_target_pct)
                    = max(2.0, 7.0)
                    = 7.0%
```

The mandate target (7.0%) exceeds the governance minimum (2.0%), so the **mandate target is the operative floor**.

### Step 2: Compute floor in dollars

```
floor_mv = total_mv × effective_floor_pct / 100
         = $479,347.59 × 7.0 / 100
         = $33,554.33
```

### Step 3: Compute mandate target in dollars

```
target_mv = total_mv × mandate_cash_target_pct / 100
          = $479,347.59 × 7.0 / 100
          = $33,554.33
```

(When mandate_target = effective_floor, target_mv = floor_mv.)

### Step 4: Compute excess above mandate

```
excess_mv  = cash_mv - target_mv
           = $41,279.15 - $33,554.33
           = $7,724.82

excess_pct = excess_mv / total_mv × 100
           = $7,724.82 / $479,347.59 × 100
           = 1.6115%
```

### Step 5: Compute deployable cash

```
deployable_mv = max(0, cash_mv - floor_mv)
              = max(0, $41,279.15 - $33,554.33)
              = $7,724.82

deployable_pct = deployable_mv / total_mv × 100
               = $7,724.82 / $479,347.59 × 100
               = 1.6115%
```

---

## 3. Expected Portfolio Impact After Deployment

Assuming full deployment of $7,724.82 into equities:

```
cash_after_mv  = cash_mv - deployable_mv
               = $41,279.15 - $7,724.82
               = $33,554.33

cash_after_pct = cash_after_mv / total_mv × 100
               = $33,554.33 / $479,347.59 × 100
               = 7.0000%
```

**Post-deployment cash weight equals mandate target exactly.** This is the correct behavior.

---

## 4. Comparison: Actual vs Expected

| Metric | Stale Artifact (2% floor) | Expected (7% mandate floor) | Difference |
|---|---|---|---|
| Operative floor | 2.0% | 7.0% | +5.0 pp |
| `floor_mv` | $9,586.95 | $33,554.33 | +$23,967.38 |
| `deployable_mv` | $31,692.20 | **$7,724.82** | **-$23,967.38** |
| `deployable_pct` | 6.6115% | 1.6115% | -5.0 pp |
| `excess_mv` | MISSING | $7,724.82 | — |
| `excess_pct` | MISSING | 1.6115% | — |
| `cash_after_pct` | 2.0% | **7.0%** | **+5.0 pp** |
| `cash_after_mv` | $9,586.97 | $33,554.33 | +$23,967.36 |
| `total_deployed` | $31,692.18 | $7,724.82 | -$23,967.36 |

---

## 5. Cash Overshoot Risk (Current Behavior)

If a user were to execute the stale plan's full $31,692.20 deployment:

- Portfolio would hold only **$9,586.95 cash (2.0%)** 
- Mandate requires **$33,554.33 cash (7.0%)**
- **Mandate violation: cash would be 5.0 percentage points below mandate target**
- **Dollar shortfall vs mandate: -$23,967.38**

This is the operational consequence of serving the stale pre-22D.6 artifact.

---

## 6. Confirmation Against User-Reported Symptoms

| Symptom Reported | Expected From Calculation | Match |
|---|---|---|
| "Deployable Cash = $31.7K" | $31,692.20 (2% floor artifact) | ✅ Explained |
| "Cash Wt After = 2.0%" | 2.0% (2% floor depletes fully) | ✅ Explained |
| "Expected ~$7.9K deployable" | $7,724.82 (7% mandate floor) | ✅ Confirmed ($7.7K ≈ $7.9K, within rounding of SPAXX balance estimate) |
| "Current cash = 8.6%" | 8.6115% | ✅ Confirmed |

---

## 7. Remediation Math

To correct without re-running: the `deployment_queue.json` artifact would need its `cash_context` updated to:

```json
{
  "cash_mv": 41279.15,
  "cash_pct": 8.6115,
  "mandate_cash_target_pct": 7.0,
  "effective_floor_pct": 7.0,
  "floor_mv": 33554.33,
  "excess_mv": 7724.82,
  "excess_pct": 1.6115,
  "deployable_mv": 7724.82,
  "deployable_pct": 1.6115
}
```

And `deployment_plan.json` would need to be regenerated using `deployable_cash=7724.82`.

**Recommended remediation: fresh portfolio re-run** — generates both artifacts correctly from live data via current mandate-aware code. No manual patching required or advised.
