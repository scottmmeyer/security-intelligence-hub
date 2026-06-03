# AEIS Signal Lineage Trace — Phase 7.5G-A

**Date:** 2026-05-31  
**Subject:** Why AEIS displays ESS = blank despite valid ESS data in the source file  
**Reference Run:** PAR-20260531-F794D952  
**Scope:** Read-only root-cause identification. No fixes. No refactoring.

---

## SECTION 1 — Expected ESS Value

The latest imported ESS source file `EquitySummaryScores-May2026.csv` (ingested as run `INTAKE-20260526-001` on 2026-05-26) contains the following for AEIS:

| Field | Value |
|-------|-------|
| `starmine_ess_text` | **BEARISH** |
| `starmine_ess_numeric` | 2.0 |
| `starmine_ess_numeric_estimated` | True |
| `starmine_ess_source_type` | TEXT_MAPPED |
| `coverage_domain` | STARMINE_COVERED |
| `signal_coverage_status` | COVERED |

**Expected value throughout the pipeline:** `ess_score_text = "BEARISH"`

---

## SECTION 2 — Actual Value at Each Pipeline Stage

| Stage | Artifact | AEIS Present? | `ess_score_text` | Notes |
|-------|----------|:---:|---------------|-------|
| **1. ESS Source File** | `EquitySummaryScores-May2026.csv` (via `data/history/signals/snapshot_date=2026-05-26/.../signal_snapshots.csv`) | ✅ | `"BEARISH"` | Row 1 of 2 in signal history snapshot; line 497 in signal_snapshot.csv |
| **1b. ESS Sentinel Row** | `ESS_NONE.csv` (NON_STARMINE_ANALYST coverage) | ✅ | `""` | Row 2 of 2; injected by intake for non-Starmine universe coverage; line 2489 in signal_snapshot.csv |
| **2. signal_snapshot.csv** | `data/current/signal_snapshot.csv` | ✅ | Two rows: `"BEARISH"` (line 497) and `""` (line 2489) | Both rows present; ordering is COVERED first, NON_COVERED second |
| **3. analytical_universe.csv** | `data/current/analytical_universe.csv` | ✅ | `""` (blank) | **FIRST CORRUPTION POINT** — see Section 3 |
| **4. PortfolioHolding** | `data/portfolio_ingestion/analysis_runs/PAR-20260531-F794D952/holdings.csv` | ✅ | `""` | Inherited from analytical_universe; `or None` coercion in enrichment.py |
| **5. SecurityIntelligenceOverlay** | `data/portfolio_ingestion/analysis_runs/PAR-20260531-F794D952/security_overlays.csv` | ✅ | `""` | Propagated from PortfolioHolding via `h.ess_score_text` in recommendations.py |
| **6. UCF Verdict** | `data/portfolio_ingestion/analysis_runs/PAR-20260531-F794D952/ucf_verdicts.json` | ✅ | not stored (UCF does not include raw ESS text) | `signal_direction = "BULLISH"` is derived from composite_score; `ucf_label = "CORE_CONVICTION_LEADER"` |
| **7. Deployment Queue** | `data/portfolio_ingestion/analysis_runs/PAR-20260531-F794D952/deployment_queue.json` | ✅ | key absent (`KEY_MISSING`) | deployment_queue items do not carry `ess_score_text` field |
| **8a. API /api/portfolio/runs/{id}** | HTTP JSON response | ✅ | `""` (overlay) | `security_overlays[AEIS].ess_score_text = ""` |
| **8b. UI rendering** | `ui/portfolio_alignment/app.js` line 1796 | ✅ | `"—"` displayed | `ov.ess_score_text \|\| c.ess_score_text \|\| "—"` evaluates to `"—"` because both are empty string (falsy) |

---

## SECTION 3 — First Corruption Point

**File:** `data/current/analytical_universe.csv`  
**Built by:** `src/history/analytical_universe_manager.py`, function `build_analytical_universe_rows_from_current()`  
**Exact lines:** 465–470

```python
# src/history/analytical_universe_manager.py, lines 465–470
signal_rows = _read_csv_rows(current_root_path / "signal_snapshot.csv")
signal_by_symbol = {
    str(row.get("symbol", "")).strip().upper(): row
    for row in signal_rows
    if str(row.get("symbol", "")).strip()
}
```

**What happens:**  
`signal_snapshot.csv` contains **two rows** for AEIS:

| Line | `coverage_domain` | `source_file` | `starmine_ess_text` |
|------|-------------------|---------------|---------------------|
| 497 | `STARMINE_COVERED` | `EquitySummaryScores-May2026.csv` | `"BEARISH"` |
| 2489 | `NON_STARMINE_ANALYST` | `ESS_NONE.csv` | `""` |

The dict comprehension at line 466 is a **plain last-wins dedup**. It iterates all rows in file order. Row at line 497 (`BEARISH`) is inserted first, then row at line 2489 (empty) **overwrites** it. The resulting `signal_by_symbol["AEIS"]` has `starmine_ess_text = ""`.

**Downstream cascade from this point (line 548):**
```python
# analytical_universe_manager.py line 548
ess_score_text = str(signal_row.get("starmine_ess_text") or base_row.get("starmine_ess_text") or "").strip()
```
`signal_row.get("starmine_ess_text")` returns `""` (falsy) → fallback to `base_row.get("starmine_ess_text")` → also `""` → `ess_score_text = ""`.

