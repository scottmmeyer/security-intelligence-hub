# Phase 23.0B — Q6: Tax Context Integration Design

**Design Date:** 2026-06-03  
**Analysis Run:** PAR-20260603-AC8FD5F0  
**Question:** How should tax context integrate into the new multi-dimensional framework?

---

## Design Principle: Tax Is a Ranking Modifier, Not a Category Generator

The fundamental architectural decision for Phase 23.0B:

> **Tax context answers "when" and "in what order" — not "whether" or "why"**

This reverses the current Phase 23.0A model, which only surfaces candidates that have a specific tax profile. In the Phase 23.0B framework:

1. Categories generate candidates (based on signal, allocation, strategic flags, loss/gain)
2. Tax context re-ranks candidates within each category
3. Tax context adds a timing recommendation (HARVEST NOW, SELL NOW, WAIT, DEFER)
4. Tax context is NEVER used to exclude a candidate from a category

**A holding that should be exited will remain a candidate regardless of its tax profile.** The tax context merely informs how and when the operator executes the exit.

---

## Current Tax State (as of 2026-06-03)

| Field | Value |
|---|---|
| Net Realized YTD | −$24,730 (losses exceed gains) |
| Potential Additional Losses | +$14,236 |
| Capital Loss Carryforward | $0 |
| Available Gain Capacity | **$24,730** |
| Projected Gain Capacity | **$38,966** |

**Available Gain Capacity = $24,730** means the operator can realize up to $24,730 in gains before incurring any additional tax liability this year. Gains within this window are effectively free.

**Projected Gain Capacity = $38,966** includes the $14,236 in potential additional losses (e.g., from FIS). Once FIS is harvested, the capacity expands.

---

## Tax Context Rules by Candidate Type

### Rule 1: Gains Within Available Capacity → "HARVEST: TAX-FREE"

If a candidate has an unrealized gain ≤ Available Gain Capacity ($24,730), realizing it is effectively tax-free this year.

**Current holdings where gains are fully within capacity:**

| Symbol | Unrealized Gain | Within Capacity? | Tax Label |
|---|---|---|---|
| TSLA | +$3,631 | Yes ($3,631 ≤ $24,730) | HARVEST: TAX-FREE |
| DODFX | +$2,751 | Yes | HARVEST: TAX-FREE |
| VOO | +$3,765 | Yes | HARVEST: TAX-FREE |
| FXAIX | +$1,302 | Yes | HARVEST: TAX-FREE |
| VXUS | +$869 | Yes | HARVEST: TAX-FREE |
| VEA | +$596 | Yes | HARVEST: TAX-FREE |
| PRIM | +$7 | Yes | HARVEST: TAX-FREE |
| FIGFX | +$151 | Yes | HARVEST: TAX-FREE |

These gains are additively constrained — selling TSLA ($3,631) + DODFX ($2,751) + VOO ($3,765) + FXAIX ($1,302) = $11,449 still leaves $13,281 of remaining capacity.

### Rule 2: Unrealized Losses → "HARVEST: ADDS CAPACITY"

If a candidate has an unrealized loss, harvesting it does not use capacity — it adds to it.

| Symbol | Unrealized Loss | Tax Label | Capacity Impact |
|---|---|---|---|
| FIS | −$14,344 | HARVEST: ADDS CAPACITY | +$14,344 to projected capacity |

After harvesting FIS: Available capacity = $24,730, Projected capacity = $38,966 + additional FIS loss already partially in projected. More precisely, harvesting FIS converts potential additional losses ($14,236) into realized losses, which:
- Directly offsets the negative YTD position
- Increases capacity for future gain realization

### Rule 3: Gains Beyond Capacity → "SELL: TAX COST APPLIES"

If cumulative realized gains approach or exceed $24,730, any further gains incur tax.

Once the capacity window is exhausted, candidates with remaining gains are labeled:
- `SELL: SHORT-TERM GAIN` — if holding < 12 months (higher tax rate)
- `SELL: LONG-TERM GAIN` — if holding ≥ 12 months (lower tax rate)

### Rule 4: Near LT Threshold → "CONSIDER DEFERRAL"

If a candidate has an unrealized gain, is short-term (< 12 months), and the gain exceeds capacity:

