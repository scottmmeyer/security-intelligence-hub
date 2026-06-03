# Phase 22D.11 — Source Change Audit
**Generated:** 2026-06-03  
**Baseline Commit:** `564f1a4` (HEAD → main, tag: portfolio-manager-v7.3b-stable)  
**Audit Scope:** All tracked modified source files (`git diff --name-only`)

---

## Executive Summary

**12 tracked files are modified** relative to the last commit. These represent accumulated work across multiple phases from 7.3C (pre-session) through 22D.10 (this session). None are from unknown or suspicious activity. All changes are attributable to named phases with documented mandates.

**Total diff magnitude:** +2,726 lines inserted, −30 lines deleted across 12 files.

---

## 1. `.gitignore`

| Attribute | Value |
|---|---|
| Change type | Addition |
| Lines changed | +3 |
| Phase | CONFIG / Security |
| Modified | 2026-06-02 |

**Change:** Added `.env` entry to gitignore.

**Rationale:** Correct security hygiene. The `.env.example` template (untracked, also in dirty list) documents required env vars without exposing secrets. The addition of `.env` to gitignore prevents accidental API key commit.

**Scope verdict:** EXPECTED — SAFE TO COMMIT

---

## 2. `scripts/run_outcome_ui.py`

| Attribute | Value |
|---|---|
| Change type | Modification |
| Lines changed | +67, −0 (net) |
| Phase | 22D.10 (D4) |
| Modified | 2026-06-02 20:43 |

**Change:** `/api/portfolio/deployment-plan` endpoint now reads `adjusted_deployable_mv` from `cash_context` when a settlement adjustment exists, falling back to the legacy behavior for pre-22D.10 run snapshots.

```python
# New logic in cash_arg computation:
if "adjusted_deployable_mv" in _cc:
    cash_arg = float(_cc["adjusted_deployable_mv"])
else:
    cash_arg = None  # pre-22D.10 runs fallback
```

**Scope verdict:** EXPECTED — PHASE 22D.10 ONLY — SAFE TO COMMIT

---

## 3. `src/history/analytical_universe_manager.py`

| Attribute | Value |
|---|---|
| Change type | Modification |
| Lines changed | +46, −0 (net) |
| Phase | 7.4D + 22D.2 (multi-phase) |
| Modified | 2026-06-01 20:07 |

**Changes:**
1. **Phase 7.4D — Replay evidence routing fix:** Industry-specific replays now accepted alongside cross-sector ALL replays. Previously only `filter_industry == "ALL"` rows were loaded; now `industry_replay_evidence` dict tracks symbol → {geo, cap, industry, replay_id} for industry-specific replays. ALL replays retain priority (first-seen wins).
2. **Phase 22D.2 — Replay percentile computation:** Per-symbol percentile rank computed within each replay cohort using current composite scores from `analytical_universe.csv`. Stored in `symbol_percentile` and wired to `replay_percentile` field.

**Scope verdict:** EXPECTED — MULTI_PHASE — SAFE TO COMMIT

---

## 4. `src/portfolio/enrichment.py`

| Attribute | Value |
|---|---|
| Change type | Modification |
| Lines changed | +1 |
| Phase | 7.5E |
| Modified | 2026-06-01 |

**Change:** Single line addition wiring `danelfin_score` from the analytical universe row into the enriched holding:
```python
danelfin_score=u.get("danelfin_score") or None,
```

**Scope verdict:** EXPECTED — PHASE 7.5E ONLY — SAFE TO COMMIT

---

## 5. `src/portfolio/models.py`

| Attribute | Value |
|---|---|
| Change type | Modification |
| Lines changed | +63 |
| Phase | MULTI_PHASE (7.5E, 7.5J, 22D.10) |
| Modified | 2026-06-02 20:42 |

**Changes:**
1. **Phase 7.5E:** Added `danelfin_score: Optional[str] = None` field to `PortfolioHolding` dataclass.
2. **Phase 22D.10 D1:** Added `safe_to_offset_cash: bool = False` field to `PortfolioHolding` with governance commentary.
3. **Phase 7.5J:** Added new `AnalystConsensus` dataclass (transparency-only; no scoring/ranking authority). Fields: `symbol`, `abr`, `analyst_count`, etc.

**Note:** This file contains changes from three separate phases bundled in one diff. All changes are additive (no deletions). All are coherent with the model extension pattern.

**Scope verdict:** EXPECTED — MULTI_PHASE — SAFE TO COMMIT

---

## 6. `src/portfolio/optimizer.py`

| Attribute | Value |
|---|---|
| Change type | Modification |
| Lines changed | +107, −0 (net) |
| Phase | 7.3C |
| Modified | 2026-05-30 16:08 |

**Change:** Added `_build_preferred_display()` helper function (Phase 7.3C) for side-by-side rendering of SECURITY_SUPERIOR optimizer decisions. Display-only; carries no action authority. Optimizer version bumped to `7.3C`.

**Note:** Modified before this session (2026-05-30). Pre-dates Phase 22D.10. Has been in the working tree since Phase 7.3C was executed.

