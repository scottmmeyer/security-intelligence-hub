# Q1 — Cash Governance Inventory
## Phase 22D.5 — Strategic Cash Governance & DCA Deployment Policy

**Investigation run:** PAR-20260602-1BF2ADA5  
**Generated:** Phase 22D.5  
**Scope:** Every location where cash targets, floors, deployable cash, reserve budgets, and deployment thresholds are defined or referenced  

---

## Section 1 — YAML Mandate Definitions

### 1a — Strategic Allocation Target: `CONCENTRATED_ALPHA`

**File:** `config/allocation_models/concentrated_alpha_profile.yaml`, line 18:
```yaml
nodes:
  CASH: 7.0    # Strategic allocation target for cash as % of total portfolio
```
**What it means:** The intended steady-state cash weight. Under a fully-deployed Concentrated Alpha portfolio, 7.0% should be held as cash.

**Philosophy statement** (same file, lines 5–9):
```yaml
philosophy: >
  Cash treated as dry powder, not idle drag. Fixed income optional; currently
  minimal. Mega cap targets reduced to reflect conviction in undervalued tiers.
```

**Other mandate profiles for comparison:**
| Mandate | CASH node target |
|---------|-----------------|
| CONCENTRATED_ALPHA | 7.0% |
| BALANCED_ALLOCATION | 5.0% |
| GROWTH_ALLOCATION | 3.0% |

CONCENTRATED_ALPHA holds the highest cash target of all mandates — intentionally.

---

### 1b — Governance Floor: `allocation_policy.yaml`

**File:** `config/allocation_policy.yaml`, lines 5–6:
```yaml
structural_policy:
  cash_floor_pct: 2.0
```

**CASH asset class governance band** (lines 48–53):
```yaml
CASH:
  max_pct: 20.0
  min_pct: 2.0
  replay_sophistication: NONE
  tactical_overlays_supported: false
  notes: >
    Global liquidity reserve. Structural floor enforced.
    Not geography-partitioned. No replay or overlay support.
```

**What this means:** Cash must be between 2.0% and 20.0% of portfolio at all times. The structural floor (2.0%) is the governance-enforced minimum — the allocation model target (7.0%) sits within this band.

---

## Section 2 — Deployment Planner Constants

### 2a — Deployment Queue: `deployment_queue.py`

**File:** `src/portfolio/deployment_queue.py`, lines 39–42:
```python
WARN_POSITION_PCT = 6.0   # soft-warn threshold
MAX_POSITION_PCT  = 8.0   # concentration ceiling
MIN_CASH_PCT      = 2.0   # mandate floor — reserve never deployed below this level
```

**Deployable cash formula** (implied by `compute_deployable_cash()`):
```
deployable_mv = max(0, cash_mv - (total_mv × MIN_CASH_PCT / 100))
```

**Important:** `MIN_CASH_PCT = 2.0` is a **constant hardcoded in the deployment engine** — it is not loaded from `allocation_policy.yaml`. The 2.0% value matches the policy YAML but is maintained independently.

**Impact:** The deployment engine will attempt to deploy all cash above 2.0% of portfolio, regardless of the strategic allocation model target of 7.0%.

### 2b — Live values (PAR-20260602-1BF2ADA5):
```
total_mv:      $475,779.42
cash_mv:       $41,198.92   (8.6592%)
floor_mv:      $9,515.59    (2.0000%)
deployable_mv: $31,683.33   (6.6592%)
```
The planner classifies 77% of the current cash position as deployable.

---

## Section 3 — `compute_deployable_cash()` Function

**File:** `src/portfolio/deployment_queue.py` (end of file):
```python
def compute_deployable_cash(
    holdings: list[PortfolioHolding],
    total_market_value: float,
) -> dict:
    """Compute deployable cash above the MIN_CASH_PCT mandate floor."""
    cash_mv   = sum(h.market_value for h in holdings if h.is_cash_equivalent)
    floor_mv  = total_market_value * MIN_CASH_PCT / 100.0
    dep_mv    = max(0.0, cash_mv - floor_mv)
    dep_pct   = dep_mv / total_market_value * 100.0 if total_market_value else 0.0
    return {
        "cash_mv":        round(cash_mv, 2),
        "floor_mv":       round(floor_mv, 2),
        "deployable_mv":  round(dep_mv, 2),
        "deployable_pct": round(dep_pct, 4),
    }
```
This function is the sole computation point for deployable cash. It uses `MIN_CASH_PCT` directly.

