# Phase 23.0B — Q7: New UI Design — Portfolio Action Pipeline

**Design Date:** 2026-06-03  
**Analysis Run:** PAR-20260603-AC8FD5F0  
**Scope:** Replace "Tax-Aware Actions" section with "Portfolio Action Pipeline" grouped by 7 categories

---

## Design Overview

The current Tax-Aware Actions UI is a single flat table keyed on bearish signal detection. The new Portfolio Action Pipeline replaces it with a grouped, categorized view that surfaces all action intelligence the system can produce.

**Layout:** Collapsible section groups, each representing one action category. Groups auto-hide when empty (no candidates). Groups auto-expand when they contain HIGH priority candidates.

---

## Section Header

Replace:
```
TAX-AWARE ACTIONS
```

With:
```
PORTFOLIO ACTION PIPELINE
[Available Gain Capacity: $24,730]   [Projected: $38,966]
[N actions identified across M categories]
```

The tax capacity display remains — it is still relevant as a ranking modifier across all categories.

---

## Section Group Structure

Each category section renders as:

```
┌─────────────────────────────────────────────────────────────┐
│ [▼] CAT N — CATEGORY NAME                     [N candidates] │
│     Context line: brief explanation of why this category is  │
│     active and what the operator should do                   │
├────────┬────────┬─────────────┬────────────────┬────────────┤
│ PRIO   │ SYMBOL │ REASON      │ TAX CONTEXT    │ TIMING     │
├────────┼────────┼─────────────┼────────────────┼────────────┤
│ HIGH   │ FIS    │ Strategic   │ ADDS CAPACITY  │ SELL NOW   │
│        │        │ exit + loss │ −$14,344       │            │
└────────┴────────┴─────────────┴────────────────┴────────────┘
```

---

## Category 1: Signal Deterioration

**Header:** `SIGNAL DETERIORATION` — [N candidates]  
**Context line:** "Holdings with bearish analytical signals or trim recommendations from conviction intelligence."  
**Auto-expand:** Yes (HIGH priority)

| PRIO | SYMBOL | REASON | TAX CONTEXT | TIMING |
|---|---|---|---|---|
| HIGH | TSLA | BEARISH signal — ESS consensus: reduce | NO COST BASIS | SELL NOW |
| HIGH | PRIM | BEARISH signal — ESS consensus: reduce | NO COST BASIS | SELL NOW |

*Note: "NO COST BASIS" replaces "cost basis unavailable for tax calculation" as the label — honest disclosure, not noise.*

When `opportunity_flag = "TRIM"` is correctly mapped (field name fix in implementation), additional TRIM-flagged holdings would also appear here.

---

## Category 2: Strategic Exit

**Header:** `STRATEGIC EXIT` — [N candidates]  
**Context line:** "Operator-designated exits — former employer stock, legacy positions, or holdings with no forward investment intent."  
**Auto-expand:** Yes (HIGH priority when present)

| PRIO | SYMBOL | REASON | TAX CONTEXT | TIMING |
|---|---|---|---|---|
| HIGH | FIS | Former employer stock — no forward intent — −38.1% loss | HARVEST: ADDS CAPACITY (−$14,344) | SELL NOW |

*When empty:* Section shows collapsed with "No strategic exits designated" note.

---

## Category 3: Allocation Reduction

**Header:** `ALLOCATION REDUCTION` — [N candidates]  
**Context line:** "[Node]: [actual]% actual vs [target]% target (+[drift]% drift, [severity])."  
**Multiple context lines when multiple overweight nodes are active.**  
**Auto-expand:** Yes for MODERATE severity nodes

**Context lines for current run:**
- "EQUITIES.INTERNATIONAL: 18.63% actual vs 12.0% target (+6.63% drift, MODERATE)"
- "EQUITIES.INTERNATIONAL.LARGE: 8.10% vs 4.0% target (+4.10% drift, MODERATE)"
- "EQUITIES.US.MEGA.HYPER_MEGA: 9.88% vs 6.3% target (+3.58% drift, MODERATE)"

| PRIO | SYMBOL | REASON | TAX CONTEXT | TIMING |
|---|---|---|---|---|
| MODERATE | DODFX | INTERNATIONAL overweight +6.6% — mutual fund, UNKNOWN signal | HARVEST: TAX-FREE (+$2,751) | SELL NOW |
| MODERATE | VXUS | INTERNATIONAL overweight +6.6% — ETF, UNKNOWN signal | HARVEST: TAX-FREE (+$869) | SELL NOW |
| MODERATE | VEA | INTERNATIONAL overweight +6.6% — ETF, UNKNOWN signal | HARVEST: TAX-FREE (+$596) | SELL NOW |
| MODERATE | FIGFX | INTERNATIONAL overweight +6.6% — mutual fund, UNKNOWN signal | HARVEST: TAX-FREE (+$151) | SELL NOW |
| (info) | TSLA | HYPER_MEGA overweight +3.6% — also Cat 1 bearish | NO COST BASIS | See Cat 1 |

*Note: TSLA is cross-referenced from Cat 1. It appears as the primary entry in Cat 1, with a secondary reference in Cat 3.*

---

## Category 4: Funding Source

**Header:** `FUNDING SOURCE` — [N candidates]  
**Context line:** "Holdings available to fund new high-conviction positions in the deployment queue."  
**Auto-expand:** When deployment queue has active BUY targets

