# Phase 7.5W — Deployment Simulation Final Verdict

## Study Summary

**Framework under test:** CW-DAS (Conviction-Weighted Deployment Allocation Score)
**Baseline portfolio:** PAR-20260602-1BF2ADA5 ($475,779.42 total MV, $31,683.33 deployable)
**Simulation method:** Static signals / static prices / dynamic position weights
**Cycles run:** Q5 = 8 cycles, Q9 = 12 cycles (fresh $31,683/cycle)

## Question-by-Question Evidence

1. Q5: Rank #1 dominated by VRT in 7/8 cycles (+2 concentration pts)
2. Q7: VRT correctly excluded from plan after WARN-threshold fill (+0)
3. Q9: Top-3 allocation share averaged 22.0% — distributed (+0)
4. Q9: VRT blocked in 9/12 months — WARN mechanism working as designed (mitigating)

**Raw concentration score: 1**

---

## Verdict: A. FRAMEWORK_CONVERGES_CORRECTLY

The CW-DAS framework demonstrates effective self-correction. As positions accumulate capital, the sizing penalty and concentration penalty naturally demote saturated positions and elevate fresh candidates. An operator faithfully executing recommendations will build a diversified portfolio without disproportionate concentration in any single holding.

## Key Structural Findings

1. **Sizing_c decay** (0–8 pts, linear): Effective gradual penalty but only 8 pts of range vs 35 pts conviction for CCL positions. CCL symbols retain large score leads even near WARN.

2. **CCL tier compound advantage**: CCL symbols receive both +7 scoring bonus (35 vs 28 conviction_c) AND +40% planner weight multiplier (1.75× vs 1.25×). This creates a 2-layer structural advantage.

3. **WARN mechanism** (sizing_c → 0 at 6%): Correctly prevents any single position from absorbing all available capital. Positions above 6% are automatically deprioritized via both sizing_c=0 and conc_pen.

4. **CCL symbols in portfolio**: ['VRT', 'CVE', 'TSM', 'GTX', 'MU']

5. **Max possible score decay for a CCL position from 0% → WARN%**: 8 pts (sizing_c) + 0 pts (no conc_pen below 6%) = 8 pts lost on 95-pt score = ~8.4% reduction.

## Operator Guidance

The framework is **designed to concentrate** capital in conviction leaders — this is the intended behavior. The WARN threshold (6%) provides a natural ceiling. The simulation question is whether the rotation AFTER saturation is clean.

**Recommendation: PROCEED with confidence.** The framework rotates capital naturally after saturation. Monitor VRT's position weight as a leading indicator — when it approaches 5.5%, expect the framework to begin routing capital to the next tier of HCA candidates.

## Deliverables Index

| File | Question |
|------|---------|
| deployment_simulation_baseline.csv | Q1: Baseline top-20 queue snapshot |
| single_trade_saturation_report.md | Q2: Single VRT trade impact |
| top3_execution_simulation.md | Q3: Top-3 execution analysis |
| full_plan_execution_report.md | Q4: Full plan execution |
| iterative_convergence_analysis.md | Q5: 8-cycle convergence |
| vrt_saturation_curve.csv | Q6: VRT score vs weight% |
| capital_rotation_analysis.md | Q7: Post-saturation rotation |
| framework_stability_assessment.md | Q8: Scoring stability |
| operator_trust_assessment.md | Q9: 12-month trust simulation |
| deployment_simulation_final_verdict.md | Final verdict |