- Waiting for the 12-month mark reduces tax rate from short-term to long-term
- Label: `WAIT: X DAYS TO LONG-TERM` where X = days remaining

This is Category 7 (Deferral) — it does not prevent the candidate from appearing; it adds a timing advisory.

---

## Tax Context Column Design

The new UI action pipeline should include a "Tax Context" column for each candidate:

| Tax Context Value | Meaning |
|---|---|
| HARVEST: TAX-FREE | Gain fully covered by available capacity |
| HARVEST: ADDS CAPACITY | Unrealized loss — selling increases future capacity |
| SELL: LONG-TERM GAIN | Gain is long-term; pay LT capital gains rate |
| SELL: SHORT-TERM GAIN | Gain is short-term; pay higher ST rate |
| WAIT: N DAYS TO LT | Deferral recommended — near LT threshold |
| NO COST BASIS | Cost basis not available; tax impact unknown |

The "NO COST BASIS" state covers the current implementation gap where `cost_basis` is not in the overlay. This is an honest disclosure rather than suppressing candidates.

---

## Re-Ranking by Tax Context Within Categories

Within Category 3 (Allocation Reduction), for example, tax context provides a secondary sort:

| Priority | Symbol | Allocation Reason | Tax Context | Recommended Timing |
|---|---|---|---|---|
| 1 | DODFX | INTERNATIONAL overweight +6.6% | HARVEST: TAX-FREE (+$2,751) | SELL NOW |
| 2 | VXUS | INTERNATIONAL overweight +6.6% | HARVEST: TAX-FREE (+$869) | SELL NOW |
| 3 | VEA | INTERNATIONAL overweight +6.6% | HARVEST: TAX-FREE (+$596) | SELL NOW |
| 4 | FIGFX | INTERNATIONAL overweight +6.6% | HARVEST: TAX-FREE (+$151) | SELL NOW |

All four INTERNATIONAL holdings have gains within capacity — excellent execution window. No deferral needed. Tax context elevates urgency: NOW is the low-cost time to rebalance.

Within Category 5 (Loss Harvest), tax context confirms and elevates:

| Priority | Symbol | Loss | Tax Context | Recommended Timing |
|---|---|---|---|---|
| 1 | FIS | −$14,344 | HARVEST: ADDS CAPACITY | SELL NOW |

---

## What Tax Context Does NOT Do

Tax context must not:
1. **Create a category** — a holding is not a sell candidate because it has a gain. A gain is only tax context for a candidate identified by other logic.
2. **Block a category** — a holding with a taxable gain is still a Category 1 or 2 candidate if signal or strategic factors warrant it. The tax label changes from "TAX-FREE" to "SELL: LONG-TERM GAIN" — it does not remove the candidate.
3. **Reorder across categories** — tax context ranks within a category, not between categories. A HARVEST: TAX-FREE Cat 3 candidate does not outrank a HIGH priority Cat 2 strategic exit candidate.

---

## Tax Context When Cost Basis Is Unavailable

Phase 23.0B design does not add cost basis to the overlay (that is Phase 23.0C scope). Until cost basis is available:

- Candidates still appear in their respective categories based on signal/allocation/strategic logic
- Tax Context column shows `NO COST BASIS` as a disclosure label
- Timing recommendation defaults to `REVIEW MANUALLY`
- This is strictly better than the current behavior (candidates don't appear at all when cost basis is unavailable)

**The operator sees the action candidate. They are informed that tax context is unavailable for that specific holding. They can still decide whether to act.** The current framework hides the candidate entirely — which is worse than surfacing it with an incomplete tax label.

---

## Summary: Tax Context Integration Rules

| Rule | Description |
|---|---|
| T1 | Tax context modifies ranking within categories; does not create or exclude candidates |
| T2 | Gains ≤ available capacity → HARVEST: TAX-FREE label → elevate timing urgency |
| T3 | Unrealized losses → HARVEST: ADDS CAPACITY → highest tax-context priority within category |
| T4 | Gains beyond capacity → label appropriately (LT/ST); do not suppress |
| T5 | Near LT threshold → add deferral advisory; candidate remains visible |
| T6 | No cost basis → label as NO COST BASIS; candidate remains visible |
| T7 | Capacity is consumed cumulatively — track across all candidates as gains are added |
| T8 | Capacity does not govern candidate visibility — only label and timing |
