# AI-006 Final Verdict

**Date:** 2026-06-15

---

## Q1. What is CAH's actual Danelfin score?

**Danelfin raw: 5/10 → normalized score: 2.5/5.0** (sourced 2026-06-15)  
Interpretation: NEUTRAL on the Danelfin AI scale. CAH's strong position is driven by VERY_BULLISH ESS, not Danelfin.

## Q2. What is NUE's actual Danelfin score?

**Danelfin raw: 7/10 → normalized score: 3.5/5.0** (sourced 2026-06-15)  
Interpretation: Mildly BULLISH. NUE has a stronger Danelfin signal than CAH but weaker ESS.

## Q3. What is SANM's actual Danelfin score?

**Danelfin raw: 8/10 → normalized score: 4.0/5.0** (sourced 2026-06-15)  
Interpretation: BULLISH on Danelfin. Strong signal that partially compensates for BULLISH (not VERY_BULLISH) ESS.

## Q4. What is MTZ's actual Danelfin score?

**Danelfin raw: 9/10 → normalized score: 4.5/5.0** (sourced 2026-06-15)  
Interpretation: **Strongest Danelfin in the queue.** Partially offsets MTZ's weak Zacks=3.0 (NEUTRAL).

## Q5. Are Danelfin scores present across all required stores?

**YES** — confirmed in latest_danelfin.csv (2,661 symbols), security_overlays.csv (all 10 DQ candidates), API payload, and UI rendering paths. Not present in `fidelity_signals_by_symbol` (by design — that payload covers only ESS/Zacks/Yahoo).

## Q6. Are Danelfin values rendered in every deployment candidate card?

**YES** — confirmed 8 rendering paths in `ui/portfolio_alignment/app.js`, all reading `ov.danelfin_score`. The operator observation of "missing Danelfin" may reflect viewing an older PAR run or a symbol without Danelfin coverage. No UI bug exists.

## Q7. If Danelfin is missing from any card: root cause?

**No systemic bug.** Two conditions can produce blank display: (1) symbol not covered by Danelfin (international/EM), (2) viewing a PAR predating today's Danelfin fetch. The current data is fresh for all top-10 candidates.

## Q8. Does CW-DAS currently use Danelfin in ranking?

**YES — Danelfin is scoring-active at 10% weight in composite_score.**  
Evidence: `analytical_universe_manager.py:_score_from_inputs()` assigns `(danelfin_val, 0.10)` to the weighted average. This composite then drives UCF signal score → deployment_score → queue rank. Danelfin is NOT display-only.

## Q9. Would CAH still rank above NUE if Danelfin were ignored?

**YES.** CAH composite without Danelfin = 4.6875; NUE = 4.3125. The ESS VERY_BULLISH (5.0 × 0.55 = 2.75) advantage for CAH exceeds NUE's Zacks 5.0 advantage (1.25 vs 1.00 = +0.25 raw). ESS dominance is structural and correct.

## Q10. Would a Zacks minimum gate alter current rankings?

- **Option A (Zacks>=3):** No change. All 10 candidates pass.
- **Option B (Zacks>=4):** PCB (#5) and MTZ (#8) excluded. 8 candidates remain.
- **Option C (Zacks>=5):** 8 of 10 excluded. Only DELL and NUE remain. Too restrictive.

## Q11. Can ESS-bullish, Zacks-neutral securities be recommended for deployment?

**YES — by design.** PCB (VERY_BULLISH ESS, Zacks=3.0, rank #5) and MTZ (BULLISH ESS, Zacks=3.0, rank #8) qualify. The formula intentionally weights ESS at 55%, allowing high-conviction ESS names to deploy without Zacks confirmation. This is consistent with the CONCENTRATED_ALPHA mandate philosophy. **Not a governance gap — an operator awareness item.**

---

## Recommended Disposition

### AI-006 should become: **Documentation + Governance Enhancement (Optional)**

| Component | Disposition | Priority |
|-----------|------------|--------|
| Danelfin display visibility | **Documentation only** — already fully working | — |
| Composite score formula transparency | **Documentation only** — explain 55/25/10/10 split in operator guide | LOW |
| Zacks governance gate (Option B) | **Governance Enhancement (Optional)** — PCB and MTZ would be excluded | MEDIUM |
| ESS-without-Zacks deployment | **Documentation only** — operator awareness, not a bug | — |
| Danelfin in fidelity_signals_by_symbol | **Not needed** — overlays is the correct source | — |

### Specific Follow-Up Issues

1. **Create a governance issue** to formally evaluate whether a Zacks >= 4 minimum should be implemented for deployment eligibility. This is a policy decision, not a bug fix. The two affected symbols are PCB (#5) and MTZ (#8).

2. **No code changes are required** based on this audit. All signals are present, correctly scored, and correctly displayed.

3. **Operator guidance:** Annotate PCB and MTZ in the deployment queue view with "Zacks NEUTRAL" warning badges to support informed sizing decisions. This can be implemented as a low-priority UI enhancement.

---

## Final Summary

| Issue | Finding |
|-------|---------|
| Danelfin missing from cards | FALSE — fully populated and rendered |
| CAH > NUE ranking anomaly | CORRECT — ESS weight drives it; expected behavior |
| Danelfin affecting rankings | TRUE — 10% composite weight, not display-only |
| PCB/MTZ with Zacks NEUTRAL | BY DESIGN — not a bug |
| Code changes required | NONE |
| Governance enhancement warranted | OPTIONAL — Zacks>=4 gate for deployment |
