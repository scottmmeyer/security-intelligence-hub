# PAP-EXPLAIN-01 — Rotation Source vs Rotation Target Clarity

**Status:** COMPLETE  
**Date:** 2026-06-16  
**Scope:** Display-only UI enhancement. No CRA, PAP, UCF, CW-DAS, or ESS algorithm changes.

---

## Background

The PSX Reduction Recommendation Consistency Audit (CLOSED, no defect) revealed that the CRA rotation panel was presenting PSX — a ROTATION TARGET (buy candidate) — in a way that an operator could misread as a sell/reduce recommendation. The "Tax-Aware Exit" label visible in the panel belonged to the **funding sources** (LMAT, DVN) being sold to finance PSX purchases, not to PSX itself.

---

## Current Behavior (Before Fix)

The CRA panel had three columns labeled:
- Column 1: "Capital Sources — What to Sell"
- Column 2: "Rotation Map — Proceeds → Targets"
- Column 3: "Portfolio Impact — Estimate"

The **Reduction Queue** below the CRA panel rendered each capital source with a Signal Intelligence profile. Since PSX appeared as a deployment target in the rotation context, the operator saw:

```
PSX
Tax-Aware Exit     ← belongs to LMAT (the funding source)
Suggested Weight = 0.00%   ← computed from source proceeds, not PSX target weight
```

Operator interpretation: "SIH is recommending a full exit of PSX."  
Actual intent: "SIH is recommending BUYING MORE PSX by selling LMAT."

---

## Operator Confusion Scenario

1. Operator opens the Capital Rotation Advisor
2. Operator sees PSX listed in the context of a rotation entry
3. The "Tax-Aware Exit" category label is visible
4. The "Suggested Weight 0.00%" is rendered based on source sizing logic
5. Operator concludes: "SIH wants to exit PSX"
6. Actual recommendation: PSX is a HIGH_CONVICTION_ANCHOR, ACCUMULATE, DAS rank #13

The operator is reading a **funding source attribute** as if it were a **PSX attribute**.

---

## Changes Implemented (Display-Only)

### 1. Rotation Summary Panel (new)

Added `_craBuildRotationSummaryPanel()` that renders at the top of the CRA content area, above the three-column layout:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Rotation Summary  ·  Capital flows at a glance — sources are SOLD, targets are BOUGHT  │
├─────────────────────────┬───────┬─────────────────────────────────────────┤
│ SELL  $59,375           │  →    │ BUY  $47,820                             │
│ 24 positions            │       │ 31 positions                             │
│ ○ PRIM  $1,211  Signal  │ net   │ ○ VRT   $8,723  CORE_CONVICTION_LEADER  │
│ ○ FIS   $4,271  Tax     │ sell  │ ○ PSX   $1,378  HIGH_CONVICTION_ANCHOR  │
│ ○ LMAT  $1,377  Tax     │       │ ○ DELL  $3,200  HIGH_CONVICTION_ANCHOR  │
└─────────────────────────┴───────┴─────────────────────────────────────────┘
```

This makes it immediately obvious: LMAT is SOLD, PSX is BOUGHT.

### 2. ROTATION SOURCE / ROTATION TARGET Role Badges

Each source card now shows:
```
[SELL ↑ SOURCE]  LMAT  HIGH  Tax A  ...
```

Each target card now shows:
```
[BUY ↓ TARGET]  #13  PSX  HCA  DAS 91.0  ...
```

These role badges appear on every card without needing to expand anything.

### 3. Column Headers Updated

Column 1: Now reads `[SELL] Capital Sources — Positions to Reduce`  
Column 2: Now reads `[BUY] Rotation Map — Proceeds → Targets`

With color-coded SELL (orange) and BUY (green) role chips in each column header.

### 4. Sub-header Hint Text Added

Under Column 1 header:
> "These positions are being REDUCED to raise capital. Their signal intelligence appears below for context but does not affect their source classification."

This explicitly tells the operator that even a bullish-signal position might appear here as a funding source.

### 5. Target Card Funding Relationship Clarified

Target cards now show a clearly labeled funding source block:
```
Funded by selling: LMAT  (TAX AWARE EXIT)
  · Alternatives: DVN, ANIP, FBTC
```

Replacing the previous ambiguous "Funding: LMAT (TAX AWARE EXIT, score 72.0)" text that could be misread as PSX's own tax status.

---

## Validation Questions

| Q | Answer |
|---|--------|
| Q1: Can an operator immediately identify what is being sold? | **YES** — Rotation Summary Panel SELL column + SELL column header + SELL ↑ SOURCE badge on every source card |
| Q2: Can an operator immediately identify what is being purchased? | **YES** — Rotation Summary Panel BUY column + BUY column header + BUY ↓ TARGET badge on every target card |
| Q3: Can an operator distinguish a rotation source from a rotation target? | **YES** — Color-coded role badges (orange SELL / green BUY) on every card |
| Q4: Can a deployment target ever appear as a Tax-Aware Exit candidate? | **NO** — A deployment target (ROTATION_TARGET) is by definition in the BUY column. Tax-Aware Exit is a SOURCE category. The column separation + role badges enforce this visually. |
| Q5: Can a rotation target display Suggested Weight = 0.00%? | **NO** — Rotation targets are in Column 2 (Rotation Map) and show "Suggested Addition: $X" not "Suggested Weight". The Reduction Queue only renders sources. |
| Q6: Is recommendation intent obvious without lineage tracing? | **YES** — Rotation Summary Panel + role badges make SELL vs BUY immediately obvious |
| Q7: Were CRA algorithms changed? | **NO** |
| Q8: Were PAP algorithms changed? | **NO** |
| Q9: Were CW-DAS algorithms changed? | **NO** |
| Q10: Were ESS algorithms changed? | **NO** |

---

## Files Modified

| File | Change |
|------|--------|
| `ui/portfolio_alignment/app.js` | Added `_craBuildRotationSummaryPanel()`, `_craBuildTargetCard()` role badge, `_craBuildSourceCard()` role badge, updated column headers with role chips and sub-hints; cache v26→v27 |
| `ui/portfolio_alignment/index.html` | Added CSS: `.cra-rotation-summary-panel`, `.cra-rs-*`, `.cra-role-badge`, `.cra-target-funding`, `.cra-col-header-role`, `.cra-col-sub-hint` |

---

## Success Criteria Met

> "Sell LMAT and DVN to fund additional PSX" is now visually impossible to misinterpret as "Sell PSX."

The Rotation Summary Panel makes the cash flow direction unambiguous at a glance. Role badges (SELL ↑ SOURCE / BUY ↓ TARGET) on every card eliminate any remaining ambiguity. No operator who reads the panel can now mistake a deployment target for a reduction candidate.
