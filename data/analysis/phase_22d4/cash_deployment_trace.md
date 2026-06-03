# Phase 22D.4 — Q2: Cash Deployment Trace (Projected 2.0%)
## Why does the deployment planner project 2.0% cash after full deployment?

**Investigation run:** PAR-20260602-1BF2ADA5  
**Active mandate:** CONCENTRATED_ALPHA  
**Generated:** Phase 22D.4 — read-only forensic trace

---

## Answer

The `2.0%` projected post-deployment cash is the **tactical cash floor** — the minimum reserve that the deployment engine is hard-coded to never breach. After full deployment, every dollar above this floor has been allocated to conviction positions, leaving exactly `MIN_CASH_PCT = 2.0%` of portfolio value in cash.

---

## Evidence Chain (step-by-step)

### Step 1 — Tactical floor constant defined

**File:** `src/portfolio/deployment_queue.py`, line 43  
```python
MIN_CASH_PCT = 2.0   # mandate floor — reserve never deployed below this level
```

This constant defines the **absolute minimum cash reserve** the deployment engine will honor. It is independent of the allocation model target. The comment explicitly says "never deployed below this level."

---

### Step 2 — Deployable cash computed against this floor

**File:** `src/portfolio/deployment_queue.py`, function `compute_deployable_cash()`, lines 381–401  
```python
def compute_deployable_cash(holdings, total_market_value):
    cash_mv   = sum(h.market_value for h in holdings if h.is_cash_equivalent)
    cash_pct  = (cash_mv / total_market_value * 100.0) if total_market_value else 0.0
    floor_mv  = total_market_value * MIN_CASH_PCT / 100.0   # ← floor computed here
    deployable_mv  = max(0.0, cash_mv - floor_mv)           # ← floor enforced here
    deployable_pct = (deployable_mv / total_market_value * 100.0) if total_market_value else 0.0
    return {
        "cash_mv": round(cash_mv, 2),
        "cash_pct": round(cash_pct, 4),
        "floor_mv": round(floor_mv, 2),
        "deployable_mv": round(deployable_mv, 2),
        "deployable_pct": round(deployable_pct, 4),
    }
```

`deployable_mv` is defined as **cash above the floor**. The floor itself is never allocatable.

---

### Step 3 — Planner deploys all deployable cash

**File:** `src/portfolio/deployment_planner.py`  

The planner calls `compute_deployable_cash()` to get the deployable amount, then allocates the full amount across the conviction queue (Tier 1 → Tier 2 → Tier 3). After distributing all `deployable_mv`:

```
total_deployed ≈ deployable_mv
```

---

### Step 4 — Portfolio impact computation

**File:** `src/portfolio/deployment_planner.py`, lines 329–330  
```python
cash_mv_after  = cash_mv_before - total_deployed
cash_pct_after = (cash_mv_after / total_mv * 100.0) if total_mv > 0 else 0.0
```

Substituting the full deployment case:  
```
cash_mv_after  = cash_mv_before − deployable_mv
               = cash_mv_before − (cash_mv_before − floor_mv)
               = floor_mv
               = total_mv × 2.0% / 100
```

Therefore:  
```
cash_pct_after = floor_mv / total_mv × 100 = 2.0%   ← exactly
```

This is mathematically guaranteed when all deployable cash is allocated.

---

### Step 5 — Test suite confirms this is expected behavior

**File:** `tests/test_7_5f_deployment_actionability.py`, line 129–133  
```python
def test_cash_after_pct_at_minimum_reserve(self):
    # Cash must be at minimum reserve (2.0%) after deployment
    assert abs(self.pi["cash_after_pct"] - 2.0) < 0.1, (
        f"cash_after_pct {self.pi['cash_after_pct']:.2f}% expected ~2.0%"
    )
```

The test **explicitly expects** `cash_after_pct ≈ 2.0%` and calls this the "minimum reserve." This is not a bug caught by a test — it is the designed behavior the test validates.

---

### Step 6 — Allocation policy aligns

**File:** `config/allocation_policy.yaml`  
```yaml
structural_policy:
  cash_floor_pct: 2.0

asset_class_governance:
  CASH:
    min_pct: 2.0
    max_pct: 20.0
    notes: "Global liquidity reserve. Structural floor enforced."
```

Both the structural policy floor (`cash_floor_pct: 2.0`) and the CASH asset class governance min (`min_pct: 2.0`) confirm that `2.0%` is the **policy-level minimum**. The deployment engine's `MIN_CASH_PCT = 2.0` is a code-level expression of this same policy constraint.

---

## Summary

| Step | Location | Role |
|------|----------|------|
| 1 | `deployment_queue.py:43` `MIN_CASH_PCT = 2.0` | Defines the tactical floor constant |
| 2 | `deployment_queue.py` `compute_deployable_cash()` | Computes floor_mv and deployable_mv |
| 3 | `deployment_planner.py` CW-DAS allocation loop | Allocates all deployable_mv to conviction queue |
| 4 | `deployment_planner.py:329-330` | cash_after = cash_before − deployed = floor_mv → 2.0% |
| 5 | `test_7_5f_deployment_actionability.py:129` | Test confirms 2.0% is the designed outcome |
| 6 | `allocation_policy.yaml` structural_policy + CASH min_pct | Policy basis for the 2.0% minimum |

The 2.0% after-deployment cash is not a coincidence or an error — it is the **designed terminus of a full deployment cycle**: all cash above the structural floor is deployed, leaving the portfolio at precisely the `MIN_CASH_PCT` reserve.