This empty string is written to `analytical_universe.csv` at line 575:
```python
ess_score_text=ess_score_text,
```
The universe record for AEIS carries `provider_lineage: provider=FIDELITY;source_file=ESS_NONE.csv` — confirming it was the NON_COVERED row that won.

---

## SECTION 4 — Root Cause

**Root cause: The `signal_by_symbol` dict comprehension in `build_analytical_universe_rows_from_current()` (lines 466–470 of `src/history/analytical_universe_manager.py`) uses last-row-wins dedup with no priority on `coverage_domain`. When `signal_snapshot.csv` contains both a `STARMINE_COVERED` row (with valid ESS text) and a `NON_STARMINE_ANALYST`/`ESS_NONE.csv` sentinel row (with empty ESS text) for the same symbol, the sentinel row — appearing later in the file — silently overwrites the valid covered row.**

Contributing factors:

1. **ESS_NONE.csv sentinel rows exist for all non-Starmine symbols.** The intake pipeline generates NON_STARMINE_ANALYST entries as coverage gap markers for the full base equity universe. AEIS is Starmine-covered, but it is also in the base universe, so it gets a NON_STARMINE_ANALYST sentinel row.

2. **signal_snapshot.csv is appended-in-intake-order.** STARMINE_COVERED rows (from the real ESS file) are appended first; NON_STARMINE_ANALYST/ESS_NONE.csv rows are appended afterward. This ordering consistently places the sentinel row after the covered row for any symbol that appears in both.

3. **The empty string `""` survives the `or` chain.** At line 548 the fallback chain `signal_row.get(...) or base_row.get(...) or ""` cannot recover the BEARISH value because the covered row has already been lost.

4. **Downstream read-path uses `or None` truncation.** In `src/portfolio/enrichment.py` line 205: `ess_score_text=u.get("ess_score_text") or None` converts `""` to `None`, permanently erasing the field from PortfolioHolding and all downstream objects.

5. **UI final safeguard is `|| "—"`.** The UI at `app.js:1796` correctly uses `ov.ess_score_text || c.ess_score_text || "—"` but both sources are empty string by this point, so the fallback to `"—"` is cosmetically correct but masks the data loss.

**The bug is not in the ESS source file, the intake normalizer, the signal_snapshot, the enrichment path, the overlay builder, or the UI. It is solely in the dict comprehension at lines 466–470 of `analytical_universe_manager.py`.**

---

## SECTION 5 — Minimal Remediation

> Per scope requirements, this section identifies the minimal fix only. No code changes are made in this phase.

**Target:** `src/history/analytical_universe_manager.py`, function `build_analytical_universe_rows_from_current()`, lines 466–470.

**Required behavior:** When multiple rows exist for the same symbol in `signal_snapshot.csv`, prefer the row with `coverage_domain == "STARMINE_COVERED"` over `"NON_STARMINE_ANALYST"`. If no STARMINE_COVERED row exists, fall back to any available row.

**Minimal fix (pseudocode):**
```python
# Replace the flat dict comprehension with coverage-aware priority selection
signal_by_symbol: dict[str, dict] = {}
_COVERAGE_PRIORITY = {"STARMINE_COVERED": 1, "NON_STARMINE_ANALYST": 0}
for row in signal_rows:
    sym = str(row.get("symbol", "")).strip().upper()
    if not sym:
        continue
    existing = signal_by_symbol.get(sym)
    if existing is None:
        signal_by_symbol[sym] = row
    else:
        # Prefer higher-priority coverage domain
        new_priority = _COVERAGE_PRIORITY.get(row.get("coverage_domain", ""), 0)
        old_priority = _COVERAGE_PRIORITY.get(existing.get("coverage_domain", ""), 0)
        if new_priority > old_priority:
            signal_by_symbol[sym] = row
```

**Scope of impact:** Only `build_analytical_universe_rows_from_current()`. All downstream code is read-only consumers; no changes required elsewhere. The fix affects `analytical_universe.csv` regeneration only — existing cached runs (`PAR-*`) are unaffected until a fresh analysis is run.

**Verification:** After applying the fix and regenerating `analytical_universe.csv`, AEIS should show `ess_score_text = "BEARISH"` in the universe file, which will propagate through all 8 stages correctly.

---

## Appendix — Signal Snapshot Evidence

```
data/current/signal_snapshot.csv line 497:
  symbol=AEIS, coverage_domain=STARMINE_COVERED,
  source_file=EquitySummaryScores-May2026.csv,
  starmine_ess_text=BEARISH, starmine_ess_numeric=2.0

data/current/signal_snapshot.csv line 2489:
  symbol=AEIS, coverage_domain=NON_STARMINE_ANALYST,
  source_file=ESS_NONE.csv,
  starmine_ess_text='', starmine_ess_numeric=''
```

```
data/current/analytical_universe.csv (AEIS row):
  ess_score_text=''
  provider_lineage=provider=FIDELITY;source_file=ESS_NONE.csv   ← sentinel won
  composite_score=4.714286  ← correctly computed from Zacks+Danelfin
```

**Note on composite_score:** Despite the ESS loss, the composite_score of 4.714286 is valid because `_score_from_inputs()` computes composite from Zacks (5.0) + Danelfin (4.0) when ESS is blank. The deployment queue ranking for AEIS is therefore accurate. Only the ESS display field is affected.
