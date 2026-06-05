# Tax-Aware Action Framework — Phase 23.0A

## Design Principle

> Taxes are a **decision modifier**, not a decision driver.
>
> The primary sequence remains:
> Identify actions → Evaluate conviction → Evaluate mandate alignment →
> Evaluate replay → Evaluate tax consequences → Prioritize.

---

## Action Bucket Definitions

### Bucket A — SELL NOW

| Criterion | Value |
|---|---|
| Conviction/Outlook | Poor or deteriorating (BEARISH signal, TRIM flag) |
| Tax Consequence | Acceptable (gain shielded or long-term rate) |
| Gain Capacity | Available or gain is long-term |

**Examples:** Bearish signal + long-term gain at favorable rate; Bearish signal + gain within available capacity

### Bucket B — SELL WHEN LONG-TERM

| Criterion | Value |
|---|---|
| Outlook | Poor |
| Gain Type | Short-term gain |
| Shielded? | No (gain exceeds available capacity) |

**Behavior:** Defer until 365-day threshold crossed.

### Bucket C — SELL FOR REBALANCING

| Criterion | Value |
|---|---|
| Trigger | Asset class overweight, mandate drift, reduce candidate |
| Tax Consequence | Acceptable |

**Behavior:** Tax consequences acceptable; mandate alignment is primary driver.

### Bucket D — HARVEST LOSS

| Criterion | Value |
|---|---|
| Outlook | Poor |
| Unrealized P&L | Loss |

**Behavior:** Realize the loss to build gain capacity.  Functions as a funding source for Bucket A sells.

### Bucket E — HOLD DESPITE GAIN

| Criterion | Value |
|---|---|
| Conviction | High |
| Signal | Bullish (BULLISH ESS direction, CW-DAS BUY) |
| P&L | Unrealized gain |

**Examples:** VRT, ARW, SNX, AVT, CAH, LRCX, DELL, CBOE

**Behavior:** Tax cost deferred; SIH conviction supports continued hold.

---

## Action Timing Labels

| Label | CSS Class | When Used |
|---|---|---|
| `SELL NOW` | `.tax-timing-SELL_NOW` | Bucket A, Bucket C |
| `WAIT` | `.tax-timing-WAIT` | Bucket B (approaching LT threshold) |
| `HARVEST LOSS` | `.tax-timing-HARVEST_LOSS` | Bucket D |
| `HOLD DESPITE GAIN` | `.tax-timing-HOLD_DESPITE_GAIN` | Bucket E |
| `DEFER` | `.tax-timing-DEFER` | Future use |

---

## Tax Category Classification

| Category | Trigger | CSS |
|---|---|---|
| Capital Loss | Unrealized P&L < 0 | `.tax-cat-LOSS` |
| Long-Term Gain | P&L > 0, holding ≥ 365 days | `.tax-cat-LT` |
| Short-Term Gain | P&L > 0, holding < 365 days | `.tax-cat-ST` |
| Gain (period unknown) | P&L > 0, no holding period data | `.tax-cat-LT` |
| N/A | No cost basis in portfolio export | `.tax-cat-NA` |

---

## Data Requirements

### From Portfolio Export (optional — shows "—" when absent)

- `cost_basis` — enables unrealized P&L calculation
- `holding_days` — enables Long-Term vs Short-Term classification

### From Tax State Panel (operator-entered)

- `net_realized_ytd` — determines available gain capacity
- `potential_additional_losses` — determines projected gain capacity
- `capital_loss_carryforward` — augments available capacity

### From SIH Analysis

- `ess_direction` / `signal_direction` — signal quality input
- `recommended_action` / `cw_das_flag` — conviction + mandate alignment input

---

## Non-Goals

This framework does NOT:
- Calculate tax liability
- Optimize tax lots
- Perform wash-sale analysis
- Import or interpret tax returns
- Override conviction-based holds for tax reasons
