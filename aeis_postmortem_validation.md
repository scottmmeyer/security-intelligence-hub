# AEIS Signal Postmortem Validation Report

**Date:** 2026-05-31  
**Reference Run (post-fix):** PAR-20260529-BAF83F16  
**Reference Run (pre-fix, immutable):** PAR-20260531-F794D952  
**Fix Applied:** Phase 7.5G-B — StarMine Coverage Overwrite Remediation  
**Source File:** `src/history/analytical_universe_manager.py` lines 465–480

---

## Summary

The AEIS signal corruption detected during Phase 7.5G-A has been fully remediated. All five validation checks pass across every artifact in the post-fix pipeline.

| Check | Expected | Actual | Result |
|-------|----------|--------|:------:|
| `analytical_universe.csv` ESS | BEARISH | BEARISH | ✅ PASS |
| `analytical_universe.csv` composite_score | 3.055556 | 3.055556 | ✅ PASS |
| `ucf_verdicts.json` ucf_label | DEPLOYMENT_CANDIDATE | DEPLOYMENT_CANDIDATE | ✅ PASS |
| AEIS in `deployment_queue.json` | Not present | Not present | ✅ PASS |
| AEIS in `deployment_plan.json` | Not present | Not present | ✅ PASS |

---

## 1. Root Cause

**Bug location:** `build_analytical_universe_rows_from_current()` in `analytical_universe_manager.py`

**Before fix (last-row-wins):**
```python
signal_by_symbol = {str(row["symbol"]).strip().upper(): row for row in signal_rows}
```

This flattened 251 symbols that had both a `STARMINE_COVERED` row and a `NON_STARMINE_ANALYST` sentinel row in `signal_snapshot.csv`. The sentinel (last row) always won, overwriting the COVERED row. For AEIS specifically, this erased the BEARISH ESS value and replaced it with a blank/neutral sentinel.

**After fix (coverage-aware priority):**
```python
_COVERAGE_PRIORITY: Dict[str, int] = {"STARMINE_COVERED": 1, "NON_STARMINE_ANALYST": 0}
signal_by_symbol: Dict[str, dict] = {}
for _row in signal_rows:
    _sym = str(_row.get("symbol", "")).strip().upper()
    if not _sym:
        continue
    _existing = signal_by_symbol.get(_sym)
    if _existing is None:
        signal_by_symbol[_sym] = _row
    else:
        _new_pri = _COVERAGE_PRIORITY.get(str(_row.get("coverage_domain", "")), 0)
        _old_pri = _COVERAGE_PRIORITY.get(str(_existing.get("coverage_domain", "")), 0)
        if _new_pri > _old_pri:
            signal_by_symbol[_sym] = _row
```

`STARMINE_COVERED` always wins over `NON_STARMINE_ANALYST` regardless of row order.

---

## 2. AEIS Signal Journey

### Pre-Fix State (PAR-20260531-F794D952)

| Artifact | ESS | Composite | UCF Label | In Queue |
|----------|-----|:---------:|-----------|:--------:|
| `analytical_universe.csv` | (blank) | 4.714286 | — | — |
| `holdings.csv` | (blank) | 4.714286 | — | — |
| `security_overlays.csv` | (blank) | 4.714286 | — | — |
| `ucf_verdicts.json` | — | 4.714286 | CCL | — |
| `deployment_queue.json` | — | 4.714286 | CORE_CONVICTION_LEADER | Rank #1 |

**Corrupted state:** Blank ESS produced inflated composite. AEIS entered the queue at rank #1 as a false CCL candidate.

### Post-Fix State (PAR-20260529-BAF83F16)

| Artifact | ESS | Composite | UCF Label | In Queue |
|----------|-----|:---------:|-----------|:--------:|
| `analytical_universe.csv` | BEARISH | 3.055556 | — | — |
| `holdings.csv` | BEARISH | 3.055556 | — | — |
| `security_overlays.csv` | BEARISH | 3.055556 | — | — |
| `ucf_verdicts.json` | — | 3.055556 | DEPLOYMENT_CANDIDATE | — |
| `deployment_queue.json` | — | — | — | Not present |

**Corrected state:** BEARISH ESS depresses composite to 3.055556. AEIS correctly classifies as DEPLOYMENT_CANDIDATE (UCF rank 42) and is excluded from the deployment queue.

---

## 3. Signal Direction Trace

**ESS source row (STARMINE_COVERED):**
- `starmine_ess_text = BEARISH`
- `coverage_domain = STARMINE_COVERED`
- `source_file = EquitySummaryScores-May2026.csv`
- `provider = FIDELITY`

**Composite scoring impact:**
- With blank ESS (pre-fix): weighted composite inflated to ~4.714
- With BEARISH ESS (post-fix): composite = 3.055556 (correct; BEARISH is a negative signal)

**UCF scoring impact:**
- Pre-fix: CCL threshold met at fake composite ~4.714
- Post-fix: composite 3.055556 → UCF score 58.49 → DEPLOYMENT_CANDIDATE (not CCL/HCA)

**Deployment queue impact:**
- Pre-fix: AEIS ranked #1 (falsely)
- Post-fix: AEIS absent from deployment queue (correctly excluded)

---

## 4. Blast Radius Context

The Phase 7.5G-B fix affected 251 symbols total (all 251 with both COVERED and NON_COVERED rows). Of these, 5 portfolio holdings had a material ESS change:

| Symbol | ESS Before | ESS After | Composite Before | Composite After | Rank Impact |
|--------|------------|-----------|:----------------:|:---------------:|-------------|
| AEIS | (blank) | BEARISH | 4.714286 | 3.055556 | Dropped from queue |
| CIEN | (blank) | BULLISH | lower | 4.2778 | Rank #13 (post-fix) |
| NUE | (blank) | BULLISH | lower | 4.1111 | Rank #14 (post-fix) |
| SANM | (blank) | BULLISH | lower | 4.2778 | Rank #11 (post-fix) |
| PLTR | (blank) | NEUTRAL | minor | minor | No queue impact |

CIEN, NUE, SANM had ESS restored to BULLISH, which improved their composites and moved them into the audited top-20.

---

## 5. Historical Artifact Disposition

| Artifact | Fix Applied | State |
|----------|:-----------:|-------|
| `data/current/analytical_universe.csv` | ✅ REBUILD-20260531-FIX | Corrected |
| `PAR-20260529-BAF83F16` (all artifacts) | ✅ Post-fix PAR run | Corrected |
| `PAR-20260531-F794D952` (all artifacts) | ❌ Pre-fix, immutable | Stale (by design) |

The old PAR run (F794D952) is immutable historical data. Its stale state is expected and does not contaminate the current pipeline. Any future analysis must reference PAR-20260529-BAF83F16 or later runs.

---

## 6. Test Coverage

Tests updated to reflect corrected rankings:

| Test | Change | Reason |
|------|--------|--------|
| `test_ac1_vrt_ranks_first` | Renamed from `test_ac1_aeis_ranks_first` | VRT is correctly #1 post-fix |
| `test_ac2_arw_ranks_second` | Renamed from `test_ac2_vrt_ranks_second` | ARW is correctly #2 post-fix |

**Test suite status:** 752 passed, 1 skipped, 0 failed (2026-05-31)

---

## 7. Validation Status

**Phase 7.5G-B remediation is complete and validated.**

All post-fix artifacts reflect the corrected BEARISH ESS for AEIS. The composite signal, UCF classification, and deployment queue exclusion are all correct. No stale artifacts from the pre-fix state are present in any active pipeline component.
