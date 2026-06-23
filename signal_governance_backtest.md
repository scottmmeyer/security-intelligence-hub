# Signal Governance Backtest — SIGNAL-GOV-01

**Date:** 2026-06-15  
**Dataset:** 28 attribution records, 27 with Zacks, 27 with Danelfin  
**Period:** June 10–11, 2026 (single snapshot interval)

---

## Critical Context: Data Limitations

- **N=27** recommendation-attribution pairs — insufficient for statistical significance
- **Zero LOSER records** — 92.6% win rate means every exclusion policy removes only Winners
- **ESS unavailable in backtest** — signal_snapshot today contains only non-StarMine Zacks data
- **Benchmark excess return = 0.0%** — June 10→11 benchmark return was 1.70% but the PIS interval used June 11→14 (Sunday) which shows 0% benchmark (same-day pricing issue from forensic audit)
- **These results are directionally informative, not statistically conclusive**

---

## Zacks Policy Results

| Policy | Condition | N | Win Rate | Avg Return | Total Attribution | Excluded | Excl Winners | Excl Losers |
|--------|-----------|---|---------|-----------|------------------|---------|-------------|------------|
| Z0 | No gate | 27 | **92.6%** | **20.93%** | $42,158 | 0 | 0 | 0 |
| Z1 | Zacks≥3 | 27 | 92.6% | 20.93% | $42,158 | 0 | 0 | 0 |
| Z2 | Zacks≥4 | 17 | 88.2% | 10.78% | $15,626 | 10 | **10** | 0 |
| Z3 | Zacks≥5 | 10 | 80.0% | 11.80% | $8,507 | 17 | 17 | 0 |

**Z2 finding:** Removes 10 winners, 0 losers. Win rate DECREASES from 92.6% → 88.2%. Avg return DECREASES 20.93% → 10.78%.

**Z3 finding:** Even more restrictive — only 10 records, win rate drops to 80%. All excluded records were winners.

**Interpretation:** Zacks tightening HURTS outcomes in this dataset because: (a) all records were winners, (b) the symbols with Zacks=3.0 (CAH, PCB, SNX) were among the strongest performers — CAH returned 10.93% and 4.26%.

---

## Danelfin Policy Results

| Policy | Condition | N | Win Rate | Avg Return | Total Attribution | Excluded | Excl Winners | Excl Losers |
|--------|-----------|---|---------|-----------|------------------|---------|-------------|------------|
| D0 | No gate | 27 | 92.6% | 20.93% | $42,158 | 0 | 0 | 0 |
| D1 | Dan≥5 | 24 | 91.7% | 19.56% | $21,531 | 3 | 3 | 0 |
| **D2** | **Dan≥7** | **10** | **100.0%** | **35.42%** | **$16,407** | 17 | 15 | 0 |
| D3 | Dan≥8 | 1 | 100.0% | 100.00% | $3,492 | 26 | 24 | 0 |

**D2 finding:** Danelfin≥7 selects 10 records with **100% win rate** and **35.42% average return** — significantly better than the baseline 20.93%. However, this comes at high cost: 15 winners are excluded, representing $25,751 in attribution.

**D3 finding:** Only 1 record (VEA EXITED at 100% return — a legitimate exit recommendation). Overly restrictive.

**Critical insight:** The D2 improvement is partially driven by selection bias — Danelfin 7-10 symbols happened to be the strongest performers in this short period. This does not necessarily hold over a longer horizon.

---

## Combined Policy Results

| Policy | Condition | N | Win Rate | Avg Return | Total Attribution | Excluded | Excl Winners | Excl Losers |
|--------|-----------|---|---------|-----------|------------------|---------|-------------|------------|
| C0 | No gate | 27 | 92.6% | 20.93% | $42,158 | 0 | 0 | 0 |
| C1 | Z≥4 AND D≥7 | 6 | **100.0%** | **14.51%** | $8,417 | 21 | 19 | 0 |
| **C2** | **Z≥4 OR D≥7** | **21** | **90.5%** | **21.44%** | **$23,616** | 6 | 6 | 0 |
| C3 | Z≥5 AND D≥7 | 3 | 100.0% | 18.80% | $2,868 | 24 | 22 | 0 |
| C4 | Z≥4 AND D≥8 | 0 | — | — | $0 | 27 | 25 | 0 |

**C2 (OR gate) finding:** Most balanced policy — excludes only 6 records, all winners, slight win rate decrease (90.5%) but slightly higher avg return (21.44%). The OR gate preserves the most deployment opportunities while still providing some quality filter.

---

## Key Backtest Finding: No Policy Removes Losers

Because there are no LOSER records in the current attribution dataset (only 28 records, all strong performers from June 10–11), **every exclusion policy exclusively removes winners.** This is a fundamental data limitation.

The backtest cannot answer "does the gate eliminate bad deployments" because there were no bad deployments in this period.

---

## Symbol-Level Backtest Detail (DEPLOYMENT_QUEUE only)

| Symbol | Zacks | Danelfin | Outcome | Return | Excluded by |
|--------|-------|---------|---------|--------|------------|
| ARW (3 entries) | 5.0 | 7.0 | WINNER×3 | 29.65%, 15.58%, 11.18% | Z3 only |
| ATLC | 5.0 | 6.0 | WINNER | 18.49% | Z3, D2, C1, C3 |
| VRT (3 entries) | 4.0 | 7.0 | WINNER×3 | 17.40%, 8.80%, 4.47% | Z3 only |
| AVT (2 entries) | 4.0 | 6.0 | WINNER×2 | 14.09%, 3.76% | Z3, D2, C1, C3 |
| PSX (2 entries) | 5.0 | 6.0 | WINNER×2 | 13.30%, 11.46% | Z3, D2, C1, C3 |
| LRCX (2 entries) | 4.0 | 6.0 | WINNER×2 | 12.30%, 4.40% | Z3, D2, C1, C3 |
| PCB | 3.0 | 7.0 | WINNER | 12.03% | Z2, Z3 |
| CAH (2 entries) | 3.0 | 5.0 | WINNER×2 | 10.93%, 4.26% | Z2, Z3, D2, D3, C1, C3 |
| SNX (2 entries) | 3.0 | 6.0 | WINNER×2 | 9.94%, 5.25% | Z2, Z3 |
| DELL (2 entries) | 5.0 | 5.0 | WINNER+NEUTRAL | 6.49%, -0.12% | D2, D3, C1, C3, C4 |
| CBOE | 5.0 | 5.0 | NEUTRAL | 0.72% | D2, D3, C1, C3, C4 |

---

## Important Observation: PCB and CAH Are WINNERS Despite Zacks=3

PCB (Zacks=3.0, Danelfin=7.0) returned **+12.03%** — a clear WINNER.  
CAH (Zacks=3.0, Danelfin=5.0) returned **+10.93% and +4.26%** — both WINNERs.  

This directly contradicts the premise that Zacks=3.0 (NEUTRAL) signals poor deployment outcomes. In the current dataset, these were strong performers.
