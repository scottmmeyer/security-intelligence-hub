# Signal Governance Design — SIGNAL-GOV-01

**Date:** 2026-06-15  
**Status:** Design + Backtest Analysis

---

## Current Scoring Architecture

```
composite_score = (ESS × 0.55 + Zacks × 0.25 + Yahoo × 0.10 + Danelfin × 0.10)
                  / total_available_weight
```

**Signal weights:**
- ESS (StarMine): 55% — primary signal
- Zacks: 25%
- Yahoo ABR: 10%
- Danelfin: 10%

**No minimum quality thresholds currently exist.** A VERY_BULLISH ESS symbol with Zacks=3.0 (NEUTRAL) can enter the deployment queue because ESS (55%) dominates.

---

## Design Objective

Evaluate whether adding minimum thresholds on Zacks and/or Danelfin before deployment eligibility improves:
- Win rate
- Average return
- Benchmark excess return
- Total directional attribution

**Constraint:** No scoring changes. No CW-DAS changes. Evidence-only phase.

---

## Policy Taxonomy

### Zacks Policies (1–5 scale, higher = more bullish)

| Policy | Condition | Rationale |
|--------|-----------|---------|
| Z0 | No gate (current) | Baseline |
| Z1 | Zacks ≥ 3 | Exclude bearish Zacks only |
| Z2 | Zacks ≥ 4 | Require at least BUY posture |
| Z3 | Zacks ≥ 5 | Require STRONG BUY only |

### Danelfin Policies (1–10 raw scale)

| Policy | Condition | Rationale |
|--------|-----------|---------|
| D0 | No gate (current) | Baseline |
| D1 | Danelfin ≥ 5 | Exclude below-average scores |
| D2 | Danelfin ≥ 7 | Require solidly bullish AI score |
| D3 | Danelfin ≥ 8 | Require strong AI conviction |

### Combined Policies

| Policy | Condition | Rationale |
|--------|-----------|---------|
| C1 | Zacks ≥ 4 AND Danelfin ≥ 7 | Both signals must confirm |
| C2 | Zacks ≥ 4 OR Danelfin ≥ 7 | Either signal confirms |
| C3 | Zacks ≥ 5 AND Danelfin ≥ 7 | Both signals must be strong |
| C4 | Zacks ≥ 4 AND Danelfin ≥ 8 | Zacks BUY + strong Danelfin |

---

## Data Limitations

The attribution dataset covers **28 records over 1 snapshot interval (June 10–11, 2026)**. This is insufficient for full statistical significance. Key findings:

1. **No LOSER records exist in the current attribution history.** Win rate is 92.6% (26/28 WINNER, 2/28 NEUTRAL) across all 27 records with signal data.
2. **ESS is unavailable** in today's signal_snapshot (non-StarMine only) — ESS is thus tracked via PAR-level data.
3. **Benchmark excess returns are 0.0%** for the benchmark comparison period (2026-06-14 was a Sunday — both entry and exit prices are 2026-06-11, benchmark_return=0).
4. **All Z0 exclusions remove only WINNER records** — there are no Losers to remove.

These limitations mean the backtest is directionally informative but not statistically conclusive. The analysis documents what the data shows while noting these constraints.

---

## Governance Gate Design Options

### Option 1: Hard Exclusion Gate
Symbols failing the threshold are removed from the deployment queue entirely.  
**Pro:** Simple, deterministic, auditable  
**Con:** Binary; may exclude high-conviction ESS names with neutral secondary signals

### Option 2: Ranking Penalty
Symbols failing the threshold receive a score penalty (e.g., −5 to deployment_score).  
**Pro:** Preserves optionality; doesn't hard-block  
**Con:** Less visible to operator; may reduce transparency

### Option 3: Advisory Warning + Mandatory Annotation
Symbols failing threshold are flagged visually in the deployment queue with "ZACKS NEUTRAL" badge.  
**Pro:** Maximum operator visibility without automation  
**Con:** Relies on operator action; not a governance enforcement

### Recommendation: Option 3 (Advisory) for Phase 1, Option 1 (Hard Gate) for Phase 2 (Z2 only)

The data supports an advisory warning in the current deployment queue for PCB and MTZ (Zacks=3.0). A hard gate at Z2 (Zacks≥4) is defensible for future implementation but should wait for a larger attribution dataset.
