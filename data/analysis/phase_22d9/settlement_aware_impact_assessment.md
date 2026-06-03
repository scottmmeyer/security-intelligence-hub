# Phase 22D.9 — Workstream E: Settlement-Aware Implementation Impact Assessment

**Phase:** 22D.9 — Settlement-Aware Deployable Cash  
**Date:** 2026-06-02  
**Design Option Assessed:** Option B (dual display — recommended)  
**Note:** Option C is also assessed for reference. No code changes are made by this phase.

---

## 1. Summary of Required Changes (Option B)

Option B adds advisory settlement-aware fields to `cash_context` without changing the
existing `compute_deployable_cash()` function signature or its core math.

| Layer | File | Type of Change | Lines Affected |
|-------|------|----------------|----------------|
| Backend — cash context augmentation | `src/portfolio/runner.py` | New post-processing block | After line 725 |
| UI — conditional settlement panel | `ui/portfolio_alignment/app.js` | New conditional render | After line 2091 |
| UI — deployable cash annotation | `ui/portfolio_alignment/app.js` | Optional label update | Line 2204 |

**No changes required to:**
- `src/portfolio/deployment_queue.py` — `compute_deployable_cash()` is untouched
- `src/portfolio/ingestion.py` — classification logic is correct as-is
- `config/` files — no model changes
- `src/portfolio/archetype.py` — no archetype changes

---

## 2. Option B — Detailed Change Specification

### 2a. `src/portfolio/runner.py` — Augment `cash_context` After Computation

**Location:** After line 725 (after `cash_context = compute_deployable_cash(...)`)

**Change:** Add a block that inspects `enriched` (not `investable`) for negative
`ACCOUNTING_ADJUSTMENT` rows and, if found, computes settlement-aware advisory fields:

```python
# ── Phase 22D.9 — Settlement-aware advisory fields ───────────────────────────
_adj_rows = [
    h for h in enriched
    if h.operational_state == "ACCOUNTING_ADJUSTMENT" and h.market_value < 0
]
if _adj_rows:
    _pending_mv = sum(h.market_value for h in _adj_rows)  # negative sum
    _adj_cash_mv = cash_context["cash_mv"] + _pending_mv
    _adj_cash_pct = (_adj_cash_mv / snapshot.total_market_value * 100.0
                     if snapshot.total_market_value else 0.0)
    _adj_floor_mv = cash_context["floor_mv"]               # floor unchanged
    _adj_deployable = max(0.0, _adj_cash_mv - _adj_floor_mv)
    _adj_deployable_pct = (_adj_deployable / snapshot.total_market_value * 100.0
                           if snapshot.total_market_value else 0.0)
    cash_context.update({
        "pending_settlement_mv":      round(_pending_mv, 2),
        "adjusted_cash_mv":           round(_adj_cash_mv, 2),
        "adjusted_cash_pct":          round(_adj_cash_pct, 4),
        "adjusted_deployable_mv":     round(_adj_deployable, 2),
        "adjusted_deployable_pct":    round(_adj_deployable_pct, 4),
    })
```

**Key design decisions:**
- The `cash_context` dict is extended with optional keys — consumers that don't know
  about the new keys continue to work unchanged (no breaking change)
- `floor_mv` is deliberately NOT adjusted (the floor is based on `total_market_value`
  which already includes the negative pending row — changing the floor requires a
  separate governance decision)
- This block only fires when negative ACCOUNTING_ADJUSTMENT rows exist — zero cost
  when the portfolio has no pending activity

### 2b. `ui/portfolio_alignment/app.js` — Conditional Settlement Panel

**Location:** After the existing cash display block (after line 2091)

**Change:** Add settlement panel, suppressed when `adjusted_deployable_mv` is absent:

```javascript
// Settlement-aware display (Option B)
const hasPendingSettlement = cashCtx.pending_settlement_mv != null
                              && cashCtx.pending_settlement_mv < 0;
if (hasPendingSettlement) {
    const pendingFmt  = formatCurrency(cashCtx.pending_settlement_mv);
    const adjCashFmt  = formatCurrency(cashCtx.adjusted_cash_mv);
    const adjCashPct  = (cashCtx.adjusted_cash_pct || 0).toFixed(2);
    const adjDeployFmt = formatCurrency(cashCtx.adjusted_deployable_mv);
    // render settlement panel with ⚠ header, adjusted figures, advisory note
}
```

**Line 2204 — optional annotation:** When `hasPendingSettlement`, append "(pre-settlement)"
to the reported `deployable_mv` display to distinguish it from the adjusted figure.

---

## 3. Option C — Additional Changes Required (Reference Only; Not Recommended Now)

Option C changes `compute_deployable_cash()` itself. The additional work beyond Option B:

