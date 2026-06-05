# Phase 23.0A.1 — Q2: Action Bucket Validation

**Validation Question**: Does the 5-bucket prioritization logic produce correct outputs for all defined scenarios?

---

## Bucket Definitions

| Bucket | Label | Timing Signal | Trigger Condition |
|---|---|---|---|
| A | SELL NOW | SELL_NOW | Poor outlook + gain (shielded or long-term) OR poor outlook + no cost basis |
| B | SELL WHEN LONG-TERM | WAIT | Poor outlook + short-term gain (approaching LT threshold) |
| C | SELL FOR REBALANCING | SELL_NOW or HARVEST_LOSS | Reduce candidate (mandate drift) |
| D | HARVEST LOSS | HARVEST_LOSS | Poor outlook + unrealized loss |
| E | HOLD DESPITE GAIN | HOLD_DESPITE_GAIN | Buy candidate + unrealized gain |

---

## Preconditions

```js
// Implemented in _computeTaxActions() — app.js line 327
const isPoorOutlook    = signal === "BEARISH" || flag === "TRIM";
const isBuyCandidate   = cwdas === "BUY"      || signal === "BULLISH";
const isReduceCandidate = flag === "TRIM"     || flag === "REDUCE_CANDIDATE";
const gainShielded     = available > 0 && unrealizedGL != null && unrealizedGL > 0 && unrealizedGL <= available;
```

---

## Branch-by-Branch Trace

The `if/else if` chain processes each security in this priority order:

### Check 1 (Bucket D): Harvest Loss
```
unrealizedGL != null && unrealizedGL < 0 && isPoorOutlook → Bucket D / HARVEST_LOSS
```
**Confirmed correct.** Requires: cost basis present, loss position, poor outlook. All three conditions checked.

### Check 2 (Bucket E): Hold Despite Gain
```
isBuyCandidate && unrealizedGL != null && unrealizedGL > 0 → Bucket E / HOLD_DESPITE_GAIN
```
**Confirmed correct.** Catch: if a security is simultaneously `isBuyCandidate` AND `isPoorOutlook` (e.g., `cwdas === "BUY"` with `signal === "BEARISH"`), Check 1 fires first for loss positions. For gain positions, Check 2 fires before Check 3 — so a BULLISH signal overrides poor outlook for gain positions, assigning Bucket E. This is the intended precedence: bullish conviction takes priority over trim flag.

### Check 3 (Buckets A or B): Poor Outlook + Gain
```
isPoorOutlook && unrealizedGL != null && unrealizedGL > 0 →
  if gainShielded → Bucket A / SELL_NOW ("gain fully shielded")
  else if isLongTerm === false → Bucket B / WAIT ("short-term, approaching LT")
  else → Bucket A / SELL_NOW ("long-term gain at favorable rate")
```
**Confirmed correct for defined cases.** Edge case documented below.

### Check 4 (Bucket C): Reduce Candidate
```
isReduceCandidate →
  Bucket C / SELL_NOW (if unrealizedGL > 0) or HARVEST_LOSS (otherwise)
```
**Design ambiguity: `flag === "TRIM"` is redundant in `isReduceCandidate`.**

`isPoorOutlook` also includes `flag === "TRIM"`. A TRIM holding will always be caught by Checks 1, 3, or 5 before reaching Check 4. The TRIM clause in `isReduceCandidate` is unreachable code under the current branch order. Bucket C fires in practice only for `flag === "REDUCE_CANDIDATE"`.

This is not a logic error — Bucket C with `REDUCE_CANDIDATE` is correct behavior. The unreachable TRIM branch in Check 4 creates minor confusion but no incorrect outcomes.

### Check 5 (Bucket A fallback): Poor Outlook, No Cost Basis
```
isPoorOutlook && unrealizedGL == null → Bucket A / SELL_NOW ("cost basis unavailable")
```
**Confirmed correct.** This is the signal-only path for holdings without portfolio cost basis data.

---

## Edge Cases and Gaps

### Edge Case 1: Missing Holding Period (Most Common Data Gap)

When `holding_days` is not present in the portfolio export:
```js
const holdingDays = parseFloat(ov.holding_days ?? "") || null;
const isLongTerm  = holdingDays != null ? holdingDays >= 365 : null;
```

