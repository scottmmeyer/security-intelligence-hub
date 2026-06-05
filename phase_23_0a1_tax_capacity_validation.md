# Phase 23.0A.1 — Q1: Tax Capacity Calculation Validation

**Validation Question**: Are the Available Gain Capacity and Projected Gain Capacity computed correctly?

---

## Formula Under Test

Implemented in `updateTaxComputed()` (`ui/portfolio_alignment/app.js`).

```
available = Math.max(0, -net_realized_ytd + capital_loss_carryforward)
projected = available + Math.abs(potential_additional_losses)
```

- `net_realized_ytd` — signed: negative values represent net losses realized so far this year; positive values represent net gains already booked.
- `capital_loss_carryforward` — unsigned (stored positive, forced via `Math.abs`): prior-year carryforward losses.
- `potential_additional_losses` — unsigned (forced via `Math.abs`): estimated additional losses the operator expects to realize before year-end.
- `available` — how much gain can be recognized this year tax-free (shielded by already-realized losses + carryforward). Floor at 0.
- `projected` — total expected capacity including losses not yet realized.

---

## Verification Case: Spec Reference Values

| Input | Value |
|---|---|
| `net_realized_ytd` | −24,730 (net losses realized YTD) |
| `potential_additional_losses` | 14,236 |
| `capital_loss_carryforward` | 0 |

**Step 1 — Available Gain Capacity**

```
available = max(0, -(-24730) + 0)
           = max(0, 24730)
           = 24,730  ✓
```

**Step 2 — Projected Gain Capacity**

```
projected = 24,730 + 14,236
           = 38,966  ✓
```

Both values match expected spec outputs.

---

## Display Precision: Pre-Fix Defect + Resolution

### Defect Found During Validation

The original `_formatTaxDollar()` used a 1,000 threshold for K-notation:

```js
// BEFORE (Phase 23.0A original)
if (abs >= 1_000) return "$" + (abs / 1_000).toFixed(1) + "K";
```

This produced:
- $24,730 → `$24.7K` (rounds to nearest $100, loses $30 of precision)
- $38,966 → `$39.0K` (rounds to nearest $100, loses $34 of precision)

For tax capacity context, operators entered exact dollar amounts and expect exact dollar amounts confirmed back to them. K-notation rounding undermines trust and creates ambiguity between e.g. $24,700 and $24,730.

### Fix Applied (Phase 23.0A.1)

```js
// AFTER (Phase 23.0A.1 fix)
if (abs >= 100_000) return "$" + (abs / 1_000).toFixed(1) + "K";
return "$" + abs.toLocaleString("en-US", { maximumFractionDigits: 0 });
```

Threshold raised to $100K. Values below $100K now display with full comma notation:
- $24,730 → `$24,730`  ✓
- $38,966 → `$38,966`  ✓
- $250,000 → `$250.0K`  ✓
- $1,250,000 → `$1.25M`  ✓

---

## Input Sign Conventions

| Field | Sign Convention | Input Source | `Math.abs` Applied? |
|---|---|---|---|
| `net_realized_ytd` | Signed. Negative = net loss. Positive = net gain. | Operator entry | No — sign is intentional |
| `potential_additional_losses` | Unsigned (magnitude only). Always positive loss amount. | Operator entry | Yes — `Math.abs` enforced in `_readTaxInputs()` |
| `capital_loss_carryforward` | Unsigned (magnitude only). Always positive carryforward. | Operator entry | Yes — `Math.abs` enforced in `_readTaxInputs()` |

The signed treatment of `net_realized_ytd` is correct: a negative value (net loss) increases available capacity. A positive value (net gain already booked) reduces available capacity toward zero.

**Edge case — already over budget**: If `net_realized_ytd = +10,000` and `carryforward = 0`, then:
```
available = max(0, -10000 + 0) = max(0, -10000) = 0
```
Result: zero available capacity. Floor prevents negative display. ✓

---

## Population from Persisted State

`loadTaxState()` → `_populateTaxFields()` maps server response keys to DOM inputs:

```js
const map = {
  taxNetRealizedYTD:   "net_realized_ytd",
  taxPotentialLosses:  "potential_additional_losses",
  taxCarryforward:     "capital_loss_carryforward",
  taxYear:             "tax_year",
};
```

On load, `updateTaxComputed()` is called after population, so the computed fields display immediately without operator needing to touch any input. ✓

Input event listeners are attached in `DOMContentLoaded` so computed fields update live on any subsequent keystroke. ✓

---

## Verdict: Q1

| Check | Result |
|---|---|
| `available` formula correct | ✓ PASS |
| `projected` formula correct | ✓ PASS |
| Sign convention on `net_realized_ytd` correct | ✓ PASS |
| `Math.abs` on unsigned fields | ✓ PASS |
| Floor at 0 prevents negative display | ✓ PASS |
| Display precision in Tax Panel computed fields | ⚠ DEFECT (fixed in 23.0A.1) |
| Live update on input event | ✓ PASS |
| Computed fields populate on load from persisted state | ✓ PASS |

**Q1 Status: PASS — one display precision defect found and corrected.**
