# Tax Position Panel — Phase 23.0A

## Purpose

Provide a collapsible operator input card within Portfolio Alignment that captures
the operator's current tax context.  This context is used as a **decision modifier**
to sequence portfolio actions — it is not a tax optimization engine.

## Location

Upload Panel → bottom of section, above "Supported file formats" details accordion.

## UI Element ID

`#taxPositionPanel`  (`.tax-panel` CSS class)

---

## Input Fields

| Field ID | Label | Description | Example |
|---|---|---|---|
| `taxNetRealizedYTD` | Net Realized Gain / Loss YTD | Negative = net losses realized YTD; Positive = net gains realized YTD | `-24730` |
| `taxPotentialLosses` | Potential Additional Losses | Unrealized losses that could still be harvested in the current tax year | `14236` |
| `taxCarryforward` | Capital Loss Carryforward | Losses carried forward from prior tax years | `0` |
| `taxYear` | Tax Year | Active tax year for this context | `2026` |

---

## Computed Display Fields

### Available Gain Capacity

$$\text{Available Gain Capacity} = \max(0,\ -\text{Net Realized YTD} + \text{Carryforward})$$

**Interpretation:** Amount of capital gains that can be realized today with zero incremental tax cost, shielded by losses already booked or carried forward.

**Example:** Net Realized YTD = -$24,730 + Carryforward = $0 → **$24,730 available**

### Projected Gain Capacity

$$\text{Projected Gain Capacity} = \text{Available Gain Capacity} + \text{Potential Additional Losses}$$

**Interpretation:** Total gain capacity if all potential losses are also harvested before year-end.

**Example:** $24,730 + $14,236 = **$38,966 projected**

---

## Persistence

Tax inputs persist via server-side JSON file at:

```
data/operator/portfolio_alignment_state.json
```

Survival guarantees:
- Page refresh ✓
- Server restart ✓
- Browser restart ✓

Inputs remain until operator edits, clears, or resets them.

---

## Design Constraints

- Collapsible: closed by default to minimize visual noise when unused
- Disclaimer always visible within panel: tax context is advisory, not optimization
- No wash-sale analysis, no lot optimization, no tax liability calculation
