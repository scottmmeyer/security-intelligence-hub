# Signal Governance Final Verdict — SIGNAL-GOV-01

**Date:** 2026-06-15  
**Review Status:** COMPLETE  
**Recommendation:** Advisory Phase — No Hard Gate

---

## Executive Summary

SIGNAL-GOV-01 evaluated whether minimum Zacks and/or Danelfin thresholds should be added as deployment gates for the CONCENTRATED_ALPHA mandate. The backtest analyzed 28 attribution records (27 with both Zacks and Danelfin) from June 10–11, 2026.

**Finding:** Current evidence does not support a hard exclusion gate. An advisory annotation system is warranted. Re-evaluation recommended at 100+ attribution records.

---

## Policy Scorecard

| Policy | Win Rate | Avg Return | Queue Pass | Recommendation |
|--------|---------|-----------|-----------|---------------|
| Z0 (no gate) | 92.6% | 20.93% | 10/10 | Current state |
| **Z2 (Zacks≥4)** | 88.2% | 10.78% | 8/10 | Advisory flag only — gate not justified |
| Z3 (Zacks≥5) | 80.0% | 11.80% | 2/10 | Reject — too restrictive |
| D1 (Dan≥5) | 91.7% | 19.56% | 10/10 | Insufficient filter |
| **D2 (Dan≥7)** | 100.0% | 35.42% | 6/10 | Advisory flag — gate premature |
| D3 (Dan≥8) | 100.0% | 100.0% (n=1) | 3/10 | Reject — overfitted |
| C1 (Z≥4 AND D≥7) | 100.0% | 14.51% | 4/10 | Phase 2 candidate, premature now |
| **C2 (Z≥4 OR D≥7)** | 90.5% | 21.44% | **10/10** | **RECOMMENDED: Phase 1 advisory** |
| C3 (Z≥5 AND D≥7) | 100.0% | 18.80% | 1/10 | Reject — too restrictive |
| C4 (Z≥4 AND D≥8) | — | — (n=0) | 2/10 | Reject — vacuous |

---

## Verdict by Question

| Question | Answer |
|----------|--------|
| Q1: Highest historical alpha? | D2 (35.42% avg return) — but limited to N=10, likely period effect |
| Q2: Highest win rate? | D2, C1, C3 all achieve 100% — by eliminating 2 NEUTRAL records |
| Q3: Most losers removed? | **Unanswerable** — no LOSER records exist in current dataset |
| Q4: Most winners removed? | Z3 removes 17/27 winners — most destructive policy |
| Q5: Zacks more predictive? | **No** — Zacks=3 symbols (PCB +12%, CAH +10.93%) were strong winners |
| Q6: Danelfin more predictive? | **Weakly yes** — Danelfin≥7 symbols had better average returns; Dan=5 symbols had 2 NUTRALs |
| Q7: Zacks≥4 hard gate justified? | **No** — removes confirmed winners, reduces portfolio quality metrics |
| Q8: Danelfin≥7 hard gate justified? | **Premature** — directional evidence exists but N=10 insufficient |
| Q9: Combined gate justified? | **C2 advisory only** — C1/C3/C4 too restrictive for current queue |
| Q10: Hard gate or ranking penalty? | **Advisory annotation** — ranking penalty at data maturity milestone |
| Q11: Configurable by mandate? | **Yes** — `allocation_policy.yaml:signal_governance` recommended |
| Q12: Recommended policy? | **C2 (Z≥4 OR D≥7) advisory with ZACKS_NEUTRAL / DANELFIN_WATCH annotations** |

---

## Decision

### Phase 1 (Now — <100 attribution records): Advisory

Implement visual annotations in the deployment queue UI:
- `ZACKS_NEUTRAL` badge on symbols with Zacks < 4.0
- `DANELFIN_WATCH` badge on symbols with Danelfin < 6.0
- No enforcement — operator may proceed at own discretion

**Current queue affected:**
- PCB (#5): `ZACKS_NEUTRAL` (Zacks=3.0, offset by Danelfin=7)
- MTZ (#8): `ZACKS_NEUTRAL` (Zacks=3.0, offset by Danelfin=9)
- No symbols blocked

### Phase 2 (At 100+ attribution records): Gate Evaluation

Re-run this backtest analysis. If D2 or C1 continues to outperform on a larger sample:
- Promote D2 from advisory to soft ranking penalty (−5 deployment score)
- Consider C1 as optional hard gate for concentrated mandates

### Phase 3 (Future — operator configurable)

Wire `signal_governance` config into the deployment queue ranker. Allow per-mandate configuration of minimum thresholds and enforcement level.

---

## Data Limitations Summary

1. **N=28** (one snapshot interval) — below statistical significance threshold
2. **Zero losers** — cannot validate loss prevention value of any gate
3. **ESS not available** in today's signal snapshot for attribution join
4. **All benchmark excess returns are 0.0%** — June 10→14 pricing issue
5. **Period effect risk** — June 10–11, 2026 was a uniformly strong return window; results may not generalize

---

## Governance Log

| Date | Action | Evidence | Outcome |
|------|--------|---------|--------|
| 2026-06-15 | Backtest executed | 28 attribution records, 27 with Zacks/Danelfin | No hard gate warranted |
| 2026-06-15 | Advisory annotations designed | PCB, MTZ flagged ZACKS_NEUTRAL | No deployment change |
| 2026-06-15 | Milestone set | Re-evaluate at 100+ records | Future item |

---

## Next Actions

| Priority | Action | Owner |
|----------|--------|-------|
| MEDIUM | Add `ZACKS_NEUTRAL` / `DANELFIN_WATCH` badges to deployment queue UI | Engineering |
| MEDIUM | Add `signal_governance` config section to `allocation_policy.yaml` | Engineering |
| LOW | Build signal governance enforcement layer in deployment queue ranker | Engineering |
| LOW | Re-run backtest when attribution records reach 100+ | Analyst |
| INFO | SIGNAL-GOV-01 complete | — |
