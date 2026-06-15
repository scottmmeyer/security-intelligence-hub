# AI-006 Signal Reconciliation

**Date:** 2026-06-15

---

## Composite Score Formula

**Source:** `src/history/analytical_universe_manager.py:_score_from_inputs()`

```
composite_score = weighted_average(
    ESS       × 0.55,   # StarMine ESS text → 5.0/4.0/3.0/2.0/1.0
    Zacks     × 0.25,   # Numeric score 1.0-5.0
    Yahoo ABR × 0.10,   # Numeric score
    Danelfin  × 0.10    # Numeric score 1.0-5.0 (danelfin_raw / 2.0)
)
```

Missing signals are excluded from both numerator AND denominator (not zeroed out). This prevents penalizing symbols that lack coverage.

---

## Q8: Does CW-DAS Use Danelfin in Ranking?

**YES — Danelfin contributes 10% of composite_score, which drives deployment ranking.**

Evidence:
- `analytical_universe_manager.py:610` — `composite_score=_score_from_inputs(ess, zacks, ess_zacks, yahoo, danelfin_score)`
- `_score_from_inputs` assigns Danelfin weight 0.10
- `unified_conviction.py:401` — `signal_component = (comp / 5.0) * 100.0` — composite directly drives UCF signal score
- UCF signal score is 1/4 of deployment_score (alongside replay, conviction, sizing)

**Danelfin is NOT display-only at the composite level.** It affects the composite_score which in turn affects deployment ranking.

---

## Q9: CAH vs NUE — Full Decomposition

### Current Composite Scores

| Symbol | ESS (55%) | Zacks (25%) | Danelfin (10%) | Yahoo | Composite | Deploy Score | Rank |
|--------|-----------|-------------|----------------|-------|-----------|-------------|------|
| CAH | VERY_BULLISH (5.0) | 4.0 | **2.5** | — | **4.4444** | 92.44 | #6 |
| NUE | BULLISH (4.0) | **5.0** | 3.5 | — | **4.2222** | 91.24 | #10 |
| SANM | BULLISH (4.0) | 4.0 | **4.0** | — | 4.0000 | 92.13 | #7 |
| MTZ | BULLISH (4.0) | 3.0 | **4.5** | — | 3.7778 | 91.36 | #8 |

### Key Observation: Danelfin HURTS CAH, HELPS MTZ/SANM

- **CAH**: Danelfin=2.5 (5/10) drags down an otherwise strong ESS+Zacks composite. Without Danelfin: 4.6875. With: 4.4444.
- **NUE**: Danelfin=3.5 (7/10) adds minor lift. Without: 4.3125. With: 4.2222. 
- **MTZ**: Danelfin=4.5 (9/10) significantly boosts a weak Zacks=3.0 composite. Without: 3.5556. With: 3.7778.
- **SANM**: Danelfin=4.0 (8/10) adds meaningful lift. Without: 3.7778. With: 4.0000.

### CAH still ranks above NUE with or without Danelfin

| Scenario | CAH | NUE | CAH > NUE? |
|---------|-----|-----|-----------|
| With Danelfin | 4.4444 | 4.2222 | **YES** |
| Without Danelfin | 4.6875 | 4.3125 | **YES** |

**CAH outranks NUE because ESS VERY_BULLISH (5.0 × 0.55 = 2.75) dominates** over NUE's Zacks advantage (5.0 × 0.25 = 1.25 vs CAH's 4.0 × 0.25 = 1.00). The ESS weight advantage (+0.75) far exceeds NUE's Zacks advantage (+0.25 × 0.25 = +0.0625 contribution).

### Why NUE Ranks Lower Despite Stronger Zacks

NUE has:
- ESS BULLISH (4.0) vs CAH's VERY_BULLISH (5.0): -1.0 ESS points × 0.55 = **-0.55 composite disadvantage**
- Zacks 5.0 vs CAH's 4.0: +1.0 Zacks points × 0.25 = **+0.25 composite advantage**

Net: NUE is -0.30 composite vs CAH from ESS/Zacks alone. This is working as designed — ESS is the primary signal.

---

## Full Deployment Queue Score Breakdown

| Symbol | Signal | Replay | Conviction | Sizing | Momentum | Fund.Modifier | Deploy |
|--------|--------|--------|-----------|--------|----------|--------------|--------|
| VRT #1 | 27.33 | 20.0 | **35.0** | 1.49 | 10.0 | 3.0 | 96.82 |
| ATLC #2 | 27.0 | 20.0 | 28.0 | 6.55 | 10.0 | 3.0 | 94.55 |
| DELL #3 | 28.33 | 20.0 | 28.0 | 6.09 | 10.0 | 2.0 | 94.43 |
| LRCX #4 | 27.0 | 20.0 | 28.0 | 6.30 | 10.0 | 3.0 | 94.30 |
| PCB #5 | 26.0 | 20.0 | 28.0 | 6.57 | 10.0 | 2.0 | 92.57 |
| CAH #6 | 26.67 | 20.0 | 28.0 | 6.27 | 10.0 | 1.5 | 92.44 |
| SANM #7 | 24.0 | 20.0 | 28.0 | 7.13 | 10.0 | **3.0** | 92.13 |
| MTZ #8 | 22.67 | 20.0 | 28.0 | 7.69 | 10.0 | **3.0** | 91.36 |
| CRS #9 | 24.0 | 20.0 | 28.0 | 7.85 | 10.0 | 1.5 | 91.35 |
| NUE #10 | 25.33 | 20.0 | 28.0 | 6.91 | 10.0 | **1.0** | 91.24 |

**Key driver of NUE ranking 10th:** `fundamental_modifier=1.0` (lowest of all) pulls its deploy score down vs MTZ (3.0) and SANM (3.0). NUE's `thesis_integrity=INTACT` but `fundamental_consistency=CONSISTENT` — the modifier is based on FMP fundamental data quality. NUE's lower fundamental_modifier is the primary drag, not Danelfin.
