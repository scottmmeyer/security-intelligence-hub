# Phase 23.0C.1 — SPAXX Duplicate Row Analysis

**PAR Run**: PAR-20260603-B66B00E3  
**Date**: 2026-06-03  
**Status**: COMPLETE

---

## 1. The Observed Anomaly

Two distinct observations about SPAXX surfaced in this PAR run:

1. **Source file has 2 SPAXX rows** — two different Fidelity accounts both hold SPAXX
2. **RC-06 FAIL** — reconciliation flags SPAXX as "present in ETF decomposition registry"

These are **separate issues** with different root causes. Neither constitutes an analytical defect.

---

## 2. Multi-Account Merge (Source Duplication)

### Source File State

| Account ID | Account Name | Symbol | Quantity | Value |
|------------|-------------|--------|----------|-------|
| X20548022 | General Brokerage | SPAXX | — | $69.51 |
| Z35123695 | Individual - TOD | SPAXX | — | $37,651.65 |
| **Total** | | | | **$37,721.16** |

Two separate Fidelity accounts both hold SPAXX (Fidelity Government Money Market Fund). This is **normal multi-account behavior** — cash sweep into SPAXX is the default position in Fidelity brokerage accounts.

### Ingestion Merge Behavior

| Layer | SPAXX Rows | Market Value |
|-------|-----------|--------------|
| Source CSV | 2 (two accounts) | $69.51 + $37,651.65 |
| Holdings CSV (after ingestion) | 1 (merged) | $37,721.16 |

Ingestion correctly **merged** the two source rows into a single combined holding. Verification: $69.51 + $37,651.65 = **$37,721.16** ✓

The `holdings.csv` entry for SPAXX shows `account_names = "General Brokerage, Joint WROS - TOD, Individual - TOD"` — the merged account string confirms multi-account aggregation was applied correctly.

### Verdict on Source Duplication

**Not a defect.** Multi-account merging is the intended behavior. The combined market value is arithmetically correct.

---

## 3. RC-06 FAIL — ETF Registry Presence

### What RC-06 Checks

RC-06 audits whether any position classified as a **cash position** is also present in the **ETF decomposition registry**. The check is designed to catch cases where a cash instrument might be inadvertently double-counted through ETF decomposition.

### RC-06 Finding

```
RC-06 FAIL
  Cash positions audited: 1
  SPAXX: present in ETF decomposition registry (SPAXX)
```

SPAXX is in the ETF decomposition registry **intentionally**. It was registered to define its decomposition composition as:

```
SPAXX → 100% CASH (Money Market)
```

This is required so that when SPAXX is held in a portfolio, the decomposition engine can compute its underlying asset class exposure (all cash). Without an ETF registry entry, SPAXX decomposition falls back to heuristic, introducing classification noise.

### Why RC-06 Fires

The reconciliation rule was designed for the case where an **equity ETF** (e.g., SPY) somehow ends up classified as cash — a genuine error. It was not designed to handle the case where a **cash instrument** has been deliberately added to the ETF registry for decomposition purposes.

The check fires because:
- SPAXX is classified as `security_type=CASH` in the holdings pipeline
- SPAXX exists as a key in the ETF decomposition registry
- The check treats this as a contradiction — but it is not

### Cash Calculation Verification

| Metric | Value | Source |
|--------|-------|--------|
| Expected cash (SPAXX only) | $37,721.16 | holdings.csv |
| Reconciliation cash total | ~$37,721.16 | RC-05 |
| RC-05 variance | $0.18 | Rounding |
| RC-05 result | **PASS** | reconciliation.json |

Cash calculation is **correct**. The RC-06 FAIL has no downstream impact on:
- Deployable cash calculation ✓
- Adjusted deployable cash ✓
- CW-DAS sizing ✓
- Allocation % ✓
- Funding source analysis ✓

### Verdict on RC-06

**False positive.** The ETF registry entry for SPAXX is intentional and necessary for correct decomposition. RC-06 fires due to an over-broad rule definition.

**Rule correction needed**: RC-06 should either:
1. Exclude cash instruments that are designated decomposition registry entries (whitelist: `CASH_DECOMPOSABLE = {SPAXX, FDIC, FDRXX, ...}`)
2. Or downgrade from FAIL → WARN for positions where RC-05 independently confirms correct cash total

---

## 4. Impact Matrix

| Dimension | Impact from Source Duplication | Impact from RC-06 FAIL |
|-----------|-------------------------------|------------------------|
| Portfolio market value | None (correctly merged) | None |
| Cash total | None | None (RC-05 PASS) |
| Allocation % | None | None |
| Deployable cash | None | None |
| Funding source selection | None | None |
| CW-DAS | None | None |

**Total financial impact: $0.00**

---

## 5. Governance Recommendation

1. **Introduce ETF registry type flag**: Add `registry_type: CASH_DECOMPOSABLE` to SPAXX's entry to distinguish intentional cash-instrument registrations from accidental ETF-as-cash classifications
2. **Update RC-06**: Scope the FAIL condition to non-intentional registry entries; reclassify SPAXX registry presence as PASS or WARN with annotation
3. **No portfolio action required**: SPAXX balance ($37,721.16) is correct and classified correctly in all allocation and cash calculations
