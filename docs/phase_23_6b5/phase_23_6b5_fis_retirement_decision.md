# Phase 23.6B.5 — FIS Strategic Exit Retirement Decision

**Date:** 2026-06-04  

---

## Question 1: Strategic Exit Criteria Review

### Original Designation

FIS was placed into `strategic_exit_symbols` to support an intentional multi-session liquidation campaign. The original designation was correct: FIS carried BEARISH ESS, no replay support, and a significant unrealized loss — all indicating a position the operator wanted to reduce.

### Position Progression (from PAR run history)

| Run | Quantity | Market Value | Change |
|-----|---------|-------------|--------|
| PAR-20260603-D95DCA03 | 478.2 shares | $19,499 | Baseline |
| PAR-20260604-3565A7CD | 378.2 shares | $15,631 | −100 shares sold |
| PAR-20260604-57D5316D | 149.2 shares | $6,146 | −229 shares sold |
| PAR-20260604-CBB7785E | 149.2 shares | $6,189 | Stable (price move) |

**Total reduction: 329 shares (69% of original position sold)**

### Has the original objective been achieved?

**Yes — substantially.** The operator reduced FIS from 478 shares ($19,499) to 149 shares ($6,189), a 69% liquidation across multiple trading sessions today. The position has been reduced from a meaningful ~4% portfolio weight to a residual ~1.3% weight.

### Does the remaining 149-share position justify continued strategic-exit treatment?

**No.** At 1.3% of portfolio ($6,189), FIS is now below-average weight. The remaining 149 shares represent:

1. A residual position — not a strategic concentration risk
2. An unrealized loss of ~$3,673 (cost basis $9,862) — a tax-harvest candidate
3. A BEARISH ESS signal — appropriate for normal CRA Category 1 detection
4. A position the operator may choose to exit via normal workflow at any time

The strategic exit designation was a commitment to an active campaign. That campaign is functionally complete.

### Would an experienced PM classify this as a strategic exit?

**No.** An experienced PM would say: "I've done most of what I set out to do. The remainder is a small residual position I'll manage through normal portfolio maintenance — it doesn't need a dedicated exit mandate."

---

## Recommendation

**RETIRE the FIS strategic exit designation.**

The 100% sizing / STRATEGIC_EXIT override currently forces FIS to the top of every CRA rotation at full value ($6,189). This overstates urgency for a 1.3% residual. Under normal rules, FIS would appear as either:
- SIGNAL_DETERIORATION MODERATE (BEARISH ESS, 50% sizing, ~$3,095) — still visible and actionable
- TAX_AWARE_EXIT HIGH (Bucket A loss harvest) — equally actionable via normal tax logic

Both outcomes represent appropriate operator guidance for a residual position — without the elevated priority that implies an active campaign.