---

## Section 4 — `phase_7_4a_analysis.py` Constants

**File:** `phase_7_4a_analysis.py`, lines 28–31:
```python
# CONCENTRATED_ALPHA target cash band
MAX_CASH_PCT = 15.0
MIN_CASH_PCT = 2.0   # floor
```
This file is a standalone analysis script (not imported by the main pipeline). It independently defines `MIN_CASH_PCT = 2.0` and `MAX_CASH_PCT = 15.0`. These constants pre-date `deployment_queue.py`.

---

## Section 5 — Allocation Methodology YAML

**File:** `config/allocation_methodology.yaml`, CASH entry:
```yaml
- key: CASH
  label: "Cash"
  baseline_target_pct_of_parent: 2.0    # ← THIS IS THE METHODOLOGY BASELINE
  confidence_level: HIGH
  evidence_basis:
    - Minimum liquidity reserve for tactical rebalancing and opportunistic deployment
    - 2% cash floor is the structural minimum enforced by governance policy.
    - At current T-bill yields (4–5%), cash drag is partially offset by money market
      returns, making a 2% floor relatively low-cost in the current rate environment.
```

**Critical ambiguity:** The methodology YAML's `baseline_target_pct_of_parent: 2.0` is the **recalculation seed** — not the active target. The active target in the allocation model is 7.0%. The 2.0% in the methodology is the **structural floor seed value** that preceded the 7.0% mandate target. The allocation model overrides this with `CASH: 7.0` in `concentrated_alpha_profile.yaml`.

---

## Section 6 — `src/allocation/structural_policy.py`

**File:** `src/allocation/structural_policy.py`, line 36:
```python
cash_floor_pct=float(sp["cash_floor_pct"]),
```
Loads `cash_floor_pct = 2.0` from `allocation_policy.yaml` into `StructuralPolicy.cash_floor_pct`.

**Validator** (lines 83–86):
```python
cash_floor = float(sp.get("cash_floor_pct", 0))
if cash_floor < 0:
    errors.append("cash_floor_pct must be >= 0")
```
No validator checks that `cash_floor_pct` equals or is compatible with the allocation model's CASH node target.

**Important gap:** There is no code that validates consistency between:
- `allocation_policy.yaml: structural_policy.cash_floor_pct = 2.0`
- `concentrated_alpha_profile.yaml: nodes.CASH = 7.0`
- `deployment_queue.py: MIN_CASH_PCT = 2.0`

These three values can diverge independently.

---

## Section 7 — Recommendation Engine (PMI)

**File:** `src/portfolio/recommendations.py` (PMI — Portfolio Management Intelligence)

Cash-related computations:
1. `get_cash_interpretation()` — computes narrative from `cash_actual_pct` vs `cash_target_pct`
2. Cash funding source identification — sums `is_cash_equivalent` holdings to compute available capital
3. EXCESS_CASH flag — issued when cash exceeds 7.0% target by more than drift tolerance

**No separate deployment budget** exists in the recommendation engine. It computes available cash and issues recommendations based on allocation drift — it does not throttle deployment velocity or impose a DCA schedule.

---

## Section 8 — Optimizer Constraints

**File:** `src/portfolio/optimizer.py`:
```python
is_cash_eq = bool(getattr(holding, "is_cash_equivalent", False))
ac = str(getattr(holding, "asset_class", "")).upper()
if is_cash_eq or ac in ("CASH", "FIXED_INCOME"):
    return False   # not eligible for equity node matching
```
Cash is excluded from optimizer scoring entirely. The optimizer does not impose a maximum deployment amount or DCA schedule.

---

## Section 9 — UI Displays

### `ui/allocation_intelligence/app.js`
```javascript
{ label: "Cash Floor", value: `${sp.cash_floor_pct ?? "—"}%` }  // line 142
// Shows "Cash Floor: 2.0%" in strategy card

floor: sp.cash_floor_pct ?? 2,  // line 499
// CASH gauge uses floor from structural_policy.cash_floor_pct = 2.0
```

