# Q5 — DCA Policy Design Options
## Phase 22D.5 — What DCA deployment approaches exist?

**Investigation run:** PAR-20260602-1BF2ADA5  
**Generated:** Phase 22D.5  
**Deployable at 2% floor:** $31,683.33  
**Deployable at 7% floor:** $7,894.36  

---

## What Does DCA Mean in This Context?

Dollar-cost averaging (DCA) as applied to capital deployment means spreading the deployment of excess cash across multiple time periods rather than deploying it all at once. The goal is:

1. **Reduce timing risk** — avoid deploying all capital into an unfavorable short-term market window
2. **Preserve tactical optionality** — maintain dry powder for genuine opportunities that may emerge
3. **Reduce behavioral momentum** — avoid over-concentrating in a single cycle's top-ranked positions
4. **Match mandate philosophy** — align deployment velocity with "dry powder" intent

The current SIH has **no DCA concept**. The deployment engine computes the full deployable amount each cycle and presents it as the deployment budget. There is no concept of a monthly deployment budget, a deployment schedule, or a velocity cap.

---

## Current Behavior (Model A — Baseline)

**Model A: Deploy all excess cash immediately (current)**

```
Cycle: Deploy $31,683 now
Cash after: 2.0%
Reserve: $9,516 (at governance floor only)
Philosophy alignment: LOW — contradicts "dry powder" mandate
Timing risk: HIGH — all at current prices
Optionality: NONE — no reserve above governance floor
Code change needed: NONE — current behavior
```

At $31,683 distributed across 42 queue candidates:
- Average allocation: $754 per position
- Top-5 allocations (proportional by score): ~$1,200–$2,400 each
- Phase 7.5W simulation shows: VRT concentration warning by month 4 when this is repeated monthly

The current system is maximally aggressive. If the operator executes the full deployment plan every cycle, the portfolio gradually concentrates (HHI 0.030 → 0.062 over 12 months per simulation).

---

## Design Option B — Monthly Budget from Full Deployable over 3 Months

**Spread $31,683 across 3 months**

```
Monthly budget: $10,561 ($31,683 / 3)
Budget as % of portfolio: 2.22%/month
Cash position after each cycle: ~6.4%, ~4.2%, ~2.0%  (approximate)
Philosophy alignment: MODERATE
Timing risk: LOWER — 3 price entry points
Optionality: BETTER — $21K+ remains for months 2–3
Code change: ADD monthly_budget or cycle_fraction to deployment plan
```

At $10,561/month:
- Average allocation per position across top-10: ~$1,056
- Scenario: Month 1 deploys VRT/ARW/ATLC; Months 2–3 deploy next tier
- Downside: Still exhausts cash to 2% by month 3 (not respecting 7% target)

---

## Design Option C — Monthly Budget from Full Deployable over 6 Months

**Spread $31,683 across 6 months**

```
Monthly budget: $5,281 ($31,683 / 6)
Budget as % of portfolio: 1.11%/month
Cash position trajectory: 8.66% → 7.5% → 6.4% → 5.3% → 4.2% → 3.1% → 2.0%
Philosophy alignment: MODERATE
Timing risk: LOWER — 6 price entry points
Optionality: GOOD — $26K+ remains for months 2–6
Code change: ADD monthly_budget param to deployment plan
```

At $5,281/month:
- Cash stays above the 7% mandate target until month 3 (remains "in target range" for the first 2 cycles)
- HHI change per cycle is minimal (~$5.3K deployed vs $31.7K → less portfolio impact)

---

## Design Option D — Monthly Budget from Full Deployable over 12 Months

**Spread $31,683 across 12 months**

```
Monthly budget: $2,640 ($31,683 / 12)
Budget as % of portfolio: 0.55%/month
Cash position trajectory: 8.66% → gradual reduction to 2.0% over one year
Philosophy alignment: MODERATE-LOW (still reaching 2% eventually)
Timing risk: LOWEST — 12 price entry points
Optionality: EXCELLENT — large reserve maintained throughout
Code change: ADD monthly_budget param to deployment plan
```

At $2,640/month:
- Average allocation per position (top-5 focus): $528/position
- Cash stays comfortably above 7% mandate target for the first 6+ months
- Provides maximum market timing optionality

---

## Design Option E — Target-Aligned Deployment (Preferred Candidate)

**Deploy only excess above the 7% strategic target, in one cycle**

```
Floor: 7.0% (strategic mandate target)
Deployable: $7,894 (cash MV - 7% floor)
Cash after: 7.00% — exactly at mandate target
Budget per cycle: Only excess above mandate target
Philosophy alignment: HIGH — fully consistent with "dry powder" philosophy
Timing risk: LOW — small deployment per cycle
Optionality: EXCELLENT — 7% reserve maintained
Code change: MODIFY compute_deployable_cash() to accept strategy_cash_target parameter
```

