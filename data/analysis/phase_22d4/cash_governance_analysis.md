# Phase 22D.4 — Cash Governance Analysis
## Q4: Is the planner behavior intentional? Q5: Is the UI card correct? Q6: Are the three cash concepts separate?

**Investigation run:** PAR-20260602-1BF2ADA5  
**Active mandate:** CONCENTRATED_ALPHA  
**Generated:** Phase 22D.4 — read-only forensic trace

---

## Q4 — Is the planner behavior intentional? (Cash drops to 2.0% after full deployment)

**Answer: YES — this is the designed behavior of the deployment engine.**

### Evidence

**1. Explicit constant with explanatory comment**

`src/portfolio/deployment_queue.py`, line 43:
```python
MIN_CASH_PCT = 2.0   # mandate floor — reserve never deployed below this level
```

The comment leaves no ambiguity. The author documented this as a floor constraint, not a target-seeking mechanism.

**2. `compute_deployable_cash()` defines the entire deployable range**

The function calculates `deployable_mv = max(0.0, cash_mv - floor_mv)`. The planner then allocates the full `deployable_mv` across the conviction queue. Remaining cash after full deployment always equals `floor_mv`, which at 2.0% of total portfolio = exactly `MIN_CASH_PCT`.

**3. Test suite validates 2.0% as the expected outcome**

`tests/test_7_5f_deployment_actionability.py`, line 129:
```python
def test_cash_after_pct_at_minimum_reserve(self):
    # Cash must be at minimum reserve (2.0%) after deployment
    assert abs(self.pi["cash_after_pct"] - 2.0) < 0.1
```

The test description calls this "minimum reserve" and checks the value against 2.0%, not 7.0%. This was written knowingly.

**4. The planner has no coupling to the allocation model**

The deployment planner (`deployment_planner.py`) and queue (`deployment_queue.py`) do not import, read, or reference `concentrated_alpha_profile.yaml` or any allocation model at runtime. The value `MIN_CASH_PCT = 2.0` is a **self-contained policy constant** in the deployment subsystem. The two systems are architecturally independent.

**Conclusion:** The deployment engine intentionally deploys all cash above the 2.0% structural floor. It is a **floor-based depletion model**, not a target-seeking model. It does not attempt to maintain or return to the 7.0% strategic allocation target.

---

## Q5 — Is the UI card displaying the "CASH WT BEFORE → AFTER: 8.7% → 2.0%" correctly?

**Answer: YES — the UI card is displaying mathematically accurate values derived directly from planner output.**

### Evidence

**1. UI reads directly from `portfolio_impact` JSON**

`ui/portfolio_alignment/app.js`, line 2185:
```javascript
const pi = plan.portfolio_impact || {};
```

Line 2212:
```javascript
<div class="da-cash-val">
  ${pi.cash_before_pct != null ? parseFloat(pi.cash_before_pct).toFixed(1) : "—"}%
  → 
  ${pi.cash_after_pct != null ? parseFloat(pi.cash_after_pct).toFixed(1) : "—"}%
</div>
```

The UI renders `cash_before_pct.toFixed(1)` and `cash_after_pct.toFixed(1)` — one decimal place of the raw planner output.

**2. The raw values are accurate**

From `deployment_plan.json` (PAR-20260602-1BF2ADA5):
```
cash_before_pct = 8.6592  →  displayed as "8.7%"
cash_after_pct  = 2.0000  →  displayed as "2.0%"
```

Both values accurately reflect portfolio state. `8.7%` is the current cash weight, rounded from `8.6592%`. `2.0%` is the post-deployment minimum reserve floor.

**3. A second render location also uses the same values**

`ui/portfolio_alignment/app.js`, line 2594:
```javascript
<div class="dp-impact-val">
  ${pct(impact.cash_before_pct)}
  → 
  <span class="dp-green">${pct(impact.cash_after_pct)}</span>
</div>
```

Both display locations render the same accurate source data.

**4. The values pass their own unit test**

`tests/test_7_5f_deployment_actionability.py`:
```python
def test_cash_before_pct_reasonable(self):
    assert 5.0 <= self.pi["cash_before_pct"] <= 20.0

def test_cash_after_pct_at_minimum_reserve(self):
    assert abs(self.pi["cash_after_pct"] - 2.0) < 0.1
```

**Conclusion:** The UI card is not incorrect. It accurately shows what will happen if the full deployment queue is executed: cash drops from `8.7%` to `2.0%`. The potential source of confusion is that `2.0%` is below the **strategic target** of `7.0%`, but the UI is rendering the **tactical deployment outcome**, not the allocation model target. These are different concepts (see Q6).

---

## Q6 — Are there actually three separate cash concepts? Are they sufficiently distinct?

**Answer: YES — there are three distinct cash concepts, each governed separately, each with a different purpose.**

### The Three Cash Concepts

---

### Concept 1: Strategic Cash Target

