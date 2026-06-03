# Phase 22D.9B — Q3: Positive Adjustment Assessment

**Phase:** 22D.9B — ACCOUNTING_ADJUSTMENT Taxonomy Audit  
**Date:** 2026-06-02  
**Question:** Have any positive ACCOUNTING_ADJUSTMENT rows ever been observed?

---

## Definition of "Positive"

For this assessment, "positive" means an ACCOUNTING_ADJUSTMENT row with:

- `market_value > 0` (explicit positive balance in processed holdings)  
- or a raw Fidelity "Pending activity" row with positive dollar value prior to
  aggregation

---

## Finding 1: Processed Holdings (operational_state = ACCOUNTING_ADJUSTMENT)

**Positive ACCOUNTING_ADJUSTMENT rows in holdings.csv: ZERO**

Across 42 total ACCOUNTING_ADJUSTMENT rows in 9 portfolio snapshots:

| MV Polarity | Count | % |
|-------------|-------|---|
| Negative (< 0) | 36 | 85.7% |
| Zero (= 0) | 6 | 14.3% |
| Positive (> 0) | **0** | **0%** |

No positive-MV ACCOUNTING_ADJUSTMENT row has ever appeared in a processed
holdings.csv file in any analysis run.

---

## Finding 2: Raw Fidelity CSV Archive

**Positive "Pending activity" rows in raw Fidelity CSVs: YES — but only as symmetric offsets**

The raw Fidelity CSV archive (35+ files across 6 dates) contains positive "Pending
activity" entries in 6 files:

| Source Archive File Pattern | Positive Row | Account | Amount |
|-----------------------------|-------------|---------|--------|
| Portfolio_Positions_May-22-2026.csv (×6 runs) | `Pending activity` | Z35123695 (Individual TOD) | +$4,344.91 |
| audit_test.csv (×4 runs) | `Pending activity` | Z35123695 (Individual TOD) | +$4,236.41 |
| 2026-05-29T04-28-57_PAR-...Portfolio_May-28-2026 (1).csv | `Pending activity` | Z35123695 | +$4,236.41 |

In **every case**, the positive raw entry is paired with an equal and opposite
negative entry in a different account (X20548022, General Brokerage):

```
X20548022,General Brokerage,Pending activity,,,,,-$4,344.91   ← ACCOUNTING_ADJUSTMENT
Z35123695,Individual - TOD,Pending activity,,,,,+$4,344.91    ← ACTIVE_POSITION
```

After `normalize_and_aggregate_holdings()` sums both rows:

```
PENDING ACTIVITY  aggregate MV = -4344.91 + 4344.91 = 0.00 → ACCOUNTING_ADJUSTMENT
```

The positive row is classified as **ACTIVE_POSITION** (not ACCOUNTING_ADJUSTMENT)
because `_classify_operational_state()` only assigns ACCOUNTING_ADJUSTMENT to
rows with `mv < 0`. The classification check is:

```python
if mv is not None and mv < 0:
    return "ACCOUNTING_ADJUSTMENT"
```

So positive pending activity rows never carry `ACCOUNTING_ADJUSTMENT` as their
`_operational_state` — they arrive as `ACTIVE_POSITION` and are then aggregated
with the corresponding negative row.

---

## Finding 3: Classification Logic Constraint

The `_classify_operational_state()` function in `src/portfolio/ingestion.py`
lines 325–339 makes it **structurally impossible** for a positive-MV row to
receive the `ACCOUNTING_ADJUSTMENT` classification:

```python
def _classify_operational_state(sym, desc, mv):
    # PENDING_SETTLEMENT check first (description keywords)
    if any(kw in desc_upper for kw in _PENDING_DESCRIPTION_KEYWORDS) or sym == "PENDING":
        return "PENDING_SETTLEMENT"
    if mv is not None and mv < 0:       ← Only negative → ACCOUNTING_ADJUSTMENT
        return "ACCOUNTING_ADJUSTMENT"
    if mv is not None and mv == 0:
        return "CLOSED_POSITION"
    return "ACTIVE_POSITION"            ← Positive → ACTIVE_POSITION
```

A positive-MV "Pending activity" row would be classified as `ACTIVE_POSITION`
by this logic, regardless of its origin.

---

## Theoretical Positive Adjustment Scenarios

The following positive-adjustment scenarios have NOT been observed but are
theoretically possible:

| Scenario | Fidelity Row Pattern | Would Appear As | Impact on Deployable Cash |
|----------|----------------------|-----------------|---------------------------|
| Pending sale proceeds | +$X, single account | ACTIVE_POSITION (not ACCOUNTING_ADJUSTMENT) | Would ADD to cash_mv (via SPAXX not yet updated) |
| Pending dividend credit | +$X dividend | ACTIVE_POSITION | No impact on ACCOUNTING_ADJUSTMENT path |
| Error reversal of prior debit | +$X, same day | Could net prior negative to zero | Net zero ACCOUNTING_ADJUSTMENT |
| Wire transfer incoming | +$X, Individual TOD | ACTIVE_POSITION | Would ADD to portfolio total MV |
| Options exercise proceeds | +$X | ACTIVE_POSITION | No specific accounting treatment |

**Key observation:** Under the current classification logic, none of these scenarios
would produce a positive ACCOUNTING_ADJUSTMENT. They would all be ACTIVE_POSITION
or net to zero after aggregation.

---

## Dollar Exposure Summary

| Category | Count | Dollar Exposure |
|----------|-------|-----------------|
| Positive ACCOUNTING_ADJUSTMENT in holdings.csv | 0 | $0.00 |
| Positive "Pending activity" in raw CSVs | 10+ rows | +$4,344.91 to +$4,236.41 (all symmetric offset) |
| Net positive ACCOUNTING_ADJUSTMENT exposure | 0 | $0.00 |

---

## Risk Assessment

**Current risk: LOW**

The classification logic structurally prevents positive-MV rows from entering
the ACCOUNTING_ADJUSTMENT category. Any positive "Pending activity" rows that
have appeared in raw Fidelity exports have been either:

1. Netted to zero by `normalize_and_aggregate_holdings()` (symmetric transfers)
2. Classified as ACTIVE_POSITION (standalone positive pending activity)

In either case, they do not affect the `ACCOUNTING_ADJUSTMENT` path that drives
Option C's cash offset calculation.

**Future risk: PRESENT but LOW**

If Fidelity ever exports a standalone positive "Pending activity" row that does
NOT have a negative counterpart (e.g., pure pending sale proceeds labeled as
"Pending activity"), it would be misclassified as ACTIVE_POSITION and counted
as a regular holding. This would slightly inflate `total_market_value` but
would not produce a spurious positive ACCOUNTING_ADJUSTMENT.

This scenario would not cause Option C to over-reduce deployable cash. The risk
direction is reversed: deployable cash would be very slightly overstated
(positive pending proceeds treated as a real holding).
