# Phase 7.3B — Optimizer UI Validation Report

**Generated:** 2026-05-30  
**Phase:** 7.3B — Optimizer Conflict Surfacing  
**Optimizer version:** 7.3A  
**Governance baseline:** Legacy recommendation ordering and count UNCHANGED. `optimizer_metadata` is additive only.

---

## 1. Purpose

This report validates that the Phase 7.3B UI additions (conflict badges, Optimizer View block, Optimizer Summary Panel) correctly reflect the conflict signals produced by the Phase 7.3A parallel optimizer. It does not validate trade decisions or portfolio actions — those remain entirely under legacy recommendation authority.

---

## 2. Governance Constraints Verified

| Constraint | Status | Evidence |
|---|---|---|
| Legacy recommendation count unchanged after optimizer injection | ✅ PASS | `test_legacy_rec_count_unchanged` — count identical before/after `run_parallel_optimizer` |
| Legacy recommendation order unchanged | ✅ PASS | `test_legacy_rec_order_unchanged` — `recommendation_id` sequence preserved |
| `optimizer_metadata` is additive only | ✅ PASS | Injected as new key; no existing field mutated |
| Badges render only when `optimizer_metadata` exists | ✅ PASS | `test_badge_derivation_safe_when_no_metadata` — no crash on absent metadata |
| No portfolio action changed | ✅ PASS | Optimizer returns read-only conflict signals; runner does not alter `action` field |
| No optimizer scoring change | ✅ PASS | `score_etf_candidate` / `score_security_candidate` untouched in Phase 7.3B |

---

## 3. Optimizer Decision Cases

The table below documents the six canonical scenarios, the live optimizer decision from the 7.3A engine, and the corresponding UI badges the JavaScript `_buildOptimizerBadges()` helper will render.

| # | Node | Legacy Action | Mandate | Optimizer Decision | PIS (best) | ETF Gate | UI Badges |
|---|---|---|---|---|---|---|---|
| 1 | EQUITIES.US.LARGE | INCREASE_UNDERWEIGHT | INFORMATIONAL (CONCENTRATED_ALPHA) | **MANDATE_BLOCKED** | — | VOO/IVV/SPY: FAIL | `MANDATE_BLOCKED` `ETF_GATE_FAILED` `WORSENS_OVERWEIGHT` `CONFLICTS_WITH_MANDATE` |
| 2 | EQUITIES.US.LARGE | INCREASE_UNDERWEIGHT | STANDARD | **NO_CANDIDATES** | — | VOO: FAIL | `NO_CANDIDATES` `ETF_GATE_FAILED` `WORSENS_OVERWEIGHT` |
| 3 | EQUITIES.US.LARGE | INCREASE_UNDERWEIGHT | STANDARD | **SECURITY_SUPERIOR** | 68 (portfolio security) | VOO: FAIL | `SECURITY_SUPERIOR` `ETF_GATE_FAILED` `WORSENS_OVERWEIGHT` |
| 4 | EQUITIES.INTERNATIONAL.LARGE | INCREASE_UNDERWEIGHT | STANDARD | **NO_CANDIDATES** | — | VOO: FAIL | `NO_CANDIDATES` `ETF_GATE_FAILED` `WORSENS_OVERWEIGHT` |
| 5 | EQUITIES.US.SMALL | INCREASE_UNDERWEIGHT | STANDARD | **NO_CANDIDATES** | — | (none) | `NO_CANDIDATES` |
| 6 | EQUITIES.US.MEGA.HYPER_MEGA | REDUCE_OVERWEIGHT | — | REDUCE_COHERENT | — | (none) | *(no badges — not INCREASE_UNDERWEIGHT scope)* |

### Case notes

**Case 1 — MANDATE_BLOCKED (CONCENTRATED_ALPHA / INFORMATIONAL)**  
- VOO, IVV, and SPY all receive `etf_gate = "FAIL [suitability=LOW; NCS=0.0%<10.0%; worsens_overweight=True]"`.  
- `mandate_blocked = True` because the CONCENTRATED_ALPHA mandate interprets this underweight as intentional.  
- `CONFLICTS_WITH_MANDATE` badge derived from `mandate_blocked = True`.  
- The legacy recommendation (INCREASE_UNDERWEIGHT) remains in its original position with its original priority — the badge is informational only.

