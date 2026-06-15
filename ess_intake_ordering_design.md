# ESS Intake Ordering Design

**Date:** 2026-06-15  
**Issue:** ESS-INTAKE-ORDERING-01  
**Status:** IMPLEMENTED (commit `bed805a`)

---

## Current Intake Flow (Pre-Fix)

### Before the fix, `append_signal_snapshots()` wrote:

```
signal_snapshot.csv ← last-write-wins
                         ↑
                    non-ess.csv run overwrites
                         ↑
              EquitySummaryScores run wrote first
```

**Semantics:** "most recent intake run" — incorrect

### Consumers of `signal_snapshot.csv`

| Consumer | File | Purpose |
|----------|------|---------|
| ESS enrichment in portfolio analysis | `src/portfolio/runner.py:1643` | Loads StarMine ESS scores for all holdings via `load_fidelity_signals()` |
| ESS coverage gap warning | `src/portfolio/ess_coverage.py:50` | Reads prior signal state to detect holdings that lost ESS coverage |
| Recommendations engine | `src/portfolio/recommendations.py:197` | Falls back to signal_snapshot when ESS absent from holding |
| `refresh_signals.py` coverage check | `src/portfolio/holdings_coverage.py` | Determines if provider refresh is needed |

---

## Overwrite Behavior (Pre-Fix)

When two providers ran on the same day (e.g., StarMine at 05:47, non-StarMine Zacks at 10:55):

1. StarMine intake ran first → wrote `signal_snapshot.csv` with 2431 StarMine rows
2. Non-StarMine Zacks intake ran second → **overwrote** `signal_snapshot.csv` with 313 Zacks-only rows
3. StarMine data disappeared from current state
4. Coverage check saw 0 StarMine incoming symbols → 55 holdings flagged as stale

**Provider ordering determined coverage results — incorrect.**

---

## Implemented Fix: Option A — Merged Canonical Current State

### New function: `_build_merged_snapshot()` in `src/history/signal_snapshot_manager.py`

```python
def _build_merged_snapshot(*, snapshot_date, history_root, extra_rows):
    # 1. Collect rows from ALL partitions for snapshot_date
    for each run_dir in history_root/snapshot_date=YYYY-MM-DD/:
        read signal_snapshots.csv

    # 2. Merge: for each symbol, keep highest-quality row
    #    Quality rank: STARMINE_COVERED with ESS text (3) > any ESS text (2) > no ESS (1)
    #    Tiebreak: latest created_at_utc

    # 3. Write merged result to signal_snapshot.csv
```

**Semantics after fix:** "latest known signal state across all providers" — correct

### Quality Ranking

| Rank | Condition | Description |
|------|-----------|-------------|
| 3 | STARMINE_COVERED + non-empty starmine_ess_text | Full ESS coverage |
| 2 | Any non-empty starmine_ess_text | Partial ESS coverage |
| 1 | No ESS text | Non-StarMine only |

### Provider Order Independence

| Order | Before Fix | After Fix |
|-------|-----------|-----------|
| StarMine runs first, Zacks second | StarMine LOST | StarMine PRESERVED |
| Zacks runs first, StarMine second | StarMine PRESERVED | StarMine PRESERVED |
| Only StarMine runs | StarMine PRESERVED | StarMine PRESERVED |
| Only Zacks runs | Zacks PRESERVED | Zacks PRESERVED |

---

## Impact on Consumers

| Consumer | Impact |
|---------|--------|
| `load_fidelity_signals()` | Now sees merged state: StarMine rows preserved even after Zacks runs |
| `build_ess_coverage_gap_warning()` | Will have fewer false gaps; stale count reflects actual missed coverage |
| `recommendations.py` | ESS scores now correctly present when StarMine data exists |
| Coverage refresh logic | Accurate coverage assessment; fewer unnecessary targeted refreshes |

---

## No-Change Areas

- Recommendation generation logic: UNCHANGED
- Attribution scoring: UNCHANGED  
- Benchmark attribution: UNCHANGED
- Immutable partition storage: UNCHANGED (partitions still written per run)
- Index: UNCHANGED