### `ui/portfolio_alignment/app.js`
```javascript
// Cash impact gauge (line 2212):
${parseFloat(pi.cash_before_pct).toFixed(1)}% → ${parseFloat(pi.cash_after_pct).toFixed(1)}%
// Shows "8.7% → 2.0%" — implies deploying nearly all cash to floor

// Deployable cash display (line 2063):
${formatMV(cashCtx.deployable_mv)}   // Shows "$31.7K" — full deployable at 2% floor
```

The UI does not display a "strategic target" vs "tactical floor" distinction. A user sees "$31.7K deployable" — the system implies this is the correct amount to deploy.

---

## Section 10 — Test Suite Expectations

**File:** `tests/test_7_5b_deployment_queue.py`

```python
def test_min_cash_pct(self):
    assert MIN_CASH_PCT == 2.0   # line 681 — hardcoded expectation
```
There is a regression test that `MIN_CASH_PCT == 2.0`. Any change to this constant would break this test.

**File:** `tests/test_7_5b_deployment_queue.py`, lines 479–485:
```python
def test_deployable_cash_above_floor():
    """Cash above MIN_CASH_PCT floor → deployable_mv > 0."""
    floor = total_mv * MIN_CASH_PCT / 100.0
    result = compute_deployable_cash([h_cash, h_other], total_mv)
    assert result["deployable_mv"] == pytest.approx(cash_mv - floor, abs=0.01)
```
Tests confirm the floor behavior explicitly but do not test whether the floor is philosophically appropriate.

---

## Section 11 — Simulation Script

**File:** `scripts/phase_7_5w_simulation.py`, line 1071:
```python
f"**Monthly deployment:** ${CYCLE_CASH:,.2f} (fresh injection each cycle)"
```
The simulation (Phase 7.5W) uses `CYCLE_CASH = deployable_mv = $31,683.33` as the monthly deployment amount — implying all deployable cash is used in a single cycle. This is "Model A" (immediate full deployment) in simulation terms.

---

## Section 12 — Summary Table

| Definition | Location | Value | Notes |
|-----------|----------|-------|-------|
| Strategic cash target | `concentrated_alpha_profile.yaml:18` | 7.0% | Mandate allocation model target |
| Policy floor (governance) | `allocation_policy.yaml:6` | 2.0% | Structural minimum |
| Policy CASH band | `allocation_policy.yaml:48-50` | 2–20% | Governance band |
| Deployment floor (code) | `deployment_queue.py:42` | `MIN_CASH_PCT = 2.0` | Hardcoded; independent of YAML |
| Methodology seed | `allocation_methodology.yaml` | 2.0% | Recalculation base; not active target |
| Deployable formula | `deployment_queue.py compute_deployable_cash()` | `cash_mv - floor_mv` | No DCA throttle |
| UI floor display | `app.js:499` | `sp.cash_floor_pct ?? 2` | Reads policy YAML floor |
| Test assertion | `test_7_5b_deployment_queue.py:681` | `assert MIN_CASH_PCT == 2.0` | Hardcoded regression test |
| Simulation assumption | `phase_7_5w_simulation.py` | Full `deployable_mv` per cycle | All-at-once model |

---

## Section 13 — Critical Observation

**The SIH has two separate cash concepts that are not architecturally connected:**

1. **Strategic cash target (7.0%):** What the portfolio *should* hold at steady state under the CONCENTRATED_ALPHA mandate. Defined in the allocation model YAML. Used by the recommendation engine and alignment calculations.

2. **Tactical deployment floor (2.0%):** The minimum cash reserve that the deployment engine will never deploy below. Defined as a hardcoded constant in `deployment_queue.py`. Unrelated to the strategic target.

**The gap:** When cash is at 8.7%, the system interprets this as:
- Allocation engine: "We are 1.7pp above our 7.0% strategic target — moderate excess"
- Deployment engine: "We have $31.7K available (everything above 2%) — deploy it all"

These two interpretations are not reconciled. The deployment engine's 2% floor is the governance minimum from `allocation_policy.yaml`, not the strategic target from the allocation model. The deployment engine does not consult the strategic target when computing deployable cash.
