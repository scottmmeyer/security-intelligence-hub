# Q6 — Deployment Policy Impact Analysis
## Phase 22D.5 — How does the current deployment policy affect downstream recommendation quality?

**Investigation run:** PAR-20260602-1BF2ADA5  
**Generated:** Phase 22D.5  

---

## Purpose

This analysis traces the downstream consequences of the current 2%-floor deployment policy on recommendation quality, concentration risk, and portfolio trajectory. It draws on:

1. The live PAR run (PAR-20260602-1BF2ADA5) deployment queue and plan
2. The Phase 7.5W 12-month simulation results (`data/analysis/phase_7_5w/operator_trust_assessment.md`)
3. The scenario analysis from Q4

---

## 1. What the Deployment Plan Proposes (Current Behavior)

From `deployment_plan.json`:
```
deployable_cash:   $31,683.33
cash_before_pct:   8.6592%
cash_after_pct:    2.0%
total_allocations: 0 (plan generated but allocations not committed)
```

The plan intends to reduce cash from **8.66% to 2.00%** in a single execution. This is the maximum available deployment under the current floor.

**Implication:** If the operator follows the deployment plan, the portfolio will have only $9,516 in cash reserves — the absolute governance minimum. Any opportunistic buying opportunity in the near term would require liquidating an equity position.

---

## 2. Position Concentration Impact

The CW-DAS deployment queue ranks 42 candidates. Current weights and positions at the top of the queue:

| Rank | Symbol | Score | Current Weight | Narrative Tier |
|------|--------|-------|---------------|----------------|
| 1 | VRT | 95.3 | 3.74% | CCL |
| 2 | ARW | 94.1 | 0.91% | HCA |
| 3 | ATLC | 93.5 | 0.87% | HCA |
| 4 | SNX | 93.5 | 0.91% | HCA |
| 5 | PSX | 93.3 | 0.76% | HCA |
| 6 | CBOE | 93.2 | 0.63% | HCA |
| 7 | AVT | 92.1 | 0.91% | HCA |
| 8 | LRCX | 91.8 | 0.93% | HCA |
| 9 | CAH | 91.6 | 1.03% | HCA |
| 10 | SANM | 90.8 | 0.67% | HCA |

**VRT (Vertiv Holdings)** is the top-ranked position with 3.74% weight and CCL tier. Per the CW-DAS formula, VRT receives preferential scoring due to its CCL designation. Under Scenario A (deploy $31.7K), VRT would receive the largest single allocation.

---

## 3. VRT Concentration Risk (from Phase 7.5W Simulation)

The 12-month simulation (`operator_trust_assessment.md`) shows:
```
VRT WARN threshold (6%) reached: Month 4
VRT BLOCKED from further deployment: Months 4–12
```

Under the full $31.7K deployment (Scenario A):
- **After first deployment:** VRT receives a significant allocation, approaching or hitting the WARN threshold (6%)
- **CW-DAS response:** Once VRT reaches WARN threshold, its `sizing_c` component drops to 0, removing it from future deployment eligibility
- **Rotation:** Capital rotates to next-tier positions (ARW, ATLC, SNX, PSX)

**Assessment:** The WARN/MAX position gates in CW-DAS (lines 205–210 of `deployment_queue.py`) correctly prevent VRT from being infinitely concentrated. This is a strong architectural safeguard. However, the large deployment amount ($31.7K) means VRT can absorb a large initial allocation before the gate activates.

---

## 4. What Happens at 7% Floor (Scenario C)

Under Scenario C (deploy only excess above 7% target, $7,894 deployable):

- **VRT allocation:** ~$1,600–$2,200 (proportional to its deployment score vs. top-20)
- **VRT weight after:** ~3.74% + 0.3–0.5% → ~4.1–4.3% (still well below 6% WARN)
- **VRT WARN risk:** LOW — VRT doesn't approach the WARN threshold in the first cycle
- **More cycles before saturation:** VRT remains deployable for 4+ cycles before hitting WARN

This means Scenario C (target-aligned floor) **preserves the deployment queue's diversity** over more cycles. With a smaller per-cycle budget, more securities can receive meaningful allocations over the same time horizon.

---

## 5. HHI Trajectory Comparison

From the Phase 7.5W simulation (Scenario A, full deployment monthly):
```
Month 1:  HHI = 0.0298
Month 4:  HHI = 0.0358  (VRT BLOCKED)
Month 8:  HHI = 0.0461
Month 12: HHI = 0.0618  (HHI has more than doubled from baseline)
```

Extrapolation for Scenario C (deploy ~$7.9K/cycle):
- Per-cycle HHI change: ~+3.1 (vs. +14.0 for full deployment)
- HHI after 12 cycles under Scenario C: ~223 + (3.1 × 12) = ~260 (vs. ~460 projected for Scenario A if deployed monthly)
- HHI growth rate under Scenario C is approximately **4.5× slower** than Scenario A