| File | Change | Risk |
|------|--------|------|
| `src/portfolio/deployment_queue.py` | Modify function signature: add `adjustment_holdings` param | Function signature break |
| `src/portfolio/deployment_queue.py` | Subtract negative adjustments from `cash_mv` in core math | Changes output of all calls |
| `src/portfolio/runner.py` | Pass non-investable ACCOUNTING_ADJUSTMENT rows as new param | — |
| Tests (see Section 5) | Update all expected `deployable_mv` values | Multiple test files |

Estimated regression surface: **all tests in `tests/test_7_5b_deployment_queue.py`** (20+
assertions referencing `deployable_mv`), plus any integration tests that compare
deployment plan outputs.

---

## 4. Regression Risk Assessment

### Option B Regression Risk: **Very Low**

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| New fields cause JSON serialization errors | Low | Standard Python dicts; JSON-safe values |
| UI rendering breaks when new keys absent | Low | All new keys conditional; suppressed by default |
| Existing tests fail | Very Low | Core math unchanged; new keys are additive |
| `deployment_plan.deployable_cash` changes | None | Not touched by Option B |
| Phase 22D.6 certification invalidated | None | PAR-20260602-4A83D5BD had no pending activity; `adjusted_*` fields not added to that run |

The only new code path (`if _adj_rows:`) is dead code when no pending activity exists.
The PAR-20260602-4A83D5BD certification run has no pending activity → no changes to its outputs.

### Option C Regression Risk: **Moderate**

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Test suite failures | High | All `compute_deployable_cash` tests reference specific `deployable_mv` values |
| Audit trail discontinuity | Medium | Reported `deployable_mv` changes vs. prior certified values |
| Phase 22D.6 certification basis changes | Medium | PAR-20260602-4A83D5BD (`deployable_mv=$7,724.82`) is unaffected only because it has no pending activity |
| Classification edge case: non-settlement adjustments | Low-Medium | Requires classification guard (`SAFE_TO_OFFSET_CASH` check from inventory) |

---

## 5. Test Impact

### Tests to verify (do not change; confirm still pass with Option B):

| Test file | Test(s) | Expected behavior |
|-----------|---------|-------------------|
| `tests/test_7_5b_deployment_queue.py` | All `compute_deployable_cash` tests | Pass unchanged (function not modified) |
| `tests/test_7_5b_deployment_queue.py` | `test_ac1_deployable_mv_uses_mandate_target` | Pass: $7,909 reported deployable unchanged |
| `tests/test_7_5b_deployment_queue.py` | `test_ac2_after_deploy_remaining_at_mandate` | Pass: floor math unchanged |
| Any integration test that checks `cash_context` field count | Verify | New fields are additive — only affect runs with pending activity |

### New tests to write if Option B is implemented:

| Test name | Assertion |
|-----------|-----------|
| `test_settlement_fields_absent_without_adjustment` | When no ACCOUNTING_ADJUSTMENT rows: `pending_settlement_mv` not in `cash_context` |
| `test_settlement_fields_present_with_negative_adjustment` | When negative ACCOUNTING_ADJUSTMENT exists: `adjusted_deployable_mv` < `deployable_mv` |
| `test_zero_mv_adjustment_not_included` | MV=$0.00 ACCOUNTING_ADJUSTMENT rows: no settlement fields added |
| `test_adjusted_deployable_exact_prg_case` | Run PAR-20260602-8CF1CB84: `adjusted_deployable_mv ≈ 4091.70` |

---

## 6. Governance Implications

| Topic | Status |
|-------|--------|
| `deployment_plan.deployable_cash` | Unchanged (still reported figure) — audit trail intact |
| Mandate floor compliance | Still measured against reported `cash_mv` — no policy change |
| Certified run (PAR-20260602-4A83D5BD) | Unaffected — no pending activity in that run |
| New fields | Advisory only — not operative for mandate compliance |
| Settlement date estimation | UI-only heuristic (T+1 from snapshot_date); does not affect calculations |
| Adjustment classification | Currently: all observed adjustments are SAFE_TO_OFFSET_CASH (Pending activity) |
| When Option C should be revisited | After: (1) formal classification tightening, (2) governance approval, (3) test update plan |

---

## 7. Restart Requirement

Per Phase 22D.6 and 22D.7 lessons: **any code change requires server restart before
regenerating runs** to avoid stale-process artifacts.

If Option B backend change is implemented:
1. Stop server (`pkill -f run_outcome_ui.py`)
2. Restart (`PYTHONPATH=. .venv/bin/python3 scripts/run_outcome_ui.py &`)
3. Re-ingest PAR-20260602-8CF1CB84 source CSV to verify `adjusted_*` fields appear
4. Verify PAR-20260602-4A83D5BD re-run does NOT have `adjusted_*` fields (no pending activity)

---

## 8. Summary Verdict

**Option B can be implemented safely** with minimal regression risk. The only substantive
risk is UI rendering when the new fields are absent — which is mitigated by conditional
suppression.

**Option C must not be implemented** without:
1. Updating all `test_7_5b_deployment_queue.py` assertions
2. Governance sign-off on changing the operative cash calculation
3. Classification guard to exclude non-settlement adjustment types