| PRIO | SYMBOL | REASON | TAX CONTEXT | TIMING |
|---|---|---|---|---|
| HIGH | FIS | Best funding source: strategic exit + loss harvest — frees $23,287 | HARVEST: ADDS CAPACITY (−$14,344) | See Cat 2 |
| MODERATE | DODFX | Allocation-aligned — overweight international, UNKNOWN signal | HARVEST: TAX-FREE (+$2,751) | See Cat 3 |
| MODERATE | VXUS | Allocation-aligned — overweight international | HARVEST: TAX-FREE (+$869) | See Cat 3 |
| LOW | VOO | Index fund → active replacement candidate | HARVEST: TAX-FREE (+$3,765) | CONSIDER |
| LOW | FXAIX | Index fund → active replacement candidate | HARVEST: TAX-FREE (+$1,302) | CONSIDER |

*Note: FIS and DODFX/VXUS/VEA are cross-referenced from Cat 2/Cat 3 with a secondary funding source tag. VOO/FXAIX appear only here.*

---

## Category 5: Loss Harvest

**Header:** `LOSS HARVEST` — [N candidates]  
**Context line:** "Holdings with unrealized losses harvestable against gain capacity. Available capacity: $[X]."  
**Auto-expand:** When unrealized losses exist

| PRIO | SYMBOL | REASON | TAX CONTEXT | TIMING |
|---|---|---|---|---|
| HIGH | FIS | −$14,344 unrealized loss (−38.1%) — largest loss in portfolio | HARVEST: ADDS CAPACITY — absorbs 58% of gain capacity | SELL NOW |

*When FIS is also in Cat 2, a cross-reference tag appears: "Also: Strategic Exit (Cat 2)."*

---

## Category 6: Gain Harvest

**Header:** `GAIN HARVEST` — [N candidates]  
**Context line:** "Holdings with gains realizable within your $[X] available gain capacity window — effectively tax-free."  
**Auto-expand:** When capacity > 0 and gain candidates exist

This section is most useful when the operator is actively trying to reposition but wants to maximize the tax-efficient window.

| PRIO | SYMBOL | REASON | TAX CONTEXT | TIMING |
|---|---|---|---|---|
| — | VOO | Not in Cat 1/2/3/4/5 — retain unless funding need | HARVEST: TAX-FREE (+$3,765) | OPTIONAL |
| — | TSLA | Cat 1 bearish — not a pure gain harvest; see Cat 1 | TAX-FREE if sold now | See Cat 1 |

*Note: If no Cat 1/2/3/4/5 candidates exist in this section (all are cross-refs), Cat 6 may be empty or show only pure gain-harvest candidates with no other action basis.*

---

## Category 7: Deferral Watch

**Header:** `DEFERRAL WATCH` — [N candidates]  
**Context line:** "Holdings near the 12-month long-term threshold. Consider waiting before acting."  
**Auto-expand:** No (LOW priority, advisory only)

*This section will remain empty until holding_days data is available. Display as collapsed with message: "Deferral analysis requires holding period data — not yet available."*

---

## Cross-Reference Behavior

Holdings appearing in multiple categories (FIS appears in Cat 2 + Cat 5 + Cat 4; TSLA appears in Cat 1 + Cat 3) should be handled as follows:

- **Primary classification:** The category with the highest semantic reason gets the full entry
- **Secondary references:** Other categories show a compact cross-reference row with "→ See Cat N" link
- **Operator impact:** One action addresses multiple categories — this should be surfaced as a benefit: "Selling FIS addresses 3 action categories simultaneously"

---

## Empty State Handling

Each category section when empty:

| Category | Empty State Text |
|---|---|
| Cat 1: Signal Deterioration | "No bearish signals or TRIM flags in current holdings." |
| Cat 2: Strategic Exit | "No strategic exits designated. Operator can tag positions for strategic exit." |
| Cat 3: Allocation Reduction | "No overweight nodes at MODERATE or HIGH severity." |
| Cat 4: Funding Source | "No deployment candidates beyond available cash. No funding source analysis needed." |
| Cat 5: Loss Harvest | "No unrealized loss positions identified. (Requires cost basis data.)" |
| Cat 6: Gain Harvest | "No gain realization opportunities (no available capacity or no gain positions)." |
| Cat 7: Deferral Watch | "Deferral analysis requires holding period data — not yet available." |

---

## Priority Badge Design

| Badge | Color | Meaning |
|---|---|---|
| HIGH | Red (#d32f2f) | Act now — signal, strategic exit, or significant loss |
| MODERATE | Amber (#f57c00) | Act when capacity and timing align |
| LOW | Gray (#757575) | Advisory — informational, low urgency |
| INFO | Blue (#1976d2) | Cross-reference or contextual note |

---

## Comparison to Current UI

| Feature | Current (Phase 23.0A) | New (Phase 23.0B) |
|---|---|---|
| FIS visibility | Hidden (NEUTRAL signal) | Visible (Cat 2 + Cat 5) — HIGH priority |
| DODFX/VXUS/VEA visibility | Hidden (UNKNOWN signal) | Visible (Cat 3) — MODERATE priority |
| VOO/FXAIX | Hidden | Visible (Cat 4 Funding Source) — LOW |
| TSLA | Bucket A "cost basis unavailable" | Cat 1 + Cat 3 with NO COST BASIS label |
| Overweight context | None | Node drift % shown per category |
| Tax context | Drives candidate generation | Modifies ranking within categories |
| Empty categories | Not applicable | Shown as collapsed with explanation |
| Cross-category holdings | Not applicable | Primary + secondary cross-reference |
| Action count summary | None | "N actions across M categories" |
