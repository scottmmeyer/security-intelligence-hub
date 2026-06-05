# Phase 23.6B.2 — Allocation Logic Fix

**Date:** 2026-06-04

---

## Defect Description

The original `_allocate_capital()` function used a 50% per-candidate proportional cap:
```python
proportional_cap = total_pool * 0.5
suggested = min(headroom_usd, remaining, proportional_cap)
```

For any pool, this guaranteed exactly 2 allocations:
1. Candidate #1 → 50% of pool
2. Candidate #2 → 50% of remaining (= 50% of 50% = 25% of pool... but remaining = pool*0.5 after first, so min(headroom, pool*0.5, pool*0.5) = pool*0.5)
3. All subsequent candidates → $0 (remaining = 0)

This produced DELL and VRT each at projected weights of ~11–14%, far above the 6% WARN threshold.

---

## Fix Location

`src/portfolio/cra/rotation_proposal_builder.py` — `_allocate_capital()` function entirely replaced.

---

## New Algorithm: Tier-Aware Proportional Allocation

Mirrors the Phase 7.5D Deployment Plan philosophy:

### Tier Split
- CCL candidates (CORE_CONVICTION_LEADER): receive 50% of total pool
- HCA candidates (HIGH_CONVICTION_ANCHOR + unclassified): receive 50% of total pool
- Unspent CCL budget rolls down to HCA

### Within-Tier: Headroom-Proportional Distribution
Each candidate receives a share proportional to its available headroom:
```
share_i = (headroom_i / total_tier_headroom) × tier_pool
```

### Hard Caps Applied to Each Candidate
```
suggested = min(
    proportional_share,
    headroom_usd,       # can't exceed headroom
    remaining,          # can't exceed remaining pool
    per_candidate_cap,  # 20% of total pool — concentration guard
    warn_cap_usd,       # don't project above WARN_POSITION_PCT (6%)
)
```

### Per-Candidate Cap
`per_candidate_cap = total_pool × 20%`

For an $85K pool: max per candidate = $17,000. A reasonable operator could fund 5+ positions at this rate; the tier structure then distributes the remainder proportionally across all eligible candidates.

### WARN Threshold Guard
`warn_cap_usd = max(0, (6% − current_weight%) × portfolio_mv)`

Ensures no single rotation pushes a position above the 6% WARN threshold.

---

## Before / After

| Metric | Before (50% cap) | After (tier-aware) |
|--------|-----------------|-------------------|
| Deployment targets | 2 | 31 |
| DELL projected weight | ~11.8% | 4.49% |
| VRT projected weight | ~14.4% | 5.39% |
| ARW allocation | $0 | $1,575 |
| PSX allocation | $0 | $1,655 |
| AVT allocation | $0 | $1,610 |
| ATLC allocation | $0 | $1,661 |
| LRCX allocation | $0 | $1,596 |
| CAH allocation | $0 | $1,584 |
| Any target > 6% | Yes (DELL, VRT) | No |
| Consistent with DP philosophy | No | Yes |

---

## CW-DAS Rank Order Preservation

All deployments are sorted by original CW-DAS rank before output. The tier grouping only affects budget assignment; the final output respects rank ordering exactly.

Verified by `test_rank_order_preserved_across_tiers`.

---

## New Constants

```python
_TIER_CCL_FRACTION      = 0.50   # CCL gets 50% of pool
_TIER_HCA_FRACTION      = 0.50   # HCA gets 50% of pool
_PER_CANDIDATE_CAP_FRACTION = 0.20   # 20% per-candidate hard cap
_WARN_POSITION_PCT      = 6.0    # matches deployment_queue.py
```

---

## Non-Negotiables

- CW-DAS deployment_score unchanged — no re-scoring
- Rank order preserved — no re-ranking
- No modifications to CW-DAS, ESS, Replay, FMI, Policy engine, or mandate logic