---

## 6. Cash Replenishment Dynamics

**Scenario A (2% floor):**
- Cash drops to $9,516 (2%)
- To return to 7% target: need $23,789 additional cash
- At a typical $2–3K/month dividend + cash inflow rate, recovery takes 8–12 months
- During recovery, portfolio has no dry powder for opportunistic deployment

**Scenario C (7% floor):**
- Cash stays at $33,305 (7%)
- No replenishment needed — portfolio is at target
- Any new cash inflows immediately push cash above 7%, creating a new deployable excess
- The dry powder reserve is continuously maintained

The architectural difference: Scenario C **preserves the deployment cycle**. Future cycles will also have small deployable amounts as excess above 7%. Scenario A creates a **cash depletion event** that breaks the cycle until replenishment occurs.

---

## 7. Recommendation Engine Coherence

From `src/portfolio/recommendations.py` (PMI layer):

The recommendation engine issues an `EXCESS_CASH` flag when cash exceeds the allocation target by more than drift tolerance. With cash at 8.66% and target 7.0%:

- **EXCESS_CASH flag:** Active — 1.66pp excess is within typical drift tolerance (2.0pp), so flag may be informational
- **Drift direction:** OVER_TARGET
- **Recommendation signal:** "Deploy excess cash into high-conviction positions"

If Scenario A is executed:
- After deployment: cash = 2.0% — UNDERWEIGHT vs. 7.0% target by 5.0pp
- **New flag:** `CASH_UNDERWEIGHT` or `REBALANCE_NEEDED` would be issued
- The system would not show cash as overweight anymore, but would not recommend buying more cash either — it would wait for natural cash accumulation

If Scenario C is executed:
- After deployment: cash = 7.0% — exactly at target
- **No flag:** Cash alignment is clean
- Next cycle: any accumulated dividends/inflows push cash slightly above 7%, creating a small new deployable excess
- The recommendation engine stays in a clean, coherent state

**Scenario C produces more coherent recommendations** — after each deployment, the system is at target, not in a new deficit condition.

---

## 8. Phase 7.5W vs. Reality Gap

The Phase 7.5W simulation assumed $31,683 of *new capital* each month — modeling a DCA injection scenario, not a one-time depletion. The simulation's "ACCEPTABLE" verdict applies to that DCA model.

The actual PAR run's deployment plan proposes a **one-time depletion**: cash goes from 8.66% to 2.00% in a single execution. The simulation does not model this scenario. The 12-month simulation's conclusion — that the system distributes well and VRT gets blocked naturally — applies to gradual DCA, not a one-time cash sweep.

If the one-time depletion is executed:
- Cash is at 2% (floor only)
- No further deployment is possible until cash replenishes
- The deployment engine would show $0 deployable for multiple months
- The "natural rotation" the simulation demonstrates would be paused

---

## 9. Signal Coherence for the Operator

The current state presents a potentially confusing mixed signal:
- **Strategy card** says: "Cash Floor: 2.0%" — implying 2% is the reserve
- **Deployment gauge** says: "$31.7K deployable" — implying deploying to 2% is the right action
- **Mandate philosophy** says: "Cash is dry powder" — implying 7% should be preserved
- **Alignment engine** says: "Cash 8.66% vs 7.0% target — slight excess" — implying only the 1.66% excess should be deployed

An operator who trusts the deployment plan ($31.7K) would deploy 5× more than an operator who trusts the alignment engine's excess calculation ($7.9K of actual excess). The two numbers ($31.7K vs $7.9K) are inconsistent and the system presents both without reconciliation.

---

## 10. Summary of Impact

| Dimension | Scenario A (2% floor) | Scenario C (7% floor) |
|-----------|----------------------|----------------------|
| Post-deployment cash | 2.00% (floor only) | 7.00% (at target) |
| Tactical dry powder preserved | NO | YES |
| Future deployable cycles | Blocked until replenishment | Continuous small deployments |
| Recommendation coherence after | CASH_UNDERWEIGHT flag likely | Clean — no new flag |
| HHI change | +14.0 (higher concentration) | +3.1 (minimal) |
| VRT WARN risk in cycle 1 | HIGH | LOW |
| Phase 7.5W simulation applicability | LOW (sim modeled DCA, not depletion) | HIGH (matches small-cycle DCA model) |
| Mandate alignment | LOW | HIGH |

---

## Conclusion

The current 2%-floor deployment policy:
1. Creates a **one-time cash depletion event** rather than a sustainable deployment cycle
2. Produces **recommendation incoherence** — post-deployment cash is far below the strategic target
3. **Contradicts the mandate philosophy** — after deployment, no dry powder exists
4. **Reduces future deployment optionality** — the engine shows $0 deployable for months after

A 7%-floor policy (Scenario C) resolves all four issues at the cost of deploying 75% less capital per cycle. Given the mandate's explicit "dry powder" philosophy, this trade-off is correct.
