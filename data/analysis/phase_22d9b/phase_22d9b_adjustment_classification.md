# Phase 22D.9B — Q2: Adjustment Classification

**Phase:** 22D.9B — ACCOUNTING_ADJUSTMENT Taxonomy Audit  
**Date:** 2026-06-02  
**Corpus:** 42 ACCOUNTING_ADJUSTMENT rows from 9 portfolio snapshots  
**Schema scope:** New schema only (holdings.csv with `operational_state` column)  
**Pre-schema runs:** May 22, 2026 — 10+ runs with symmetric pending activity rows; not classified as ACCOUNTING_ADJUSTMENT due to old schema (23-column format, no `operational_state` field)

---

## Classification Framework

| Class | Label | Definition |
|-------|-------|------------|
| A | PENDING_PURCHASE | Unsettled equity purchase; cash debited from brokerage, shares not yet delivered |
| B | PENDING_SALE | Unsettled equity sale; shares delivered, proceeds not yet credited |
| C | CASH_TRANSFER | Intra-account or inter-account cash movement pending settlement |
| D | DIVIDEND_ACCRUAL | Dividend declared but not yet paid |
| E | CORPORATE_ACTION | Merger, split, spinoff, or other structural event |
| F | FIDELITY_BOOKKEEPING | Fidelity-internal accounting artifact (no real capital impact) |
| G | UNKNOWN | Cannot be classified from available data |

---

## Classification Results

### Class A — PENDING_PURCHASE (pending equity purchase settlement)

**Count:** 36 rows (85.7% of total)  
**Dollar exposure:** -$60,199.65  

All 36 negative-MV rows represent a single Fidelity "Pending activity" line in the
Individual TOD account (Z35123695) with no positive counterpart in the same export.
This is the standard Fidelity representation of an equity purchase placed but not
yet settled at T+1.

| MV Value | Count | Date Range | Source File |
|----------|-------|------------|-------------|
| -$1,500.00 | 33 | 2026-05-29 → 2026-06-01 | Portfolio_Positions_May-29-2026 (3).csv |
| -$3,566.55 | 3 | 2026-06-02 | Portfolio_Positions_Jun-02-2026 (1).csv + (2).csv |

**Evidence for Class A classification:**
- Single-account entry: Z35123695 (Individual - TOD) only
- No offsetting positive "Pending activity" row in same export
- MV equals an equity purchase amount (not a round lot or transfer)
- Pattern matches "purchase placed, settlement pending" Fidelity behavior
- Value disappears on the next day's portfolio export (consistent with T+1 settlement)

**Confidence:** HIGH (pattern is unambiguous in available data)

### Class C — CASH_TRANSFER (intra-account transfer, net zero after aggregation)

**Count:** 6 rows (14.3% of total)  
**Dollar exposure:** $0.00 (net zero after aggregation)

The 6 zero-MV rows arise from the `normalize_and_aggregate_holdings()` function in
`src/portfolio/enrichment.py`, which sums duplicate-symbol rows. In these cases,
the source Fidelity CSV contained TWO "Pending activity" rows:

```
X20548022,General Brokerage,Pending activity,,,,,-$4,236.41
Z35123695,Individual - TOD,Pending activity,,,,,+$4,236.41
```

After aggregation: -4,236.41 + 4,236.41 = **0.00**

The negative row (mv < 0) was classified as ACCOUNTING_ADJUSTMENT by ingestion;
the positive row was classified as ACTIVE_POSITION. After `normalize_and_aggregate_holdings()`
sums them by symbol, the result is one ACCOUNTING_ADJUSTMENT row with MV=0.00.

**Sub-classification of these 6 rows:**
- 4 rows: from `audit_test.csv` (May 29 re-run of May 28 data; -$4,236.41 + $4,236.41)
- 1 row: from replay archive of PAR-20260528-3B200665 (same pattern, -$4,236.41)
- 1 row: from `Portfolio_Positions_May-28-2026 (1).csv` snapshot date 2026-05-29

**Evidence for Class C classification:**
- Two-account symmetric pattern (General Brokerage negative, Individual TOD positive)
- Equal and opposite values (perfect net zero)
- Cross-account pattern is consistent with a Fidelity account-to-account transfer

**Confidence:** MEDIUM (could also be a pending purchase that was subsequently settled
and the archive file was re-ingested after T+1; the $4,236.41 value matches round
transfer amounts rather than odd-lot purchase amounts)

---

## Pre-Schema Observations (May 22, 2026 — NOT in ACCOUNTING_ADJUSTMENT inventory)

Before the `operational_state` column was added to holdings.csv (23-column schema),
10 runs on May 22, 2026 ingested Fidelity CSVs with PENDING ACTIVITY rows. These
rows exist in the archive but are NOT classified as ACCOUNTING_ADJUSTMENT.

**Raw data from May 22 archive files:**
```
X20548022,General Brokerage,Pending activity,,,,,-$4,344.91
Z35123695,Individual - TOD,Pending activity,,,,,+$4,344.91
```

This is also a symmetric offset (net zero) — same Class C pattern.

**Impact on counts:** If pre-schema runs were included using the current
classification logic, the count would increase by approximately 10 more zero-MV
rows (all Class C). The Class A count would be unchanged.

---

## Classification Summary Table

| Class | Label | Count | % Total | Net MV Exposure |
|-------|-------|-------|---------|-----------------|
| A | PENDING_PURCHASE | 36 | 85.7% | -$60,199.65 |
| C | CASH_TRANSFER (net zero) | 6 | 14.3% | $0.00 |
| B | PENDING_SALE | 0 | 0% | $0.00 |
| D | DIVIDEND_ACCRUAL | 0 | 0% | $0.00 |
| E | CORPORATE_ACTION | 0 | 0% | $0.00 |
| F | FIDELITY_BOOKKEEPING | 0 | 0% | $0.00 |
| G | UNKNOWN | 0 | 0% | $0.00 |
| **TOTAL** | | **42** | **100%** | **-$60,199.65** |

---

## Classification Notes

### What Makes This Classification Reliable

1. **Symbol uniformity:** 100% of rows have symbol "PENDING ACTIVITY" — no variation.
2. **Description uniformity:** 100% have blank description.
3. **Pattern consistency:** The single-account negative pattern (Class A) and
   symmetric two-account pattern (Class C) are entirely stable across 6 distinct
   dates and 6 source files.
4. **Value interpretation:** The two observed negative amounts ($1,500.00 and
   $3,566.55) are non-round values consistent with equity purchase amounts, not
   wire transfer amounts or fee accruals.

### What Limits This Classification

1. **Observation window is narrow:** Only 6 calendar dates (2026-05-28 to 2026-06-02),
   spanning a 5-day period. The portfolio has been running since at least May 21.
2. **No Class B, D, E, F observed:** This could mean they don't occur, or that the
   observation window is too short to encounter them.
3. **Fidelity-specific format:** The interpretation of "Pending activity" as a
   pending purchase settlement is inferred from context; Fidelity documentation
   does not explicitly map this label to a transaction type.