| Attribute     | Value |
|---------------|-------|
| Value         | **7.0%** of total portfolio value |
| Type          | Allocation model node target |
| Source        | `config/allocation_models/concentrated_alpha_profile.yaml` → `nodes.CASH: 7.0` |
| Governed by   | `src/allocation/validators.py` (validates >= `cash_floor_pct`) |
| Semantics     | The **intended steady-state allocation** to cash under the CONCENTRATED_ALPHA mandate |
| Role          | Defines the long-run portfolio composition goal. Used by allocation intelligence to detect cash drift, generate CASH drift recommendations, and evaluate if current cash is overweight/underweight. |
| Mandate note  | "Cash treated as dry powder, not idle drag." — Cash is maintained at 7.0% intentionally; it is a **conviction reserve** waiting for opportunities |

---

### Concept 2: Tactical Cash Floor

| Attribute     | Value |
|---------------|-------|
| Value         | **2.0%** of total portfolio value |
| Type          | Hard constraint — never deployable |
| Source (code) | `src/portfolio/deployment_queue.py` → `MIN_CASH_PCT = 2.0` |
| Source (policy) | `config/allocation_policy.yaml` → `structural_policy.cash_floor_pct: 2.0` |
| Source (governance) | `config/allocation_policy.yaml` → `asset_class_governance.CASH.min_pct: 2.0` |
| Semantics     | The **absolute minimum** cash reserve. The deployment engine will never allocate below this level. |
| Role          | Liquidity and operational safety floor. Ensures the portfolio always retains a minimum cash buffer regardless of deployment activity. |

---

### Concept 3: Deployable Cash Reserve

| Attribute     | Value |
|---------------|-------|
| Value (PAR run) | **$31,683.33** (6.6592% of portfolio) |
| Type          | Computed quantity — cash available for deployment |
| Source        | `deployment_queue.py` `compute_deployable_cash()` |
| Formula       | `max(0.0, cash_mv − floor_mv)` = `$41,198.92 − $9,515.59` |
| Semantics     | The portion of cash **above the tactical floor** that the planner is authorized to allocate to conviction positions |
| Role          | The actual deployment budget. Fed to the CW-DAS conviction queue and distributed across Tier 1/2/3 holdings. |

---

### Relationship Between the Three Concepts

```
                    ┌─────────────────────────────────────────────────┐
  8.6592%           │        CURRENT CASH (overweight)                │
  $41,198.92        │                                                  │
                    │  ┌───────────────────────────────┐              │
  6.6592%           │  │   DEPLOYABLE CASH RESERVE     │              │
  $31,683.33        │  │   ($41,198.92 − $9,515.59)    │              │
                    │  │   CW-DAS allocates this        │              │
  7.0% strategic ──►│  │   ≈ would stop here if planner│              │
  target            │  │     targeted 7.0% instead     │              │
                    │  └───────────────────────────────┘              │
  2.0% floor ──────►│  ┌──────────────────────────────┐               │
  $9,515.59         │  │   TACTICAL CASH FLOOR        │               │
                    │  │   (MIN_CASH_PCT = 2.0%)       │               │
  0%                │  │   Never deployed              │               │
                    └──┴──────────────────────────────┴───────────────┘
```

**Key observation:** The current cash (8.66%) is **above** the strategic target (7.0%), meaning the portfolio is cash-overweight. However, the deployment engine does not target 7.0% — it targets 2.0%. The entire gap between current cash and the 2.0% floor is treated as deployable. There is no intermediate stop at the 7.0% strategic level.

---

### Why the System Doesn't Target 7.0% for Deployment

The allocation intelligence subsystem and the deployment subsystem are **architecturally independent**:

1. **Allocation intelligence** (validators, recalculation engine) owns the 7.0% strategic target. It monitors drift from 7.0% and would generate a CASH drift recommendation if cash were significantly below or above target. It operates at the portfolio-level planning horizon.

2. **Deployment engine** (deployment_queue.py, deployment_planner.py) owns the 2.0% tactical floor. It manages capital deployment in a specific conviction cycle. It has no reference to the allocation model YAML.

This separation is a design choice: the deployment engine maximizes capital deployed toward conviction positions, subject only to the structural safety floor. The strategic 7.0% target is an allocation intelligence concern, not a deployment constraint.

---

## Summary Table

| Cash Concept         | Value    | Source File                                     | Purpose                    | System Layer      |
|----------------------|----------|-------------------------------------------------|----------------------------|-------------------|
| Strategic Target     | 7.0%     | `concentrated_alpha_profile.yaml` nodes.CASH    | Steady-state allocation goal | Allocation intelligence |
| Tactical Floor       | 2.0%     | `deployment_queue.py` MIN_CASH_PCT              | Deployment hard constraint  | Deployment engine |
| Deployable Reserve   | $31,683.33 (6.66%) | `deployment_queue.py` compute_deployable_cash() | Actual deployment budget | Deployment engine |
