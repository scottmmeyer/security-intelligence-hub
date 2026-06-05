# Phase 23.6B.2 — Capital Pool Fix

**Date:** 2026-06-04

---

## Defect Description

CRA capital pool included two non-tradeable artifacts as sell candidates:

| Symbol | Market Value | Inclusion Amount | Root Cause |
|--------|-------------|-----------------|-----------|
| SPAXX | $44,049 | $11,012 (25% sizing) | `is_cash_equivalent=True` not checked |
| PENDING ACTIVITY | $10,205 | $2,551 (25% sizing) | Settlement row classified as `ACTIVE_POSITION` |

Pool overstatement: **$13,563 (13.8% of total pool)**

---

## Fix Location

`src/portfolio/cra/capital_source_builder.py` — `build_capital_sources()` function

---

## Implementation

A `non_tradeable` exclusion set is built before any category detection loop:

### Layer 1: Field-based exclusion (existing portfolio classification fields)
```python
_ACTIVE_OP_STATES = frozenset({"ACTIVE_POSITION", ""})
non_tradeable = frozenset(
    _sym(h) for h in holdings
    if _bool_field(h.get("is_cash_equivalent"))
    or (h.get("operational_state") or "") not in _ACTIVE_OP_STATES
    or _bool_field(h.get("safe_to_offset_cash"))
)
```

Catches: SPAXX (`is_cash_equivalent=True`), and any row with operational_state ∈ {CASH_EQUIVALENT, PENDING_SETTLEMENT, ACCOUNTING_ADJUSTMENT, CLOSED_POSITION, NON_ANALYZABLE}.

### Layer 2: Symbol-pattern exclusion (defensive fallback for ambiguously-classified rows)
```python
_NON_TRADEABLE_PATTERNS = ("PENDING", "ACTIVITY", "CONTRA", "M26CNT", "CYBERARK SOFTWA F")
non_tradeable = non_tradeable | frozenset(
    _sym(h) for h in holdings
    if any(p in (_sym(h) or "").upper() for p in _NON_TRADEABLE_PATTERNS)
)
```

Catches: PENDING ACTIVITY (classified as ACTIVE_POSITION due to positive MV in the ingestion layer, but identified by name pattern), M26CNT legacy contra rows, and similar Fidelity CSV placeholder symbols.

### Guard in every category loop
Each of the 5 category detection loops now begins with:
```python
if sym in non_tradeable:
    continue
```

---

## Before / After

| Metric | Before (defective) | After (fixed) |
|--------|-------------------|---------------|
| SPAXX in sources | Yes ($11,012) | No |
| PENDING ACTIVITY in sources | Yes ($2,551) | No |
| Capital pool | $98,644 | $85,081 |
| Pool overstatement | +$13,563 | $0 |

---

## Non-Negotiables

- No modification to portfolio ingestion classifications
- No modification to how holdings.csv is written or how operational_state is assigned
- CRA reads existing fields as-is; the exclusion is purely in the CRA composition layer
