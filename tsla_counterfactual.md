# TSLA Counterfactual Analysis

**Date:** 2026-06-09  
**Scenario:** DO_NOT_SELL policy removed from TSLA

---

## Current State (Baseline)

| Field | Value |
|---|---|
| Policy | DO_NOT_SELL (ACTIVE) |
| Execution state (DQ) | policy_suppressed (not in queue) |
| Execution state (PAP rec) | BLOCKED_BY_POLICY |
| Effective action | MONITOR_ONLY |
| Opportunity flag | TRIM |
| ESS score | VERY_BEARISH |
| Composite score | 1.33 / 5.0 |
| RPS (Reduction Priority Score) | **85** |
| Market value | $13,904 (2.99% of portfolio) |
| UCF label | TRIM_WATCH |
| Replay percentile | 6.2 (bottom tier — UNDERPERFORMING) |
| CRA capital pool | Excluded (blocked_by_policy=True) |

---

## Counterfactual: DO_NOT_SELL Removed

### In the Deployment Queue (DQ)

TSLA would **NOT** enter the DQ even if policy were removed. The DQ eligibility gate requires:
- `signal_direction == BULLISH` ← TSLA is BEARISH/VERY_BEARISH **FAIL**
- `replay_supported == True` ← TSLA is replay-supported PASS  
- `strategic_classification == HIGH_CONVICTION_RETAIN` ← TSLA is TACTICAL_GROWTH **FAIL**
- `narrative_tier in {CCL, HCA}` ← TSLA is not CCL or HCA **FAIL**

**TSLA cannot enter the DQ under any current policy state. DQ is a buy-only surface.**

### In the REDUCE_OVERWEIGHT Recommendation

The REDUCE_OVERWEIGHT rec containing TSLA (REC-F129627C) would move from:
- BLOCKED_BY_POLICY → **EXECUTABLE**
- effective_action: MONITOR_ONLY → **REDUCE**

TSLA's RPS = **85** (highest in portfolio).

### In the PAP

The REDUCE_OVERWEIGHT rec would move from the Blocked lane → **Actions lane** (top of Actions lane due to RPS 85).

### Where Would TSLA Rank vs the Current Top 10?

**Current Top 10 are all BUY actions (CW-DAS scores 88–98).**

TSLA RPS = 85 vs VRT CW-DAS = 97.99. 

**These scores are incommensurable** — they measure different things on different scales. CW-DAS measures buy attractiveness; RPS measures reduction urgency. Under the current architecture, they cannot be directly compared.

However, if we apply the naive comparison (both normalized 0–100):

| Position | Symbol | Score | Action | System |
|---|---|---|---|---|
| 1 | VRT | 97.99 | BUY | CW-DAS |
| … | … | … | … | … |
| 20 | GTX | 86.11 | BUY | CW-DAS |
| **21** | **TSLA** | **85.0** | **TRIM** | **RPS** |
| 22 | DODFX | 58.0 | HOLD (reduce) | RPS |

TSLA at RPS=85 would rank **#21 in the unified stack** — narrowly outside the current Top 20, just below GTX (CW-DAS 86.11). Under a unified queue, TSLA would be the **first reduction action** to appear in the operator's primary action view if the Top 20 were extended to 25.

### Would TSLA Outrank VRT?

**No.** TSLA RPS=85 < VRT CW-DAS=97.99. VRT remains #1 under naive comparison.

However, this comparison is architecturally undefined — the scores are not designed to be compared cross-system.

### Would TSLA Become the #1 Portfolio Action?

**No** under naive comparison. But TSLA at RPS=85 is the **#1 reduction action** in the portfolio. Depending on how portfolio urgency is weighted (allocation mandate vs buy opportunity), an argument can be made that addressing a top-1 RPS TRIM candidate is more urgent than the marginal improvement from buying ARW vs ATLC (both score ~94-97, very close). This is an architectural judgment call, not a data question.

### CRA Capital Pool Impact

If TSLA DO_NOT_SELL were removed:
- TSLA ($13,904 at 100% sizing) would enter as a SIGNAL_DETERIORATION source
- Capital pool would increase from $96,633 → **~$110,537**
- TSLA would be the highest-priority source (URGENT priority, VERY_BEARISH signal)

---

## Summary

| Question | Answer |
|---|---|
| Would TSLA enter DQ Top 10? | No — DQ eligibility requires BULLISH signal; TSLA fails structurally |
| Would TSLA enter PAP actions lane? | Yes — REDUCE_OVERWEIGHT becomes EXECUTABLE, top of Actions lane |
| Would TSLA enter CRA pool? | Yes — SIGNAL_DETERIORATION at URGENT priority |
| Would TSLA outrank VRT? | Not under naive score comparison (85 vs 97.99) |
| Would TSLA be #1 reduction action? | Yes |
| Would TSLA be #1 portfolio action? | Only if a unified queue is defined and weighted; currently incommensurable |
