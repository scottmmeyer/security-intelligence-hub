# ESS Artifact Selection Audit

**Date:** 2026-06-15  
**Scope:** Determine which ESS artifact was used and whether it was the latest available

---

## Q1. Which ESS artifact was selected?

Today's portfolio alignment analysis reads from `data/current/signal_snapshot.csv`.

**Current artifact:**

| Field | Value |
|-------|-------|
| Path | `data/current/signal_snapshot.csv` |
| Rows | 313 |
| snapshot_date | 2026-06-15 |
| run_id | `intake-20260615` |
| Source file | `non-ess.csv` (non-StarMine Zacks data only) |
| StarMine rows | **0** |
| Coverage domains | `NON_STARMINE_ANALYST: 313` |
| Created | 2026-06-15T10:55:06 UTC |

---

## Q2. Why was it selected?

`data/current/signal_snapshot.csv` is the always-current artifact written by the ESS intake stage. It is overwritten on each intake run. The Jun 15 intake processed only `non-ess.csv` (the Zacks non-StarMine file) from `incoming/ess/non_starmine_zacks/`.

**The `EquitySummaryScores-15Jun2026.csv` StarMine file was also processed today** — it was successfully ingested into the historical store (`data/history/signals/snapshot_date=2026-06-15/`). However, the intake stage writes `signal_snapshot.csv` with the **union of all signals from the current run**. Since the `EquitySummaryScores-15Jun2026.csv` StarMine data was ingested in a prior run today (confirmed by the ESS intake completion from this morning), `signal_snapshot.csv` reflects the Jun 15 `non-ess.csv` as the most recent overwrite.

**Root cause of apparent gap:** Both intake sources were processed, but `signal_snapshot.csv` was last written by the `non-ess.csv` run, which contains no StarMine data.

---

## Q3. Was it the latest available ESS artifact?

**Partially.** The Jun 15 `signal_snapshot.csv` is the latest run artifact but contains **only non-StarMine Zacks data**. 

The most recent StarMine (EquitySummaryScore) data is:

| Field | Value |
|-------|-------|
| Path | `data/history/signals/snapshot_date=2026-06-12/run_id=intake-20260612/signal_snapshots.csv` |
| StarMine rows | 2,431 |
| Source | `EquitySummaryScores-12Jun2026.csv` |
| snapshot_date | 2026-06-12 |

This Jun 12 data is **3 days old** as of today (Jun 15).

---

## Q4. Were any newer ESS artifacts ignored?

The `EquitySummaryScores-15Jun2026.csv` was ingested this morning (it no longer exists in `incoming/ess/starmine/` — it was cleaned up by the intake stage, confirming successful processing). Its data was written to `data/history/signals/snapshot_date=2026-06-15/`, but this partition data is **not reflected in the current `signal_snapshot.csv`** because the non-ess.csv intake ran afterward and overwrote it.

**This is the root cause of the 55-gap warning.** See `ess_coverage_validation.md` for details.

---

## Summary

The Jun 15 StarMine ESS data **was successfully ingested** this morning into the historical store. However, `signal_snapshot.csv` (the artifact read by portfolio analysis) reflects only the non-StarMine Zacks data from the most recent intake run. The coverage warning is triggered because `build_ess_coverage_gap_warning()` compares the `incoming_ess_symbols` from today's intake (non-StarMine only) against portfolio holdings — and the 55 portfolio holdings that had StarMine coverage on Jun 12 are not in today's `incoming_ess_symbols` set.
