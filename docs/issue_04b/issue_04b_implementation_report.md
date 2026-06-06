# ISSUE-04B — Implementation Report
## Dislocation Backend Classifier — Class A1

**Date:** June 5, 2026  
**Status:** COMPLETE  
**Scope:** Backend classifier + API payload wiring + unit tests. No UI changes.

---

## 1. Summary

Replaced the JavaScript-only `_fmpDislocationType()` heuristic with a
backend-computed dislocation classification that flows through the standard SIH
payload architecture. The new `dislocation_by_symbol` key appears in every run
response alongside `analyst_consensus_by_symbol` and `fidelity_signals_by_symbol`.

---

## 2. Files Created / Modified

| File | Change |
|------|--------|
| `src/portfolio/dislocation.py` | New module — Class A1 classifier, `DislocationType`, `build_dislocation_payload()` |
| `src/portfolio/runner.py` | Import + `_build_dislocation_payload()` builder + wire into `run_analysis()` return + `load_analysis_run()` |
| `tests/test_issue_04b_dislocation.py` | 26 unit tests |

**No UI changes. No scoring changes. No CW-DAS changes. No CRA changes.**

---

## 3. Module Design — `src/portfolio/dislocation.py`

### Public API

```python
classify_dislocation(symbol, fmp_row, overlay) -> DislocationType
build_dislocation_payload(overlays, fmp_by_sym) -> dict[str, dict]
```

### `DislocationType` dataclass

```python
@dataclasses.dataclass(frozen=True)
class DislocationType:
    symbol:            str     # uppercase ticker
    tier:              str     # NONE | WATCH | MODERATE | HIGH_CONVICTION
    dislocation_class: str     # A1_FUNDAMENTAL_BEAT_DIVERGENCE | NONE
    evidence:          tuple   # 2–4 human-readable strings
    version:           str     # "1.0" — bump on algorithm changes
```

### Governance constants

```python
DISLOCATION_NONE              = "NONE"
DISLOCATION_WATCH             = "WATCH"
DISLOCATION_MODERATE          = "MODERATE"
DISLOCATION_HIGH_CONVICTION   = "HIGH_CONVICTION"
DISLOCATION_CLASS_A1          = "A1_FUNDAMENTAL_BEAT_DIVERGENCE"
DISLOCATION_VERSION           = "1.0"
```

---

## 4. Class A1 Logic — Tier Assignment

**Gate 1:** FMP coverage must not be NO_DATA / ETF_NOT_APPLICABLE  
**Gate 2:** `thesis_integrity` must be INTACT  
**Gate 3:** `beat_rate_8q` ≥ 0.625 (5/8 quarters minimum)

| Tier | Beat Rate | ESS | Danelfin | Consistency |
|------|-----------|-----|----------|-------------|
| HIGH CONVICTION | ≥ 87.5% | BEARISH or VERY_BEARISH | < 2.0 (or ESS = VERY_BEARISH) | Any (CONSISTENT strengthens) |
| MODERATE | ≥ 75% | BEARISH or NEUTRAL | < 3.0 | Not CONTRADICTORY |
| MODERATE (variant) | ≥ 87.5% | BEARISH | Any | Not CONTRADICTORY |
| WATCH | ≥ 62.5% | NEUTRAL | < 3.5 | Any |
| WATCH (cap) | Any | Any | Any | CONTRADICTORY → caps HIGH/MODERATE to WATCH |
| NONE | All other cases | | | |

---

## 5. Integration Architecture

```
Security overlays (built in run_analysis())
  └── _build_dislocation_payload(overlays)
        └── load_fmp_enriched_universe()
              └── classify_dislocation(symbol, fmp_row, overlay)
                    └── _classify_thesis_integrity(fmp_row)
                    └── _classify_fundamental_consistency(fmp_row, ess, thesis)
                    └── _classify_a1(thesis, consistency, beat_rate, ess, danelfin, revenue_growth, coverage)
                          └── DislocationType(tier, class, evidence, version)
```

Result key in API response: `dislocation_by_symbol[SYMBOL]`

Both `run_analysis()` (POST /api/portfolio/analyze) and
`load_analysis_run()` (GET /api/portfolio/runs/{id}) now emit this key.

---

## 6. Approved Inputs Used

| Input | Source | Role |
|-------|--------|------|
| `thesis_integrity` | `_classify_thesis_integrity(fmp_row)` | GATING — must be INTACT |
| `beat_rate_8q` | `fmp_row["beat_rate_8q"]` | PRIMARY — tier driver |
| `ess_score_text` | `overlay.ess_score_text` | PRIMARY divergence signal |
| `danelfin_score` | `overlay.danelfin_score` | PRIMARY divergence signal |
| `fundamental_consistency` | `_classify_fundamental_consistency()` | SUPPORTING — caps CONTRADICTORY |
| `revenue_growth_q1_yoy` | `fmp_row["revenue_growth_q1_yoy"]` | CONFIRMING — evidence text only |

**Approved suppressions honored — not used:**  
CW-DAS, composite_score, portfolio_weight, allocation_drift, market_cap,  
STI classification, upside_pct, analyst_targets.

---

## 7. Governance

| Property | Value |
|----------|-------|
| Scoring influence | None |
| Ranking influence | None |
| CW-DAS influence | None |
| CRA influence | None |
| Action implied | None — informational advisory only |
| Version | `DISLOCATION_VERSION = "1.0"` |
