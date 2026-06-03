# Q2 — Strategic vs Tactical Cash Analysis
## Phase 22D.5 — Are the 7% target and 2% floor architecturally consistent?

**Investigation run:** PAR-20260602-1BF2ADA5  
**Generated:** Phase 22D.5  

---

## Thesis

The CONCENTRATED_ALPHA mandate defines a **7.0% strategic cash target** in the allocation model, with an explicit philosophy that "cash is treated as dry powder, not idle drag." However, the deployment engine uses a **2.0% tactical floor** as its reserve — deploying everything above that floor. The two values evolved independently and are not architecturally reconciled. The result is a system that says it treats cash as dry powder but behaviorally minimizes cash to 2%.

---

## Two Separate Subsystems

### Subsystem A — Allocation Intelligence (Strategic Layer)

The allocation model defines *what the steady-state portfolio should look like*:

```
CONCENTRATED_ALPHA mandate
└─ nodes (depth 1)
   ├─ EQUITIES: 88.0%
   ├─ FIXED_INCOME: 2.0%
   ├─ DIGITAL: 1.0%
   ├─ COMMODITIES: 2.0%
   └─ CASH: 7.0%           ← the intended steady-state cash position
```

This 7.0% is an **allocation target** — a statement of portfolio composition intent. The recommendation engine computes "cash is 8.66%, target is 7.0%, drift = +1.66pp" and would show moderate excess but not a strong DEPLOY signal.

**Philosophy:** "Cash treated as dry powder, not idle drag."  
**Interpretation:** Cash is a deliberate strategic reserve. The 7.0% target means maintaining dry powder for opportunistic deployment *when conviction is high*, not systematically deploying at every cycle.

---

### Subsystem B — Deployment Queue (Tactical Layer)

The deployment engine defines *how to deploy excess cash above the absolute floor*:

```python
MIN_CASH_PCT = 2.0   # mandate floor — reserve never deployed below this level

def compute_deployable_cash(holdings, total_market_value):
    cash_mv  = sum(h.market_value for h in holdings if h.is_cash_equivalent)
    floor_mv = total_market_value * MIN_CASH_PCT / 100.0
    deployable_mv = max(0.0, cash_mv - floor_mv)
    return {...}
```

With 8.66% cash ($41,199) and total MV $475,779:
```
floor_mv     = $475,779 × 2.0% = $9,516
deployable   = $41,199 - $9,516 = $31,683   (6.66% of portfolio)
```

**Interpretation:** The system offers $31,683 as immediately deployable — 77% of the current cash position. The deployment plan shows `cash_after_pct = 2.0%` — it intends to reduce cash from 8.66% to 2.00% in a single execution.

---

## Where They Diverge

| Dimension | Strategic Layer (7% target) | Deployment Layer (2% floor) |
|-----------|----------------------------|-----------------------------|
| Governing file | `concentrated_alpha_profile.yaml` | `deployment_queue.py` |
| Concept | Steady-state allocation target | Absolute minimum reserve |
| With 8.66% cash | "Moderate excess; 1.66pp above target" | "Deploy $31.7K; reduce to 2%" |
| After deployment | 7% → back at target | 2% → far below target |
| Data flow | Alliance intelligence engine → recommendations | Deployment queue → deployment plan |
| Architectural relationship | Independent — not connected | Independent — not connected |

The **deployment engine does not read the strategic cash target**. It reads only `MIN_CASH_PCT` (hardcoded 2.0%) and computes relative to that. It has no knowledge that the mandate calls for 7.0% as a target — only that governance prohibits going below 2.0%.

---

## Evidence That These Evolved Independently

### 1. Phase 7.4A Analysis Script (earliest traceable origin)

`phase_7_4a_analysis.py`, line 28–31:
```python
# CONCENTRATED_ALPHA target cash band
MAX_CASH_PCT = 15.0
MIN_CASH_PCT = 2.0   # floor
```

