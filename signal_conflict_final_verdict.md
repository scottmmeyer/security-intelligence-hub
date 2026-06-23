# Signal Conflict Final Verdict — SIGNAL-GOV-02

**Date:** 2026-06-15  
**Review Status:** COMPLETE  
**Recommendation:** Advisory Badges Only — No Gate

---

## Executive Summary

SIGNAL-GOV-02 evaluated whether analyst conflict signals (explicit sell recommendations, HOLD consensus, source disagreement) should influence deployment governance for the CONCENTRATED_ALPHA mandate.

**Finding:** Current evidence does not support deployment restrictions based on conflict levels. Advisory visibility annotations are strongly warranted. No ranking penalties or gates are justified at N=28.

The operator instinct — "I don't want to deploy when sources say SELL" — is philosophically valid but empirically challenged: the best performer in attribution history (ARW, +29.65%) had 2 explicit sell votes. The composite ESS signal (55%) already aggregates and discounts minority bearish views.

---

## Data Architecture Finding

**Named source opinions (Refinitiv/Verus, Trading Central, ISS-EVA, Argus) are not available as separate SIH data fields.** These are sub-providers within the LSEG StarMine ESS score. Their individual opinions feed the ESS composite but cannot be isolated programmatically. The only separately-available aggregate is FMP Street consensus (buy_count, sell_count, etc.).

**Action Item:** If the operator wants named-source conflict detection (NUE/Trading Central case), it requires either:
1. Direct ESS export with provider columns (Jefferson Research, McLean, Zacks columns are present)
2. Manual operator annotation for known disagreements

---

## Backtest Summary

| Conflict Level | N | Win Rate | Avg Return | Status |
|---------------|---|---------|-----------|--------|
| L0 Full Alignment | 6 | 100% | 9.4% | Baseline |
| L1 Mild (HOLD consensus) | 1 | 100% | 12.0% | Small sample |
| L2 Moderate (1+ sell votes) | 14 | 85.7% | **15.0%** | Higher avg return than L0 |
| L3 Significant | 0 in history | — | — | Cannot evaluate |
| L4 Severe | 0 in history | — | — | Cannot evaluate |

**The backtest does not support conflict-level-based gates.**

---

## Final Answer Table

| Q | Question | Answer |
|---|----------|--------|
| Q1 | How many historical recs had bearish signals? | **14 of 28** (50%) had ≥1 sell vote |
| Q2 | Did those outperform or underperform? | **Slightly outperformed** (15.0% vs 9.4% avg return) |
| Q3 | Which sources most frequently disagreed? | **FMP Street (unresolved)** — AVT, CBOE, ARW highest sell proportions |
| Q4 | Does disagreement predict weaker outcomes? | **No** — no evidence in current data |
| Q5 | Does disagreement predict stronger outcomes? | **No** — higher avg return for L2 is ARW-driven, not systematic |
| Q6 | Surface conflict in UI? | **YES** — strongly recommended |
| Q7 | Affect ranking? | **No** — no empirical basis |
| Q8 | Affect deployment eligibility? | **No for L1/L2; L3 advisory review is reasonable** |
| Q9 | NUE ranked appropriately despite disagreement? | **Yes** — #10 is appropriate; flag with `HIGH_ANALYST_DISAGREEMENT` |
| Q10 | Which governance option recommended? | **Option B (badges) + Option C for L3 holdings (review)** |
| Q11 | Implementation recommended? | **Yes — advisory badges only** |

---

## Current Portfolio Conflict Summary

### Deployment Queue
| Symbol | Rank | Conflict | Action |
|--------|------|---------|--------|
| VRT | #1 | **L0** Full Alignment | None |
| ATLC | #2 | **L0** Full Alignment | None |
| DELL | #3 | L2 (2 sells/45) | `CONFLICTING_SIGNAL` badge |
| LRCX | #4 | L2 (1 sell/50) | `CONFLICTING_SIGNAL` badge |
| PCB | #5 | L1 (HOLD consensus) | `HOLD_CONSENSUS` badge |
| CAH | #6 | L1 (45% holds) | `HIGH_HOLD_RATIO` badge |
| SANM | #7 | L2 (2 sells/17, 11.8%) | `CONFLICTING_SIGNAL` badge |
| MTZ | #8 | **L0** Full Alignment | None |
| CRS | #9 | L2 (1 sell/21) | `CONFLICTING_SIGNAL` badge |
| NUE | #10 | L2 (3 sells/32) + L4 candidate | `HIGH_ANALYST_DISAGREEMENT` badge |

### Holdings Requiring Attention (L3)
| Symbol | Conflict | Sell% | Action |
|--------|---------|-------|--------|
| **TSLA** | L3 SIGNIFICANT | 18.5% (15/81) | `SIGNIFICANT_CONFLICT` badge; operator review before new capital |
| **AVT** | L3 SIGNIFICANT | 20.0% (4/20) | `SIGNIFICANT_CONFLICT` badge |
| **GTX** | L3 SIGNIFICANT | 25.0% (2/8) + HOLD consensus | `SIGNIFICANT_CONFLICT` badge |

### Special Case
| Symbol | Issue | Resolution |
|--------|-------|-----------|
| **NUE** | Trading Central (98) = Buy, Refinitiv/Verus (86) = Sell (operator-identified) | Classified as L4 candidate by operator annotation. #10 ranking appropriate. Operator should note the named source conflict in investment log. |

---

## Recommended Configuration

Add to `allocation_policy.yaml`:

```yaml
signal_conflict:
  # FMP sell count thresholds
  l2_sell_count_min: 1          # ≥1 sell vote = L2 Moderate
  l3_sell_pct_min: 0.15         # ≥15% sell rate = L3 Significant
  l1_hold_consensus_label: HOLD # HOLD consensus label = L1 Mild
  # Advisory badge behavior
  enforcement: "advisory"       # advisory | review_required | block
  l3_enforcement: "advisory"    # Future: "review_required"
  badges:
    l0: null
    l1: "HOLD_CONSENSUS"
    l2: "CONFLICTING_SIGNAL"
    l3: "SIGNIFICANT_CONFLICT"
    l4: "HIGH_ANALYST_DISAGREEMENT"
```

---

## Implementation Scope (Phase 1)

| Item | Priority | Scope |
|------|----------|-------|
| Add conflict badge to deployment queue rendering (`app.js`) | HIGH | ~20 lines JS |
| Load FMP sell counts in `run_outcome_ui.py` `/api/deployment/queue` response | HIGH | ~15 lines Python |
| Add `signal_conflict` config section to `allocation_policy.yaml` | MEDIUM | 10 lines YAML |
| Add advisory note to NUE card in deployment queue | LOW | Manual annotation |
| Re-evaluate at 100+ attribution records for gate promotion | LOW | Future milestone |

---

## Governance Log

| Date | Action | Evidence | Outcome |
|------|--------|---------|--------|
| 2026-06-15 | SIGNAL-GOV-02 backtest executed | 28 records, 14 L2 | No gate warranted |
| 2026-06-15 | NUE Level 4 conflict documented | Operator research (TC vs RV) | Advisory annotation |
| 2026-06-15 | L3 holdings identified | TSLA, AVT, GTX | Advisory flags |
| 2026-06-15 | Implementation scoped | Option B advisory badges | Ready for dev |
