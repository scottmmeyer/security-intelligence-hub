# Phase 22D.9B — Q5: Taxonomy Evolution Analysis

**Phase:** 22D.9B — ACCOUNTING_ADJUSTMENT Taxonomy Audit  
**Date:** 2026-06-02  
**Question:** Should the ACCOUNTING_ADJUSTMENT taxonomy be subdivided into more
granular types? If yes, what subtypes are needed, and what rule would distinguish them?

---

## Current Taxonomy (Single State)

```
operational_state = "ACCOUNTING_ADJUSTMENT"
```

**Current classification rule (src/portfolio/ingestion.py lines 325–339):**

```python
def _classify_operational_state(sym, desc, mv):
    desc_upper = desc.upper()
    if any(kw in desc_upper for kw in _PENDING_DESCRIPTION_KEYWORDS) or sym == "PENDING":
        return "PENDING_SETTLEMENT"
    if mv is not None and mv < 0:
        return "ACCOUNTING_ADJUSTMENT"
    if mv is not None and mv == 0:
        return "CLOSED_POSITION"
    return "ACTIVE_POSITION"
```

**Coverage:** ACCOUNTING_ADJUSTMENT applies to ANY row with negative market value
that is not already matched as PENDING_SETTLEMENT. It is a catch-all for negatives.

**Problem:** The single state makes it impossible to distinguish:
1. A pending purchase settlement (safe to offset against deployable cash)
2. A net-zero transfer artifact (irrelevant to deployable cash)
3. A future corporate action cash obligation (unknown offset behavior)

---

## Observed Classification Distribution

| Current State | Underlying Reality | Rows | % |
|---------------|-------------------|------|---|
| ACCOUNTING_ADJUSTMENT (mv < 0) | Pending purchase settlement | 36 | 85.7% |
| ACCOUNTING_ADJUSTMENT (mv = 0) | Net-zero transfer artifact | 6 | 14.3% |
| (Total) | | 42 | 100% |

---

## Proposed Subtype Taxonomy

### Option 1: Operational State Subtypes (String-Based)

Extend the `operational_state` value to carry subtype information:

```
ACCOUNTING_ADJUSTMENT                   ← current; preserve for backward compat
ACCOUNTING_ADJUSTMENT.PENDING_PURCHASE  ← Class A; safe to offset
ACCOUNTING_ADJUSTMENT.CASH_TRANSFER     ← Class C; net zero, irrelevant
ACCOUNTING_ADJUSTMENT.PENDING_SALE      ← Class B (unobserved); cash incoming
ACCOUNTING_ADJUSTMENT.CORPORATE_ACTION  ← Class E (unobserved); case-by-case
ACCOUNTING_ADJUSTMENT.UNKNOWN           ← catch-all for new patterns
```

**Pros:** Self-documenting, searchable in CSVs and JSON.  
**Cons:** String-based subtypes are fragile to parse; requires downstream code
changes to parse `.`-suffixed values; breaks backward compatibility of
`operational_state` enum comparisons.

### Option 2: Boolean Governance Attribute (Recommended)

Add a new boolean column `safe_to_offset_cash` to the PortfolioHolding dataclass:

```python
@dataclasses.dataclass
class PortfolioHolding:
    ...
    safe_to_offset_cash: bool = False   # New field
```

**Classification rules (in _classify_operational_state or post-processing):**

| Condition | safe_to_offset_cash |
|-----------|---------------------|
| operational_state == "ACCOUNTING_ADJUSTMENT" AND mv < 0 AND known single-account negative (pending purchase) | `True` |
| operational_state == "ACCOUNTING_ADJUSTMENT" AND mv == 0 (net-zero transfer) | `False` (noop anyway) |
| operational_state == "ACCOUNTING_ADJUSTMENT" AND mv > 0 (pending sale — structural impossibility today) | `False` |
| Any other operational_state | `False` |
| Unknown / unclassified type | `False` (conservative default) |

**Pros:** Explicit governance intent; backward compatible (doesn't change existing
enum values); allows per-row override; default `False` is conservative.  
**Cons:** Requires new schema column; adds complexity to PortfolioHolding.

### Option 3: Subtype String Field