This script pre-dates `deployment_queue.py`. The `MIN_CASH_PCT = 2.0` here is described as "the floor" of a *target band* (2–15%). When `deployment_queue.py` was later built, it copied the floor constant but did not implement a concept of "target band" — only "minimum floor."

### 2. Allocation Methodology YAML Seed

`config/allocation_methodology.yaml`:
```yaml
- key: CASH
  baseline_target_pct_of_parent: 2.0
```
The methodology **seed** for CASH is 2.0% — the structural minimum. This is the value the evidence-weighted recalculation engine starts from before applying mandate-specific overrides. The 7.0% in `concentrated_alpha_profile.yaml` is the **mandate override**, not the baseline.

This means the 2.0% was the *original* CASH target in the allocation methodology layer. The 7.0% was introduced deliberately at the mandate level to reflect a more conservative, dry-powder-oriented posture for CONCENTRATED_ALPHA. The deployment engine was never updated to reflect this shift.

### 3. ALLOCATION_PRIMER_WHY_THESE_NUMBERS.md

`docs/ALLOCATION_PRIMER_WHY_THESE_NUMBERS.md`, lines 94–97:
```
The 2% cash floor is the governance-enforced minimum.
Holding more than 2–3% cash in a growth portfolio is a drag.
```
This documentation describes a **growth-oriented** perspective — minimizing cash drag. But CONCENTRATED_ALPHA is NOT a growth portfolio in the traditional sense; it holds concentrated conviction positions and intentionally maintains higher cash as dry powder.

The 2% floor was documented as appropriate for a growth mandate. The CONCENTRATED_ALPHA mandate's 7% target reflects a different philosophy — but the deployment engine was never updated.

### 4. No `cash_strategy_pct` Parameter

The `compute_deployable_cash()` function signature:
```python
def compute_deployable_cash(holdings, total_market_value) -> dict
```
There is no `strategy_cash_target` or `mandate_cash_target` parameter. The function has no architectural pathway to receive the strategic target — it can only use the hardcoded floor.

---

## Current Behavioral Implication

If the operator follows all deployment recommendations in the current cycle:

| State | Cash % | Cash MV |
|-------|--------|---------|
| Before deployment | 8.66% | $41,199 |
| After full deployment | 2.00% | $9,516 |

The system would reduce cash from **8.66% to 2.00%** — a reduction of 77% of the cash position in a single cycle. This is the opposite of a dry-powder reserve strategy.

The strategic mandate says: "Cash is dry powder. Hold 7% for opportunistic deployment."  
The deployment engine says: "You have $31.7K. Here's where to put it."

---

## Are the 12-Month Simulation Results Consistent with This Analysis?

From `data/analysis/phase_7_5w/operator_trust_assessment.md`:
```
Monthly deployment: $31,683.33 (fresh injection each cycle)
HHI change (12 months): 0.02982 → 0.06178
VRT WARN threshold hit: months 4–12
```

The simulation assumes `$31,683.33` (the full deployable amount) is deployed each month with a "fresh injection each cycle" — meaning a hypothetical redeployment of a new monthly cash inflow. This is a simulation of DCA behavior using a constant monthly budget, not the one-time deployment of existing excess cash.

The simulation does NOT model what happens if you deploy $31,683 once from the existing 8.66% position (reducing to 2%) — which is what the deployment plan actually proposes.

---

## Conclusion

**The 7% strategic target and 2% deployment floor are not architecturally consistent.** They:
- Were set independently, without cross-reference
- Are maintained independently (YAML vs. hardcoded constant)
- Are consumed by independent subsystems (allocation engine vs. deployment engine)
- Are not validated for consistency at any point in the pipeline
- Produce conflicting behaviors: the mandate says "preserve dry powder," the deployment engine says "deploy 77% of cash"

The current architecture implements a *de facto* "minimize cash above 2%" deployment policy, regardless of the strategic mandate's explicit 7% dry powder target. Whether this is intentional (the operator wants to deploy the excess and rebuild) or unintentional (the deployment engine has an incorrect floor) is the policy question Phase 22D.5 must resolve.