At $7,894/cycle:
- Average allocation per position (top-10): ~$789
- Cash stays at exactly the mandate target after deployment
- The system "naturally" deploys only the accumulated excess above the strategic target
- No need for explicit DCA schedule — the architecture itself enforces target-preservation

**This is the architectural equivalent of DCA built into the floor, not DCA as a scheduling mechanism.**

---

## Design Option F — Hybrid (Recommended)

**Deploy excess above 7% target, but cap at 50% of excess per cycle**

```
Strategic floor: 7.0%
Excess (deployable at 7% floor): $7,894
Deploy per cycle: 50% of excess = $3,947
Cash after: ~7.83% (halfway between current 8.66% and target 7.0%)
Accumulates toward 7% over 2 cycles
Philosophy alignment: HIGH — approaches target gradually
Timing risk: VERY LOW — minimal deployment per cycle
Optionality: EXCELLENT — well above 7% reserve for next cycle
```

This provides an additional DCA buffer above the target itself: even when cash is 1.66pp above the strategic target, only half is deployed per cycle — a natural glide path.

---

## No-Code DCA: Operator Policy vs. Architectural Change

There is an important distinction:

**Option A (no code change):** The operator manually decides to deploy only a portion of the recommended budget. The system shows $31.7K deployable; the operator chooses to execute $7.9K or $10K worth of trades.

**Options B/C/D (schedule change):** The system shows a monthly budget (1/3 or 1/6 of total deployable). Requires adding a `deployment_schedule` or `cycle_fraction` parameter to the deployment plan output.

**Option E (floor change):** The system's `MIN_CASH_PCT` (or a new `strategy_cash_target_pct` parameter) is set to 7.0%, so `compute_deployable_cash()` returns $7,894 instead of $31,683. This is the **cleanest architectural change** — the floor itself reflects the mandate philosophy.

**Option F (hybrid):** Combines Options E + a cycle fraction, adding a `max_deploy_fraction_per_cycle` parameter.

---

## Code Change Scope Analysis

| Model | Code Change | Complexity | Test Impact |
|-------|------------|-----------|-------------|
| A (current) | None | None | None |
| B (3-month) | Add `cycle_fraction=0.33` param to deployment plan | Low | Test assertions need update |
| C (6-month) | Add `cycle_fraction=0.17` param | Low | Test assertions need update |
| D (12-month) | Add `cycle_fraction=0.083` param | Low | Test assertions need update |
| E (target floor) | Add `strategy_floor_pct` param to `compute_deployable_cash()` | Medium | `test_min_cash_pct` at line 681 would need update |
| F (hybrid E+fraction) | Both above + `max_cycle_fraction` | Medium | Multiple test updates |

---

## Comparison Table

| Model | Monthly Deploy | Cash After 1 Cycle | Mandate Alignment | HHI Δ | Timing Risk |
|-------|---------------|-------------------|------------------|--------|------------|
| A — Immediate | $31,683 | **2.00%** | LOW | **+14.0** | High |
| B — 3-month | $10,561 | ~6.44% | Moderate | +4.9 | Medium |
| C — 6-month | $5,281 | ~7.55% | **Moderate-High** | +2.5 | Low-Medium |
| D — 12-month | $2,640 | ~8.10% | Moderate | +1.2 | Very Low |
| E — Target floor | $7,894 | **7.00%** | **HIGH** | +3.1 | Low |
| F — Hybrid | $3,947 | ~7.83% | **HIGH** | +1.6 | Very Low |

---

## Relationship to Phase 7.5W Simulation

The Phase 7.5W simulation modeled 12 cycles of $31,683/month (Model A, with fresh injection). Key result: the framework remains "ACCEPTABLE" for trust over 12 months — capital rotates, positions diversify, VRT gets blocked naturally.

However, that simulation was a DCA thought experiment — it assumed the operator **adds new capital monthly** rather than deploying existing cash all at once. The simulation result does not justify Model A for one-time deployment of $31.7K from existing cash, because:

1. The simulation's fresh injection keeps total MV growing (cash replenishes)
2. One-time deployment to 2% floor leaves no replenishment mechanism

Under Model E (target floor), the 12-month simulation would show:
- Monthly deployment: $7,894 (from accumulated excess)
- Cash would oscillate around 7% rather than declining to 2%
- VRT concentration warning would be delayed (smaller positions per cycle)
- More stable HHI trajectory

---

## Recommendation Preview

Model E (target-aligned deployment floor) is the architecturally cleanest solution. It:
1. Requires a single parameter change to `compute_deployable_cash()`
2. Naturally enforces the mandate's dry-powder philosophy without a separate DCA scheduler
3. Reduces HHI concentration pressure
4. Preserves meaningful liquidity at all times
5. Aligns the deployment engine with the allocation model's intent

See Q7 (governance recommendation) for the full verdict.
