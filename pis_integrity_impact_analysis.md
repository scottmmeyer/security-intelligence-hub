# PIS-INTEGRITY-01 Impact Analysis

**Date:** 2026-06-15

---

## PIS Snapshots

**Before fix:**
- Position snapshots contained PENDING_SETTLEMENT, ACCOUNTING_ADJUSTMENT, ZERO_VALUE_LEGACY_POSITION rows
- position_count in snapshot index included non-investable rows
- `43` non-investable rows across all historical snapshots

**After fix (new uploads only):**
- Position snapshots contain only ACTIVE_POSITION and CASH_EQUIVALENT
- position_count in index accurately reflects investable holdings only
- No retroactive change to historical partitions (immutability preserved)

**Governance / Canonical:** No impact. Governance evaluates `portfolio_value` and `account_name`, not individual positions. Canonical selection is unaffected.

---

## Change Detection

**Before fix:**
- 28 change records involved non-investable symbols
- 6 spurious NEW_POSITION records
- 5 spurious EXITED_POSITION records
- 17 spurious UNCHANGED records

**After fix:**
- New portfolio uploads produce change records for investable holdings only
- PENDING ACTIVITY appearing/disappearing in Fidelity exports no longer generates NEW/EXITED records
- Accounting correction rows (M26CNT069) no longer appear as change targets

**Quantified improvement (per new upload cycle):**
- Expected elimination of ~3-5 spurious change records per upload cycle where PENDING ACTIVITY was present

---

## Lineage

**Before fix:**
- 52 lineage records; 24 unmatched (confidence=NONE)
- 11 of 24 unmatched (46%) caused by non-investable symbols
- Lineage match rate: 28/52 = 54%

**After fix (projected for future uploads):**
- Non-investable symbols absent from change records → absent from lineage input
- Unmatched count from non-investable symbols drops to 0
- Projected match rate improvement: ~21% fewer unmatched entries

**Historical records:** Existing lineage_records.csv not retroactively modified. PIS-005 refresh chain will recompute on next upload.

---

## Attribution

**No impact.** Attribution scores only rows with `confidence != NONE`. The 11 non-investable unmatched lineage rows have `confidence=NONE` and are already excluded from attribution scoring.

**Verification:** Zero attribution records involve PENDING ACTIVITY or M26CNT069. (Confirmed: attribution_records.csv checked — no such symbols present.)

---

## Benchmark Attribution

**No impact.** Benchmark attribution reads from attribution_records.csv and change_records.csv, then joins via snapshot_date/interval. Non-investable symbols have no attribution records to join against. SPY price computation is completely independent of position symbols.

---

## CPV (Compliance Validator)

**No impact.** CPV reads alignment data (derived from investable holdings only). CPV evaluates L1 node percentages (EQUITIES, FIXED_INCOME, DIGITAL, etc.) which are computed from investable holdings exclusively. Non-investable rows do not contribute to alignment percentages.

---

## Summary

| Component | Impact | Status |
|-----------|--------|--------|
| PIS Snapshots | Cleaner (non-investable excluded) | IMPROVED |
| Change Detection | Spurious NEW/EXITED eliminated | IMPROVED |
| Lineage | ~46% reduction in non-investable unmatched | IMPROVED |
| Attribution | None (already excluded) | UNAFFECTED |
| Benchmark Attribution | None | UNAFFECTED |
| CPV | None | UNAFFECTED |
| Recommendations | None | UNAFFECTED |
| Governance/Canonical | None | UNAFFECTED |
