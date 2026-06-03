# Q4 — Cash Floor Scenario Analysis
## Phase 22D.5 — What happens under different deployment floor assumptions?

**Investigation run:** PAR-20260602-1BF2ADA5  
**Generated:** Phase 22D.5  
**Portfolio MV:** $475,779.42  
**Cash MV:** $41,198.92 (8.6592%)  

---

## Setup

The current portfolio holds 8.66% cash ($41,199). The deployment engine uses a 2.0% floor, making $31,683 (6.66%) deployable. The strategic mandate target is 7.0%.

This analysis models four deployment floor scenarios: what would change if the floor were set at 2%, 5%, 7%, or 10%?

---

## Scenario Results

| Scenario | Floor | Floor MV | Deployable | Deploy% | Cash After | HHI Before | HHI After | ΔHHI |
|----------|-------|----------|-----------|---------|------------|-----------|-----------|------|
| A — Current (2%) | 2.0% | $9,516 | **$31,683** | 6.66% | **2.00%** | 223.21 | 237.19 | **+13.98** |
| B — Moderate (5%) | 5.0% | $23,789 | $17,410 | 3.66% | 5.00% | 223.21 | 230.35 | +7.13 |
| C — Aligned (7%) | 7.0% | $33,305 | $7,894 | 1.66% | **7.00%** | 223.21 | 226.28 | +3.07 |
| D — Strategic (10%) | 10.0% | $47,578 | **$0** | 0.00% | 8.66% | 223.21 | 223.21 | **0.00** |

*HHI is computed as equity positions weighted by (MV/total_MV×100)². Lower is more diversified. New deployable funds distributed proportionally across top-20 queue items by deployment score.*

---

## Scenario A — Current (Floor = 2%)

**Current behavior.**

- Deployable: **$31,683** — 77% of the total cash position
- Cash after deployment: **2.00%** — at the absolute governance floor
- HHI change: **+13.98** — most concentrated outcome
- Post-deployment cash: $9,516 — provides minimal liquidity buffer above transaction costs
- Mandate alignment: **NO** — puts cash 5.0pp below the 7.0% strategic target

**Assessment:** Maximizes capital deployment velocity. Operationally aggressive. If all 42 queue candidates are used, average allocation per position ≈ $754. Leaves virtually no tactical cash reserve for opportunistic buying. Contradicts the "dry powder" mandate philosophy.

---

## Scenario B — Moderate (Floor = 5%)

**Intermediate option: maintain meaningful liquidity while deploying excess.**

- Deployable: **$17,410** — 42% of the total cash position
- Cash after deployment: **5.00%** — above governance floor, below strategic target
- HHI change: **+7.13** — moderate concentration increase
- Post-deployment cash: $23,789 — maintains a meaningful liquidity buffer

**Assessment:** Splits the difference between deploying capital and preserving optionality. Post-deployment cash of 5% provides ~$23.8K of tactical reserve. Still 2.0pp below the 7% strategic target. Reduces HHI increase by ~49% vs Scenario A.

---

## Scenario C — Aligned (Floor = 7%)

**Deploys only the excess above the strategic mandate target.**

- Deployable: **$7,894** — 19% of the total cash position
- Cash after deployment: **7.00%** — exactly at the strategic target
- HHI change: **+3.07** — minimal concentration increase
- Post-deployment cash: $33,305 — maintains full dry powder reserve

**Assessment:** This is what the strategic mandate actually calls for. Post-deployment, the portfolio sits at exactly 7.0% cash — aligned with the CONCENTRATED_ALPHA philosophy. The deployable $7,894 is more selective (fewer positions funded) but each allocation preserves mandate integrity. HHI increase is 78% smaller than Scenario A.

**Example execution:** $7,894 distributed across top-5 queue positions would give ~$1,579/position average — more selective than Scenario A's $754 average across 42 positions.

---

## Scenario D — Strategic Floor (Floor = 10%)

**No deployment — current cash is already below the proposed floor.**

- Deployable: **$0** — cash MV ($41,199) < floor MV ($47,578)
- Cash after deployment: **8.66%** — no change
- HHI change: **0.00** — no change

**Assessment:** With cash at 8.66% and a 10% floor, there is nothing to deploy. This scenario is informational: it shows that only 1.34pp separates the current cash position from a 10% strategic reserve. If the mandate intent is a 10% dry powder buffer, the portfolio is already within range and no deployment should occur.

---

## Concentration Risk Analysis

The HHI metric captures deployment's concentration effect:

```
Scenario A:  +13.98 HHI points  (most concentrated)
Scenario B:  +7.13  HHI points  (moderate)
Scenario C:  +3.07  HHI points  (conservative)
Scenario D:  +0.00  HHI points  (no deployment)
```

At baseline HHI = 223.21, the typical CONCENTRATED_ALPHA operating range is 200–300. All scenarios keep HHI within this range. None trigger a concentration red flag. The HHI difference between scenarios is real but not alarm-level.

---

## What the 12-Month Simulation Reveals

From `data/analysis/phase_7_5w/operator_trust_assessment.md`:

The Phase 7.5W simulation models 12 consecutive monthly deployments of **$31,683** (Scenario A assumption, with a fresh cash injection each cycle). Results:
- Month 1: HHI = 0.0298 (reporting scale differs)
- Month 12: HHI = 0.0618
- VRT hits WARN threshold in months 4–12

This simulation was a **DCA modeling exercise** — it assumed the operator injects fresh capital monthly. It does not model one-time depletion of existing cash from 8.66% to 2.00%.

If Scenario A is executed once (8.66% → 2.00%), the portfolio needs to accumulate ~$24K in new cash inflows to return to 7% target — which at no explicit savings rate, could take many months. During that time, the portfolio has no tactical dry powder reserve.

---

## Summary of Recommendation

| Goal | Best Scenario |
|------|--------------|
| Maximum capital deployment velocity | **A (2% floor)** |
| Maintain operational liquidity | **B (5% floor)** |
| Match CONCENTRATED_ALPHA mandate intent | **C (7% floor)** |
| Preserve maximum optionality | **D (10% floor)** |

The choice depends on which question the operator is trying to answer:
- "I want to deploy this cash now and rebuild over time" → Scenario A or B
- "I want to deploy only the genuine excess above my target reserve" → Scenario C
- "I'm happy with my current cash level" → Scenario D (deploy nothing)

---

## Full Data

See [cash_floor_scenario_analysis.csv](./cash_floor_scenario_analysis.csv) for the full numeric table.
