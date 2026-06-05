# Portfolio Alignment — Tax-Aware Action Columns — Phase 23.0A

## Table: Tax-Aware Portfolio Actions

Rendered in `#taxActionSection` below the Security Intelligence Overlay.
Visible only when the analysis contains holdings with actionable tax guidance.

---

## Column Definitions

| Column | Source | Description |
|---|---|---|
| Priority | Computed | Integer sort rank (1 = highest urgency). Priority-1 styled red, priority-2 amber, priority-3 teal. |
| Symbol | `security_overlays[].symbol` | Ticker in monospace, accent color |
| Current Action | `security_overlays[].recommended_action` | SIH action badge (TRIM, MONITOR, HOLD, etc.) |
| Tax Impact | Computed from `cost_basis` + `market_value` | Estimated unrealized gain (+) or loss (−). Shows "—" when cost basis unavailable. |
| Holding Period | `holding_days` | Days held + LT/ST label.  Shows "—" when absent. |
| Tax Category | Computed | Long-Term Gain / Short-Term Gain / Capital Loss / N/A |
| Recommended Timing | Bucket logic | SELL NOW / WAIT / HARVEST LOSS / HOLD DESPITE GAIN |
| Reason | Computed | Plain-English rationale string |

---

## Bucket Group Headers

Rows are grouped by bucket with a full-width header row:

| Bucket | Header Text |
|---|---|
| A | A — SELL NOW |
| B | B — SELL WHEN LONG-TERM |
| C | C — SELL FOR REBALANCING |
| D | D — HARVEST LOSS |
| E | E — HOLD DESPITE GAIN |

---

## Badge Styles

### Timing Badges (`.tax-timing`)

| Value | CSS Class | Color |
|---|---|---|
| SELL NOW | `.tax-timing-SELL_NOW` | Red |
| WAIT | `.tax-timing-WAIT` | Amber |
| HARVEST LOSS | `.tax-timing-HARVEST_LOSS` | Green |
| HOLD DESPITE GAIN | `.tax-timing-HOLD_DESPITE_GAIN` | Blue |

### Tax Category Chips (`.tax-cat`)

| Value | CSS Class |
|---|---|
| Long-Term Gain | `.tax-cat-LT` — green |
| Short-Term Gain | `.tax-cat-ST` — orange |
| Capital Loss | `.tax-cat-LOSS` — light green |
| N/A | `.tax-cat-NA` — grey |

---

## Footer

Table footer shows current Available Gain Capacity and Projected Gain Capacity
derived from the active tax state.

---

## Example Rows

| Priority | Symbol | Action | Tax Impact | Holding | Category | Timing | Reason |
|---|---|---|---|---|---|---|---|
| 1 | FIS | TRIM | −$14,236 | 520d (LT) | Capital Loss | HARVEST LOSS | Poor outlook + unrealized loss |
| 2 | XYZ | TRIM | +$8,100 | 410d (LT) | Long-Term Gain | SELL NOW | Poor outlook + long-term gain |
| 3 | ABC | TRIM | +$4,500 | 180d (ST) | Short-Term Gain | WAIT | Short-term gain approaching LT threshold |

---

## Visibility Rule

`#taxActionSection` is hidden (`display:none`) when:
- No analysis has been run
- No holdings qualify for bucket assignment (no poor-outlook or reduce candidates)

The section is shown automatically after `renderResults()` runs.
