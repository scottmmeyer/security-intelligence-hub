# ESS Refresh Integrity Report

**Date:** 2026-06-15  
**Scope:** Verify today's ESS refresh was complete and intact

---

## Refresh Execution Summary

### Jun 15 ESS Intake (non-StarMine Zacks)

| Field | Value |
|-------|-------|
| Run ID | `intake-20260615` |
| Source | `non-ess.csv` |
| Rows | 313 |
| Coverage domain | `NON_STARMINE_ANALYST` |
| Created | 2026-06-15T10:55:06 UTC |
| Status | **COMPLETE** |

### Jun 15 ESS Intake (StarMine)

| Field | Value |
|-------|-------|
| Source file | `EquitySummaryScores-15Jun2026.csv` |
| Status | **COMPLETE** — file cleaned from `incoming/ess/starmine/` after processing |
| Historical store | `data/history/signals/snapshot_date=2026-06-15/` |
| Note | StarMine rows ingested to history partition but NOT present in current `signal_snapshot.csv` |

---

## Q10. Did ESS refresh successfully?

**YES** — both files were processed. The ESS intake stage completed without error:
- `EquitySummaryScores-15Jun2026.csv`: processed and cleaned from incoming (cleanup = success signal)
- `non-ess.csv`: processed and cleaned from incoming (confirmed)

The ingestion validation confirmed:
- 313 rows appended (from today's run)
- Persistence verification: PASSED
- Files cleaned: 2

---

## Q11. Was the generated file complete?

**The historical partition is complete.** However, `data/current/signal_snapshot.csv` does not reflect the Jun 15 StarMine data because:

1. The ESS intake stage writes `signal_snapshot.csv` with the signals from the current intake run
2. The non-StarMine Zacks intake ran **after** the StarMine intake and overwrote `signal_snapshot.csv` with only 313 non-StarMine rows
3. The Jun 15 StarMine data exists in the historical partition but not in the "current" artifact

**This is the operational gap**: the current signal snapshot reflects only one half of today's intake.

---

## Q12. Were any partial failures observed?

**No failures.** Both intake runs completed cleanly. The coverage warning is a consequence of the overwrite order, not of any intake failure.

---

## Coverage Calculation Code Path

**Source:** `src/portfolio/ess_coverage.py:build_ess_coverage_gap_warning()`

```python
def build_ess_coverage_gap_warning(
    *,
    incoming_ess_symbols: set[str],  # ← from current intake batch
    snapshot_date: date,
    signal_snapshot_path: Path,      # ← data/current/signal_snapshot.csv
    analysis_runs_root: Path,
) -> EssCoverageGapWarning | None:
    holdings = load_latest_equity_holdings(analysis_runs_root)
    prior_ess = load_fidelity_signals(signal_snapshot_path)

    for sym, holding in holdings.items():
        if sym in incoming_ess_symbols:  # ← only non-StarMine today
            continue
        previous = prior_ess.get(sym)   # ← reads prior signal_snapshot.csv
        if previous is None:
            continue
        # ... creates gap entry
```

**Symbol matching:** Direct string equality comparison (`sym in incoming_ess_symbols`). No alias mapping, no normalization. Symbol `MU` in portfolio is compared directly to symbol `MU` in incoming_ess_symbols.

**Q7 — Is the warning calculation correct?** YES. The calculation is correct given its inputs. The gap arises from `incoming_ess_symbols` being empty of StarMine symbols today.

**Q8 — Is symbol normalization involved?** NO. Direct uppercase string equality. No alias or ticker mapping.

**Q9 — Are aliases causing false misses?** NO. All 55 symbols match by exact ticker string.

---

## Recommended Operational Fix

The `_run_intake.py` script (or the intake stage) should ensure that both intake sources write to `signal_snapshot.csv` in a merge fashion rather than last-write-wins. Alternatively, the StarMine intake should always run last so it populates `signal_snapshot.csv` with StarMine data before the coverage warning is computed.

**This is a process/ordering issue, not a data quality issue.**