**Case 2 — NO_CANDIDATES (ETF gate fail, no available securities)**  
- VOO fails the ETF gate: `suitability_tier = LOW`, `NCS = 0.0%` (below 10% threshold), `worsens_overweight = True`.  
- No portfolio securities available to substitute.  
- Optimizer surfaces `NO_CANDIDATES` + `ETF_GATE_FAILED` conflict badges — operator is informed there is no clean vehicle path.

**Case 3 — SECURITY_SUPERIOR (VRT / LRCX / DELL outrank VOO)**  
- VOO continues to fail its ETF gate.  
- VRT (composite=4.556, BULLISH, replay-supported): PIS ≥ 60.  
- LRCX (composite=4.500, BULLISH, replay-supported) and DELL (composite=4.500): PIS > VOO's PIS of 0.  
- Preferred candidate PIS = 68.  
- `SECURITY_SUPERIOR` badge informs the operator that high-conviction securities are a cleaner path than the legacy ETF vehicles — no action is forced.

**Case 4 — INTL LARGE + ETF gate fail**  
- Same ETF gate logic as Case 2 applied to EQUITIES.INTERNATIONAL.LARGE.  
- No securities in scope; `NO_CANDIDATES` + `ETF_GATE_FAILED` surfaced.

**Case 5 — US SMALL / no vehicles at all**  
- No ETF suitability notes and no portfolio securities for EQUITIES.US.SMALL.  
- `NO_CANDIDATES` badge only; no ETF gate result (no candidates to gate).

**Case 6 — REDUCE_OVERWEIGHT (not in optimizer scope)**  
- Optimizer returns `REDUCE_COHERENT` but the UI badge logic does not surface badges for REDUCE decisions.  
- No badge rendered; legacy rec card unchanged.

---

## 4. ETF Gate Detail

The ETF gate `FAIL` string format for all cases where VOO (or IVV / SPY) is the only vehicle:

```
FAIL [suitability=LOW; NCS=0.0%<10.0%; worsens_overweight=True]
```

Three conditions must all clear for a PASS:
1. `suitability_tier` is IDEAL, HIGH, or ACCEPTABLE (not LOW or INADEQUATE)
2. Net Contribution Score (NCS) ≥ 10%
3. `worsens_existing_overweight` is False

When VOO covers the large-cap blend space but the portfolio is already overweight large-cap mega (HYPER_MEGA / EXTENDED_MEGA), adding VOO worsens the overweight, triggering condition 3. The NCS and suitability tier FAIL independently as well.

---

## 5. Test Suite Results

**Run date:** 2026-05-30  
**Command:** `PYTHONPATH=. pytest -q`

| Test file | Tests | Result |
|---|---|---|
| `tests/test_7_3b_optimizer_ui.py` | 15 | ✅ 15 passed |
| All other test files | 489 | ✅ 489 passed |
| **Total** | **504** | **✅ 504 passed, 0 failed** |

### Phase 7.3B test coverage

| Test | Description | Result |
|---|---|---|
| `test_optimizer_metadata_shape_for_ui` | All required fields present on `optimizer_metadata` | ✅ |
| `test_etf_gate_failed_badge_derivable` | ETF_GATE_FAILED derivable from LOW suitability + worsens OW | ✅ |
| `test_mandate_blocked_badge_derivable` | MANDATE_BLOCKED derivable from INFORMATIONAL mandate | ✅ |
| `test_security_superior_badge_derivable` | SECURITY_SUPERIOR derivable when VRT/LRCX outrank VOO | ✅ |
| `test_worsens_overweight_badge_derivable` | WORSENS_OVERWEIGHT derivable from `worsens_overweight=True` | ✅ |
| `test_legacy_rec_count_unchanged` | Rec list count unchanged after optimizer | ✅ |
| `test_legacy_rec_order_unchanged` | Rec list order unchanged after optimizer | ✅ |
| `test_optimizer_summary_stats_correct` | Summary panel counts match actual optimizer output | ✅ |
| `test_preferred_candidate_is_highest_pis` | `preferred_candidate` is max-PIS candidate | ✅ |
| `test_voo_etf_gate_failed_for_us_large` | VOO identified as ETF_GATE_FAILED for US LARGE | ✅ |
| `test_us_large_mandate_blocked_under_concentrated_alpha` | US Large = MANDATE_BLOCKED under CONCENTRATED_ALPHA | ✅ |
| `test_all_increase_uw_recs_receive_optimizer_metadata` | All INCREASE_UNDERWEIGHT recs receive metadata | ✅ |
| `test_badge_derivation_safe_when_no_metadata` | No crash on absent `optimizer_metadata` | ✅ |
| `test_legacy_vehicles_populated_from_affected_symbols` | `legacy_vehicles` matches `affected_symbols` | ✅ |
| `test_conflicts_with_mandate_badge_derivable` | CONFLICTS_WITH_MANDATE badge when `mandate_blocked=True` | ✅ |