If `holding_days` is absent → `holdingDays = null` → `isLongTerm = null`.

In Check 3:
```
else if (isLongTerm === false) → false  (null !== false)
else → Bucket A / SELL_NOW
```

**Implication:** A security with a poor outlook, an unrealized gain, and an unknown holding period defaults to Bucket A (SELL NOW). This is a **conservative default** — it does not suppress the action. However, it may prematurely classify short-term gains for immediate sale when waiting would produce a lower tax rate.

**Advisory:** This is acceptable behavior but should be disclosed to operators: "Holding period not available — defaulted to SELL NOW; verify before acting."

Bucket B (WAIT) is effectively unavailable without `holding_days` data in the portfolio export.

### Edge Case 2: Bucket B Threshold Not Communicated

Bucket B fires when a gain is short-term (`isLongTerm === false` = `holding_days < 365`). The table shows "holding period" (days + ST/LT badge) but does NOT show how many days remain until long-term treatment. A "days to LT" column would improve actionability.

**Advisory:** Consider adding `days_to_lt = max(0, 365 - holding_days)` as a derived column in Bucket B rows.

### Edge Case 3: Gain Exactly at Loss Limit

When `unrealizedGL === available` (gain exactly equals available capacity), `gainShielded = true`. Bucket A fires (SELL NOW — gain fully shielded). This is correct.

When `unrealizedGL > available > 0` (partial shield — gain exceeds available capacity), `gainShielded = false`. The security falls to the `isLongTerm` branch. No partial-shield signal is surfaced. The operator must infer partial shield from the table columns.

**Advisory:** A future enhancement could flag "partially shielded" when `0 < available < unrealizedGL`, with a reason note. Not required for MVP.

### Edge Case 4: Negative `net_realized_ytd` with Scenario Where No Tax State Is Saved

With all tax inputs at 0 (empty panel), `available = 0`, `gainShielded = false`. The table still renders with signal-based bucketing. No incorrect assignments occur. Tax capacity context is simply absent from the rendering.

---

## Test Matrix

| Symbol | Signal | Flag | CW-DAS | UnrealizedGL | isLongTerm | Tax State | Expected Bucket | Verified |
|---|---|---|---|---|---|---|---|---|
| AAA | BEARISH | — | — | -8,000 | false | any | D (Harvest Loss) | ✓ |
| BBB | BEARISH | — | — | +15,000 | true | available=0 | A (Sell Now — LT rate) | ✓ |
| CCC | BEARISH | — | — | +12,000 | false | available=0 | B (Wait — ST) | ✓ |
| DDD | BEARISH | — | — | +8,000 | true | available=10,000 | A (Sell Now — shielded) | ✓ |
| EEE | BULLISH | — | BUY | +5,000 | true | any | E (Hold Despite Gain) | ✓ |
| FFF | NEUTRAL | — | — | +10,000 | true | any | (no bucket) | ✓ |
| GGG | NEUTRAL | REDUCE_CANDIDATE | — | null | null | any | C (Sell for Rebalancing) | ✓ |
| HHH | BEARISH | — | — | null | null | any | A (no cost basis fallback) | ✓ |
| III | BEARISH | — | — | +8,000 | null | any | A (missing period — conservative) | ✓ |

---

## Verdict: Q2

| Check | Result |
|---|---|
| Bucket A — sell now (shielded gain) | ✓ PASS |
| Bucket A — sell now (long-term gain) | ✓ PASS |
| Bucket A — sell now (no cost basis) | ✓ PASS |
| Bucket B — wait (short-term gain) | ✓ PASS |
| Bucket C — reduce candidate | ✓ PASS |
| Bucket D — harvest loss | ✓ PASS |
| Bucket E — hold despite gain | ✓ PASS |
| Missing holding period → conservative Bucket A fallback | ✓ PASS (documented) |
| Partial gain shield (no explicit flag) | ⚠ ADVISORY — enhancement opportunity |
| `isReduceCandidate` TRIM branch unreachable | ⚠ ADVISORY — dead code, not an error |
| No "days to LT" in Bucket B rows | ⚠ ADVISORY — UX enhancement opportunity |

**Q2 Status: PASS — 3 advisories documented (no functional defects).**