**Scope verdict:** EXPECTED — PHASE 7.3C — SAFE TO COMMIT

---

## 7. `src/portfolio/recommendations.py`

| Attribute | Value |
|---|---|
| Change type | Modification |
| Lines changed | +140, −0 (net) |
| Phase | MULTI_PHASE |
| Modified | 2026-06-01 20:07 |

**Change:** Replaced naive last-row-wins dict comprehension for `signal_by_symbol` with coverage-priority-aware deduplication. `STARMINE_COVERED` now always wins over `NON_STARMINE_ANALYST` for the same symbol, preventing valid covered rows from being silently overwritten by ESS_NONE sentinel rows.

```python
_COVERAGE_PRIORITY: Dict[str, int] = {"STARMINE_COVERED": 1, "NON_STARMINE_ANALYST": 0}
```

**Scope verdict:** EXPECTED — MULTI_PHASE — SAFE TO COMMIT

---

## 8. `src/portfolio/runner.py`

| Attribute | Value |
|---|---|
| Change type | Modification |
| Lines changed | +313 |
| Phase | MULTI_PHASE (Phases 7.5B–22D.10) |
| Modified | 2026-06-02 20:43 |

**Changes (in order, all additive):**
1. **Phase 22D.10 D1:** `enriched` list comprehension applies `safe_to_offset_cash` to `ACCOUNTING_ADJUSTMENT` holdings with `market_value < 0`.
2. **Phase 22D.10 D2:** Settlement adjustment engine: sums `abs(market_value)` for `safe_to_offset_cash` excluded holdings, computes `_adjusted_deployable_mv`.
3. **Phase 22D.10 D3:** `build_deployment_plan()` now receives `_adjusted_deployable_mv` as `deployable_cash` (the CW-DAS remediation).
4. **Phase 22D.10 D4:** Writes `settlement_adjustment`, `adjusted_cash_mv`, `adjusted_deployable_mv`, `adjusted_deployable_pct` into the snapshot dict.
5. **Earlier phases:** Deployment queue integration, `build_deployment_queue()` call wiring, UCF field propagation.

**Scope verdict:** EXPECTED — MULTI_PHASE — SAFE TO COMMIT

---

## 9. `src/portfolio/scoring.py`

| Attribute | Value |
|---|---|
| Change type | Modification |
| Lines changed | +1, −1 |
| Phase | MINOR |
| Modified | 2026-06-02 |

**Change:** Single line wording fix:
```python
# Before:
"No replay percentile data available for supported holdings."
# After:
"Replay quality unavailable — no cohort percentile scores found for supported holdings."
```

**Scope verdict:** EXPECTED — TRIVIAL — SAFE TO COMMIT

---

## 10. `tests/test_optimizer.py`

| Attribute | Value |
|---|---|
| Change type | Modification |
| Lines changed | +1, −1 |
| Phase | 7.3C |
| Modified | 2026-06-02 |

**Change:** Version assertion loosened from exact match to membership check:
```python
# Before:
assert opt["optimizer_version"] == "7.3A"
# After:
assert opt["optimizer_version"] in ("7.3A", "7.3B", "7.3C")
```

**Rationale:** Correct accommodation of version evolution. Test still validates the field exists with a valid value.

**Scope verdict:** EXPECTED — PHASE 7.3C — SAFE TO COMMIT

---

## 11–12. `ui/portfolio_alignment/app.js` and `ui/portfolio_alignment/index.html`

These are covered in the dedicated UI Change Audit (`phase_22d11_ui_change_audit.md`).

---

## Cross-Phase Summary

| Phase | Files Touched |
|---|---|
| 7.3C | optimizer.py, test_optimizer.py, app.js, index.html |
| 7.4D | analytical_universe_manager.py |
| 7.5B | runner.py |
| 7.5E | enrichment.py, models.py, fidelity_signal.py (new) |
| 7.5J | models.py, analyst_consensus.py (new) |
| 7.7A | unified_conviction.py (new), runner.py |
| 22D.2 | analytical_universe_manager.py |
| 22D.10 | models.py, runner.py, run_outcome_ui.py, app.js, index.html |
| CONFIG | .gitignore |
| MINOR | scoring.py |

**Finding:** All 12 tracked modifications have clear phase attribution. No file contains unexplained changes. The multi-phase bundling in models.py, runner.py, app.js, and index.html is a consequence of these files being central integration points — changes accumulated without intermediate commits. This is the expected state given commit cadence relative to the v7.3b-stable tag.

---

## Anomaly Register

| # | Anomaly | Severity | Disposition |
|---|---|---|---|
| A1 | `app.js?v=4` not bumped to v=5 after Phase 22D.10 D5 | ADVISORY | Browser cache risk; not a correctness defect. Address before next deploy. |
| A2 | `src/portfolio/scoring.py` modified on 2026-06-02 but has only a minor wording change | INFO | Consistent with Phase 22D review pass. No concern. |
| A3 | Multi-phase bundling in `models.py`, `runner.py` | INFO | Expected for central model files. Documented above. |

**Anomalies classified as ADVISORY or INFO. No BLOCKING anomalies detected in source files.**
