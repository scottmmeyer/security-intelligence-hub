# ESS Intake Ordering Final Verdict

**Date:** 2026-06-15  
**Issue:** ESS-INTAKE-ORDERING-01  
**Decision:** ACCEPT

---

## Q1. Was root cause confirmed?

**YES.** The root cause was `append_signal_snapshots()` using a last-write-wins model for `signal_snapshot.csv`. When the non-StarMine Zacks intake ran after the StarMine intake, it overwrote `signal_snapshot.csv` with only 313 non-StarMine rows, causing all 55 previously-StarMine-covered holdings to appear as gaps.

---

## Q2. Which consumers read signal_snapshot.csv?

- `src/portfolio/runner.py:1643` — ESS enrichment for all holdings via `load_fidelity_signals()`
- `src/portfolio/ess_coverage.py:50` — ESS coverage gap warning computation
- `src/portfolio/recommendations.py:197` — recommendation engine ESS fallback
- `src/portfolio/holdings_coverage.py` — coverage refresh targeting

---

## Q3. Was provider-order dependence eliminated?

**YES.** `_build_merged_snapshot()` merges all same-day partitions, producing identical output regardless of intake execution order. Tests T3 and T4 confirm: StarMine-then-Zacks and Zacks-then-StarMine produce the same merged `signal_snapshot.csv`.

---

## Q4. Does coverage analysis now reflect actual signal availability?

**YES.** After the fix:
- Both StarMine and non-StarMine rows are merged into `signal_snapshot.csv`
- `build_ess_coverage_gap_warning()` correctly computes `incoming_ess_symbols` across all providers
- MU, VRT, NVDA will no longer appear as stale when their StarMine data exists in any partition for the current date

---

## Q5. Did recommendation logic change?

**NO.** Only `src/history/signal_snapshot_manager.py` was modified.

---

## Q6. Did attribution logic change?

**NO.**

---

## Q7. Did benchmark logic change?

**NO.**

---

## Q8. Is the solution production-ready?

**YES.**
- 9/9 ordering tests pass
- 77/77 total regression tests pass (0 failed)
- Single-file change with deterministic, auditable merge logic
- Backward compatible: all partition storage and index logic unchanged

---

## Definition-of-Done Status

| Requirement | Status |
|------------|--------|
| MU no longer falsely appears uncovered | ✓ PASS |
| VRT no longer falsely appears uncovered | ✓ PASS |
| NVDA no longer falsely appears uncovered | ✓ PASS |
| Coverage warnings reflect true signal availability | ✓ PASS |
| Provider execution order cannot change coverage results | ✓ PASS |
| No recommendation behavior changes | ✓ PASS |
| No attribution behavior changes | ✓ PASS |
| No benchmark behavior changes | ✓ PASS |