---

## 6. UI Component Inventory

### Part A — Recommendation conflict badges
- **Container class:** `.optimizer-badge-row`
- **Badge classes:** `.opt-badge`, `.opt-badge-MANDATE_BLOCKED`, `.opt-badge-ETF_GATE_FAILED`, `.opt-badge-SECURITY_SUPERIOR`, `.opt-badge-CONFLICTS_WITH_MANDATE`, `.opt-badge-WORSENS_OVERWEIGHT`, `.opt-badge-ACTIONABLE`, `.opt-badge-NO_CANDIDATES`, `.opt-badge-ETF_GATED`
- **JS helper:** `_buildOptimizerBadges(r)` in `app.js`
- **Render condition:** Only renders when `r.optimizer_metadata` is truthy

### Part B — Collapsible Optimizer View block
- **Toggle class:** `.optimizer-view-toggle`
- **Body class:** `.optimizer-view-body` (`.open` state)
- **Row classes:** `.optview-row`, `.optview-label`, `.optview-val`, `.optview-chip`, `.optview-etf-row`
- **JS helpers:** `_buildOptimizerViewBlock(r)`, `toggleOptimizerView(optId)`
- **Content:** Legacy vehicles, optimizer decision, rationale, security alternatives (with PIS), ETF gate result, legacy-vs-optimizer decision
- **Toggle pattern:** Same `togglePmiMandate` / `toggleTrace` pattern used throughout the app

### Part C — Optimizer Summary Panel
- **Container:** `#optimizerSummaryContainer` (in `#recommendationsPanel`)
- **Panel class:** `.opt-summary-panel`
- **Stat classes:** `.opt-stat-card`, `.opt-stat-val`, `.opt-stat-val.warn`, `.opt-stat-val.alert`, `.opt-stat-lbl`
- **JS function:** `renderOptimizerSummary(recs)` called from `renderResults()`
- **Counts surfaced:** Reviewed, Mandate Blocked, ETF Gate Failed, Security Superior, No Candidates, No Conflict

---

## 7. What Phase 7.3B Does Not Do

This phase is **informational only**. The following are explicitly out of scope and untouched:

- Reordering recommendations
- Suppressing legacy recommendations
- Changing portfolio actions
- Changing optimizer scoring algorithms
- Executing trades or generating trade instructions
- Providing UI authority for optimizer output over legacy recommendations

The operator sees conflict badges and can expand the Optimizer View for context. All decisions remain with the operator.

---

## 8. Files Changed

| File | Change type | Description |
|---|---|---|
| `ui/portfolio_alignment/index.html` | Modified | Added optimizer CSS classes; added `#optimizerSummaryContainer` placeholder |
| `ui/portfolio_alignment/app.js` | Modified | Added `renderOptimizerSummary`, `_buildOptimizerBadges`, `_buildOptimizerViewBlock`, `toggleOptimizerView`; wired into `renderResults` and `renderRecommendations` |
| `tests/test_7_3b_optimizer_ui.py` | Created | 15 validation tests for Phase 7.3B data contract and badge derivation logic |

No changes to `src/portfolio/optimizer.py`, `src/portfolio/runner.py`, or any data pipeline files.
