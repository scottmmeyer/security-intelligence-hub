# Signal Coverage Remediation Report
**Phase:** 22D.2 — Workstream B  
**Reference Date:** 2026-06-01  
**Status:** COMPLETE  

---

## Finding Addressed

**Phase 22D.1 Finding:** Five holdings (SBS, STNG, SIMO, MCB, BSVN) had empty
`ess_score_text` in the analytical universe, causing their ESS weight (0.55) to
be excluded from composite score renormalization and their signal direction to
show UNKNOWN in the UI.

**Root Cause by Symbol:**

| Symbol | Cause |
|--------|-------|
| SBS, MCB | Absent from `signal_snapshot.csv` entirely |
| STNG, SIMO, BSVN | Present in snapshot with `signal_coverage_status=NON_STARMINE_ANALYST`; `starmine_ess_text` empty |

All five symbols have valid recent entries in `ess_history_master.csv` that the pipeline did not consult.

**Confirmed Archive Values (latest by capture_date):**

| Symbol | capture_date | ess_category | ess_5pt |
|--------|-------------|--------------|---------|
| MCB | 2026-04-18 | VERY_BULLISH | 5 |
| SBS | 2026-04-04 | BULLISH | 4 |
| BSVN | 2026-05-20 | VERY_BULLISH | 5 |
| STNG | 2026-05-20 | VERY_BULLISH | 5 |
| SIMO | 2026-05-20 | BULLISH | 4 |

---

## Changes Made

### Layer 1 (Immediate) — `src/portfolio/recommendations.py` — `build_security_overlays()`

Loads `ess_history_master.csv` at function entry, builds `_ess_archive: dict[str, str]`
(symbol → latest ess_category by max capture_date).

After unpacking `h.ess_score_text`:
```python
ess = h.ess_score_text or ""
if not ess:
    ess = _ess_archive.get(sym, "")
ess = ess or "UNKNOWN"
```

This provides immediate correction without requiring an analytical universe rebuild.
The `ess_score_text` field on the overlay (and therefore the UI signal direction)
is corrected at runtime.

### Layer 2 (Pipeline) — `src/history/analytical_universe_manager.py` — `build_analytical_universe_rows_from_current()`

After `danelfin_scores_by_symbol` is loaded, reads `ess_history_master.csv` into
`ess_archive_by_symbol: Dict[str, str]` (same max-date-per-symbol logic).

After the primary ESS assignment:
```python
ess_score_text = str(signal_row.get("starmine_ess_text") or base_row.get("starmine_ess_text") or "").strip()
if not ess_score_text:
    ess_score_text = ess_archive_by_symbol.get(symbol, "")
```

This ensures the next universe rebuild persists corrected ESS text to
`data/current/analytical_universe.csv`, eliminating the need for the runtime
fallback on an ongoing basis.

---

## Acceptance Criteria Verification

| ID | Criterion | Result |
|----|-----------|--------|
| AC-B1 | ESS fallback reads max capture_date entry for each symbol | PASS — smoke test confirmed all 5 symbols resolve to expected category |
| AC-B2 | Fallback only activates when primary ESS is empty | PASS — `if not ess_score_text` guard in place |
| AC-B3 | Composite score will change for 5 symbols on next rebuild (explicitly permitted) | EXPECTED — ESS weight (0.55) now included in renormalization |
| AC-B4 | No change to symbols with valid primary ESS | PASS — fallback is conditional on empty string |

---

## Design Notes

- The archive fallback is general-purpose, not limited to the 5 confirmed symbols. Any symbol with empty ESS in the primary signal path will benefit from archive coverage. This is the correct behavior for the defect class.
- `ess_category` values from the archive (`VERY_BULLISH`, `BULLISH`, etc.) are directly compatible with the `ess_score_text` field used in `_score_from_inputs()`.
- No scoring threshold changes. No ranking logic changes. No signal weight changes.
