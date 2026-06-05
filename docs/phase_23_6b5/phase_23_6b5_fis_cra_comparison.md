# Phase 23.6B.5 — FIS CRA Comparison

**Date:** 2026-06-04  

---

## Current Behavior (with strategic_exit_symbols)

| Field | Value |
|-------|-------|
| Category | STRATEGIC_EXIT |
| Priority | HIGH |
| Sizing | 1.0 (100%) |
| Estimated Proceeds | $6,189 (full position) |
| Evidence | "operator-designated strategic exit (no STI profile available) \| [signal context] ESS=BEARISH" |
| Tax Bucket | A (unrealized loss ~$3,673) |
| Rank in source list | #2 (after blocked TSLA) |

FIS dominates the actionable source list as the highest-priority non-blocked sell candidate.

---

## Projected Behavior After Retirement

Without `strategic_exit_symbols`, FIS is processed through normal category detection:

**ESS=BEARISH, opportunity_flag=WATCH, is_overweight=False, replay=False**

Category 1 (Signal Deterioration): WATCH flag + BEARISH → **MODERATE priority, 25% sizing**
- Proceeds: $6,189 × 25% = **$1,547**

Category 4 (Tax-Aware Exit): unrealized loss ~$3,673 → **Bucket A**, which triggers priority upgrade MODERATE → **HIGH**
- Proceeds: $1,547 (sizing stays 25%, but priority elevated)

Net outcome after tax modifier: **SIGNAL_DETERIORATION HIGH, 25% sizing, ~$1,547 proceeds**

| Field | Before (strategic exit) | After (normal rules) |
|-------|------------------------|---------------------|
| Category | STRATEGIC_EXIT | SIGNAL_DETERIORATION |
| Priority | HIGH | HIGH (Bucket A upgrade) |
| Sizing | 100% | 25% |
| Proceeds | $6,189 | ~$1,547 |
| Source rank | #2 of 26 | #5–7 (behind larger tax harvest candidates) |
| Action implied | Full exit | Partial sell (monitoring position) |

---

## Interpretation

The change accurately reflects the shift in operator intent:

- **Before retirement**: "I am actively liquidating FIS — sell everything CRA suggests"
- **After retirement**: "FIS is a residual BEARISH position with a loss — I may opportunistically harvest it"

The 25% sizing ($1,547) is appropriate for a 1.3% position with BEARISH (not VERY_BEARISH) ESS and no active exit mandate. If the operator eventually decides to exit the full remaining position, they can either add FIS back to `strategic_exit_symbols` or use the Include/Skip controls in the CRA UI to manually include the full position.

The $3,673 unrealized loss still makes FIS a legitimate Bucket A harvest candidate — it won't disappear from the CRA output, it will just be appropriately sized.