Add `accounting_adjustment_subtype: str | None` to PortfolioHolding:

```
"PENDING_PURCHASE"   ← Class A
"CASH_TRANSFER"      ← Class C
"PENDING_SALE"       ← Class B (unobserved)
"CORPORATE_ACTION"   ← Class E (unobserved)
None                 ← non-ACCOUNTING_ADJUSTMENT rows
```

**Pros:** Human-readable, supports future programmatic routing.  
**Cons:** Nullable field; requires handling None cases throughout downstream code.

---

## Recommended Approach: Option 2 (Boolean Governance Attribute)

**Rationale:**

1. **Simplest to implement correctly:** Option C's formula only needs `safe_to_offset_cash`
   to select which rows to include in the offset. No string parsing required.

2. **Conservative default:** New/unknown rows default to `False`, preventing
   incorrect offsets when new Fidelity CSV patterns appear.

3. **Explicit governance provenance:** The attribute documents the decision to
   offset, not just the operational state. Future code readers see the intent.

4. **Backward compatible:** Existing `operational_state` values and consumers
   are unchanged.

5. **Observable in output:** `safe_to_offset_cash = true` in holdings.csv
   makes it auditable — operators can verify which rows drove the offset.

---

## Classification Rules for safe_to_offset_cash

### Rule 1: Standalone Negative Pending Activity (Observed Pattern → Class A)

```python
def _classify_safe_to_offset_cash(row):
    if row.operational_state != "ACCOUNTING_ADJUSTMENT":
        return False
    if row.market_value < 0:
        # Class A: pending purchase settlement
        # Conservative assumption: any negative ACCOUNTING_ADJUSTMENT
        # row is a purchase commitment unless otherwise known
        return True
    return False  # mv == 0 or mv > 0 → no offset needed/safe
```

This rule is sufficient for all 36 observed Class A rows and harmless for all
6 Class C rows (MV=0 → safe_to_offset_cash would return True but offset = $0).

### Rule 2 (Future Enhancement): Symmetric Pair Detection

To distinguish Class A (genuine purchase) from Class C (symmetric transfer that
happens to produce a negative-MV row before netting), the ingestion pipeline would
need to track whether a symbol was seen with both negative and positive pending
activity in the same export. If so, flag as `CASH_TRANSFER` and set
`safe_to_offset_cash = False`.

This requires analysis at the `_parse_fidelity()` level before row-level
classification — a more significant change than Rule 1.

**Current impact of deferring Rule 2:**
- Class C rows currently have MV=0 after aggregation, so `safe_to_offset_cash=True`
  would still offset $0 (harmless)
- The only scenario where Rule 2 matters is if a symmetric pair produces a net
  NEGATIVE (e.g., if one of the pair rows is missing). Not observed in 42 rows.

---

## Backward Compatibility Analysis

| Component | Impact of Option 2 | Migration Required |
|-----------|---------------------|---------------------|
| holdings.csv schema | New column `safe_to_offset_cash` | Add column; existing readers can ignore |
| PortfolioHolding dataclass | New field with default `False` | Source-level change; downstream OK |
| runner.py Option C filter | Change from `operational_state` check to `safe_to_offset_cash` check | One-line change |
| UI (holdings display) | New column available; no required change | Optional future display |
| Test assertions on holdings | Tests using exact column counts need update | ~3 test files |
| snapshot.json | PortfolioHolding fields serialized; new field appears | No breaking change |

---

## Governance Recommendation

**Short-term (Phase 22D.10):** Implement Option 2 Rule 1 simultaneously with
Option C. The `safe_to_offset_cash = True` condition for negative-MV ACCOUNTING_ADJUSTMENT
rows is equivalent to the `market_value < 0` filter in Option C, but makes the
governance decision explicit and auditable.

**Medium-term (Phase 22D.11+):** Evaluate Rule 2 (symmetric pair detection) only
if symmetric transfer patterns produce materially incorrect offsets. Based on
observed data (zero harm from Class C rows), this is low priority.

**Long-term:** Maintain a classification register (`config/accounting_adjustment_registry.yaml`)
that maps observed row patterns to explicit `safe_to_offset_cash` verdicts, reviewed
quarterly or when new Fidelity export formats are introduced.
