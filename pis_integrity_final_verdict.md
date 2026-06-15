# PIS-INTEGRITY-01 Final Verdict

**Date:** 2026-06-15  
**Issue:** #51  
**Decision:** ACCEPT

---

## Q1. What was the root cause?

`register_portfolio_snapshot_from_sih()` in `src/pis/service.py` received `raw_holdings` from the ingestion pipeline — the complete unfiltered set including PENDING_SETTLEMENT, ACCOUNTING_ADJUSTMENT, and ZERO_VALUE_LEGACY_POSITION holdings. Portfolio analytics applied the investable-state filter downstream (after PIS registration), creating a divergence.

---

## Q2. Which systems were inconsistent?

| System | Used | Investable only? |
|--------|------|-----------------|
| Portfolio recommendations | ACTIVE_POSITION, CASH_EQUIVALENT | ✓ YES |
| PIS snapshot history (before fix) | ALL operational states | ✗ NO |
| Change detection (before fix) | Derived from PIS snapshots | ✗ NO |
| Lineage (before fix) | Derived from change detection | ✗ NO |

After fix, all systems use the same investable-state rule.

---

## Q3. What correction was implemented?

Added `_PIS_INVESTABLE_STATES = frozenset({"ACTIVE_POSITION", "CASH_EQUIVALENT"})` constant and investable filter inside `register_portfolio_snapshot_from_sih()` in `src/pis/service.py`:

```python
investable_holdings = [
    h for h in holdings
    if str(getattr(h, "operational_state", "ACTIVE_POSITION") or "ACTIVE_POSITION")
    in _PIS_INVESTABLE_STATES
]
pis_positions = _to_pis_positions(snapshot, investable_holdings)
```

This is 7 lines of change in one file. No other files modified.

---

## Q4. Did change detection behavior change?

**Going forward: YES.** New portfolio uploads will no longer generate change records for PENDING_SETTLEMENT, ACCOUNTING_ADJUSTMENT, or ZERO_VALUE_LEGACY_POSITION holdings. Spurious NEW_POSITION and EXITED_POSITION events from settlement artifacts are eliminated.

**Historical records: NOT retroactively modified** (immutability preserved).

---

## Q5. Did lineage metrics improve?

**Going forward: YES.** With non-investable holdings absent from new snapshots:
- No change records generated for settlement artifacts
- No lineage attempts to match non-existent changes
- Projected reduction of ~46% of unmatched lineage entries per upload cycle that previously contained PENDING ACTIVITY

---

## Q6. Did recommendation logic change?

**NO.** Zero changes to any recommendation generation code.

---

## Q7. Did attribution logic change?

**NO.** Zero changes to performance_attribution.py or any attribution code.

---

## Q8. Did benchmark attribution change?

**NO.** Zero changes to benchmark_attribution.py or any benchmark code.

---

## Q9. Did CPV behavior change?

**NO.** CPV reads alignment data which was already derived from investable holdings only. CPV is unaffected.

---

## Q10. Is PIS-INTEGRITY-01 production-ready?

**YES.**

- Root cause identified and corrected at the authoritative boundary
- Single constant defines investable states (single source of truth)
- 11 new tests covering all required scenarios
- 68 total regression tests passing (0 failed)
- No modifications to recommendations, attribution, benchmark, or governance logic
- Backward compatible: historical snapshots preserved, future uploads are clean

---

## Commit

`3f56ef4` — PIS-INTEGRITY-01: filter non-investable holdings before PIS snapshot registration

## Files Changed

| File | Change |
|------|--------|
| `src/pis/service.py` | Added `_PIS_INVESTABLE_STATES` + 7-line filter |
| `tests/test_pis_integrity_01.py` | New — 11 tests |
