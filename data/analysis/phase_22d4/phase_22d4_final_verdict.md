# Phase 22D.4 — Final Verdict: Cash Governance Trace

**Phase:** 22D.4 — Cash Governance Trace  
**Investigation run:** PAR-20260602-1BF2ADA5  
**Active mandate:** CONCENTRATED_ALPHA  
**Generated:** Phase 22D.4 — read-only forensic trace

---

## Verdict

**B. STRATEGIC_VS_TACTICAL_CASH**

The `8.7% → 2.0%` deployment projection is correct and expected. There is no bug, no misconfiguration, and no data error. The apparent contradiction between the 7.0% strategic cash target and the 2.0% projected post-deployment cash arises because these numbers belong to **architecturally separate systems** with **different purposes**.

---

## Question-by-Question Findings

### Q1 — Where does the 7.0% cash target come from?

| Field      | Value |
|------------|-------|
| **Source** | `config/allocation_models/concentrated_alpha_profile.yaml` |
| **Key**    | `nodes.CASH: 7.0` |
| **Concept** | Strategic allocation model target — intended steady-state cash weight |
| **System layer** | Allocation intelligence (drift detection, recalculation engine) |

Full trace: [cash_target_trace.md](cash_target_trace.md)

---

### Q2 — Where does the 2.0% post-deployment projection come from?

| Field      | Value |
|------------|-------|
| **Source** | `src/portfolio/deployment_queue.py`, line 43 |
| **Key**    | `MIN_CASH_PCT = 2.0   # mandate floor` |
| **Concept** | Tactical cash floor — the minimum reserve the deployment engine never breaches |
| **System layer** | Deployment engine (CW-DAS scoring, deployment queue, planner) |

Full trace: [cash_deployment_trace.md](cash_deployment_trace.md)

---

### Q3 — Is the math correct?

**YES — math validates to machine precision.**

| Metric                   | Value         | Verification |
|--------------------------|---------------|--------------|
| Total portfolio MV       | $475,779.42   | deployment_queue.json |
| Cash before (SPAXX)      | $41,198.92    | = 8.6592% of portfolio → UI shows 8.7% |
| Tactical floor (2.0%)    | $9,515.59     | = $475,779.42 × 2.0% |
| Deployable               | $31,683.33    | = $41,198.92 − $9,515.59 |
| Total allocated          | $31,683.31    | deployment_plan.json (±$0.02 rounding) |
| Cash after               | $9,515.61     | = $41,198.92 − $31,683.31 |
| Cash after %             | 2.0000%       | = $9,515.61 / $475,779.42 × 100 → UI shows 2.0% |

Rounding residual: $0.02 (unallocated_cash in portfolio_impact). Floor is honored.

Full validation: [cash_math_validation.csv](cash_math_validation.csv)

---

### Q4 — Is it intentional that cash falls to 2.0% after full deployment?

**YES — this is the explicitly designed behavior.**

1. `MIN_CASH_PCT = 2.0` is documented as "mandate floor — reserve never deployed below this level"
2. `compute_deployable_cash()` defines `deployable_mv = max(0.0, cash_mv − floor_mv)` — deploys everything above the floor
3. The test suite explicitly validates `cash_after_pct ≈ 2.0%` and labels it "minimum reserve"
4. The planner has no reference to the allocation model YAML — the 7.0% target is invisible to it

---

### Q5 — Is the UI card displaying the values correctly?

**YES — the UI card is correct.**

The UI reads `portfolio_impact.cash_before_pct` and `portfolio_impact.cash_after_pct` from the deployment plan JSON and renders them with `.toFixed(1)`. The values:

- `8.6592%` → displayed as `8.7%` ✓
- `2.0000%` → displayed as `2.0%` ✓

These are mathematically accurate. The UI correctly shows the deployment outcome — cash drops to the tactical floor after full deployment. The UI does not represent the strategic target (7.0%) in this card, which may create a perceived contradiction, but both values are individually correct for their respective concepts.

---

### Q6 — Are there three distinct cash concepts?

**YES — three fully separate cash concepts, each in its own system layer.**

| Concept               | Value    | Governed by                                      | Purpose                               |
|-----------------------|----------|--------------------------------------------------|---------------------------------------|
| Strategic Target      | 7.0%     | `concentrated_alpha_profile.yaml` + validators   | Steady-state allocation goal          |
| Tactical Floor        | 2.0%     | `allocation_policy.yaml` + `MIN_CASH_PCT`        | Hard minimum reserve (never deployed) |
| Deployable Reserve    | $31,683  | `compute_deployable_cash()` in deployment_queue  | Actual deployment budget              |

The deployment engine uses only Concept 2 (floor) and Concept 3 (reserve). It has no knowledge of Concept 1 (strategic target).

Full analysis: [cash_governance_analysis.md](cash_governance_analysis.md)

---

## Why the Verdict is B, Not a Bug

The 7.0% is an **allocation intelligence** concept. The deployment engine is operating in a separate subsystem with a separate mandate: maximize capital deployed to conviction positions, constrained only by the structural safety floor.

After a full deployment cycle, the portfolio will be at 2.0% cash. At that point, the **allocation intelligence layer** would correctly flag CASH as severely underweight (actual: 2.0%, target: 7.0%, drift: −5.0pp) and generate a REBALANCE recommendation. The appropriate response is to reduce equity positions and rebuild cash to the 7.0% target — **not** for the deployment engine to stop deploying at 7.0%.

This is the correct architectural separation:
- **Deployment engine** answers: "What should I buy with the available cash?"
- **Allocation intelligence** answers: "Is the portfolio composition aligned with the mandate?"

The two systems operate independently and complement each other.

---

## Verdict Declaration

```
PHASE_22D.4_VERDICT: B. STRATEGIC_VS_TACTICAL_CASH

The 8.7% → 2.0% cash projection is mathematically correct and architecturally 
intentional. The deployment planner operates against the 2.0% tactical floor 
(MIN_CASH_PCT in deployment_queue.py), not the 7.0% strategic allocation target 
(CASH node in concentrated_alpha_profile.yaml). These two values belong to 
separate, independent subsystems with separate governance. No code change, 
data correction, or configuration adjustment is warranted.

STATUS: CLOSED — NO ACTION REQUIRED
```

---

## Files Produced

| File | Contents |
|------|----------|
| [cash_target_trace.md](cash_target_trace.md) | Q1: Full provenance chain for the 7.0% strategic target |
| [cash_deployment_trace.md](cash_deployment_trace.md) | Q2: Full code path for the 2.0% projected post-deployment cash |
| [cash_math_validation.csv](cash_math_validation.csv) | Q3: Exact portfolio numbers with formula verification |
| [cash_governance_analysis.md](cash_governance_analysis.md) | Q4+Q5+Q6: Planner intent, UI correctness, three-concept taxonomy |
| [phase_22d4_final_verdict.md](phase_22d4_final_verdict.md) | Q7: This file — final verdict and summary |
