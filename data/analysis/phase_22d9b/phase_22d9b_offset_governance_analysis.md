# Phase 22D.9B — Q6: Offset Governance Analysis

**Phase:** 22D.9B — ACCOUNTING_ADJUSTMENT Taxonomy Audit  
**Date:** 2026-06-02  
**Question:** What governance structure — operational_state alone, or an explicit
safe_to_offset_cash attribute — should drive the Option C settlement offset?

---

## The Governance Question

Phase 22D.9A's proposed Option C uses `operational_state == "ACCOUNTING_ADJUSTMENT"`
as the filter to select rows that should reduce deployable cash. This document
evaluates whether that is a sufficient governance signal, or whether an explicit
`safe_to_offset_cash` attribute is required.

---

## Option A: Drive Offset from operational_state Alone

**Formula (current Option C proposal):**

```python
adjustment = sum(
    abs(h.market_value)
    for h in non_investable
    if h.operational_state == "ACCOUNTING_ADJUSTMENT" and h.market_value < 0
)
adjusted_deployable_mv = deployable_mv - adjustment
```

**Safety evaluation for observed data:**

| Row Class | Count | mv < 0? | Included in offset? | Correct? |
|-----------|-------|---------|---------------------|---------|
| A — Pending purchase | 36 | YES | YES | ✓ CORRECT |
| C — Net-zero transfer | 6 | NO (mv=0) | NO | ✓ CORRECT (noop) |
| **Total impact** | **42** | — | **36 rows, -$60,199.65** | **100% CORRECT** |

**Safety evaluation for unobserved/theoretical data:**

| Theoretical Class | Would mv < 0? | Included in offset? | Correct? |
|-------------------|-------------|---------------------|---------|
| B — Pending sale (structural impossibility today) | NO (mv > 0, classified ACTIVE_POSITION) | NO | ✓ Protected by classification logic |
| C' — Symmetric transfer with missing positive row (1 row instead of 2) | YES | YES | ✗ INCORRECT (double-counts transfer) |
| D — Dividend accrual (if labeled as Pending activity) | Unlikely mv < 0 | Probably NO | Ambiguous |
| E — Corporate action cash obligation | POSSIBLE mv < 0 | YES if mv < 0 | ✗ UNKNOWN — could be incorrect |
| F — Fidelity bookkeeping artifact with negative mv | YES | YES | ✗ INCORRECT |

**Assessment of Option A:**
- Correct for 100% of observed data
- Has structural protection against the most likely incorrect case (Class B)
- Has no protection against Classes C', E, F if they appear
- The `mv < 0` filter is the only governance constraint

**Option A verdict:** ACCEPTABLE for current portfolio; INSUFFICIENT for production governance.

---

## Option B: Drive Offset from safe_to_offset_cash Attribute

**Formula (proposed governance-aware Option C):**

```python
adjustment = sum(
    abs(h.market_value)
    for h in non_investable
    if h.safe_to_offset_cash
)
adjusted_deployable_mv = deployable_mv - adjustment
```

**Safety evaluation for observed data:**

| Row Class | safe_to_offset_cash? | Included in offset? | Correct? |
|-----------|----------------------|---------------------|---------|
| A — Pending purchase (mv < 0) | TRUE | YES | ✓ CORRECT |
| C — Net-zero transfer (mv = 0) | FALSE (mv not < 0) | NO | ✓ CORRECT (noop) |
| **Total impact** | — | **36 rows, -$60,199.65** | **100% CORRECT** |

**Safety evaluation for unobserved/theoretical data:**

| Theoretical Class | safe_to_offset_cash (default)? | Included in offset? | Correct? |
|------------------|-------------------------------|---------------------|---------|
| B — Pending sale | FALSE (default) | NO | ✓ Protected |
| C' — Missing counterpart | FALSE (default) | NO | ✓ Protected |
| D — Dividend accrual | FALSE (default) | NO | ✓ Protected |
| E — Corporate action | FALSE (default until explicitly reviewed) | NO | ✓ Protected |
| F — Fidelity artifact | FALSE (default) | NO | ✓ Protected |

**Option B verdict:** CORRECT for observed data AND provides explicit governance
protection against all unobserved theoretical cases.

---

## Comparative Analysis

| Criterion | Option A (operational_state) | Option B (safe_to_offset_cash) |
|-----------|------------------------------|-------------------------------|
| Correct for observed data? | YES | YES |
| Protects against Class B? | YES (structural) | YES (explicit) |
| Protects against Class C' (missing pair)? | NO | YES (default False) |
| Protects against Class E (corporate action)? | NO | YES (default False) |
| Implementation complexity | LOWER | SLIGHTLY HIGHER |
| Auditability (can operator verify?) | Implicit (must know classification logic) | Explicit (column in holdings.csv) |
| Backward compatible? | YES | YES (new column with default) |
| Requires schema change? | NO | YES (new PortfolioHolding field) |
| Future-proof for new Fidelity formats? | NO — new patterns with mv < 0 auto-include | YES — new patterns default to safe_to_offset_cash=False |
| Governance provenance in holdings.csv? | NO | YES |

---

## Recommended Governance Structure

**Recommendation: Option B (safe_to_offset_cash) as the long-term governance
standard, implemented alongside Option C in Phase 22D.10.**

**Rationale for Option B:**

1. **Default-safe:** New ACCOUNTING_ADJUSTMENT patterns discovered in the future
   will default to `safe_to_offset_cash = False`, requiring an explicit governance
   decision to include them in offsets.

2. **Auditable:** The boolean appears in holdings.csv exports, enabling
   operators to verify which rows drove the cash offset without reading code.

3. **Documents the intent, not just the condition:** `safe_to_offset_cash = True`
   communicates that this row has been reviewed and approved for cash offset, as
   opposed to `market_value < 0` which is a technical condition that happens to
   proxy for the right thing today.

4. **Incremental overhead is low:** Adding one boolean field to PortfolioHolding
   with a default value requires ~15 lines of code changes.

**Implementation sequence:**

1. Add `safe_to_offset_cash: bool = False` to PortfolioHolding (dataclass field).
2. In `_classify_operational_state()` or post-enrichment, set
   `safe_to_offset_cash = True` for rows where `operational_state == "ACCOUNTING_ADJUSTMENT"
   and market_value < 0`.
3. Update Option C formula in runner.py to filter on `h.safe_to_offset_cash`.
4. Update holdings.csv schema to include new column.
5. Update test assertions.

**Interim compatibility:** During Phase 22D.10, both Option A logic and Option B
logic produce identical results for current data. Option A logic (`mv < 0` filter)
can be the fallback if the schema change is deferred.

---

## Governance Gap Statement

The current codebase has NO explicit governance mechanism for the cash offset
decision. The `ACCOUNTING_ADJUSTMENT` operational state was designed to mark rows
for exclusion from investable portfolio calculations — it was not designed to signal
that a row should reduce deployable cash. Repurposing it for Option C is pragmatic
but introduces implicit coupling between a classification state and a cash offset
decision.

**The `safe_to_offset_cash` attribute breaks this implicit coupling and makes the
governance decision an explicit, first-class data attribute.**
