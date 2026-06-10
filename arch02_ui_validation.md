# ARCH-02: UI Validation

**Date:** 2026-06-09  
**PAR:** PAR-20260609-87134CE1

---

## Reduction Queue — Expected Content

Using `build_capital_sources()` with PAR-87134CE1 data:

| Rank | Symbol | Priority | Category | Est. Proceeds | Blocked | Policy |
|---|---|---|---|---|---|---|
| 1 | **TSLA** | — | SIGNAL_DETERIORATION | $13,904 | **YES** | DO_NOT_SELL |
| 2 | LMAT | MODERATE | TAX_AWARE_EXIT | $7,133 | No | — |
| 3 | CIEN | MODERATE | TAX_AWARE_EXIT | $4,667 | No | — |
| 4 | DVN | MODERATE | TAX_AWARE_EXIT | $4,508 | No | — |
| 5 | SBS | LOW | OVERWEIGHT_REDUCTION | $4,389 | No | — |
| 6 | VB | MODERATE | LOW_CONVICTION_REDUCTION | $4,340 | No | — |
| 7 | VOO | MODERATE | LOW_CONVICTION_REDUCTION | $4,248 | No | — |
| 8 | MSFT | MODERATE | TAX_AWARE_EXIT | $4,117 | No | — |
| 9 | ANIP | MODERATE | TAX_AWARE_EXIT | $4,006 | No | — |
| 10 | AVGO | MODERATE | TAX_AWARE_EXIT | $3,966 | No | — |

**DODFX** ($3,728, OVERWEIGHT_REDUCTION, SELL_LAST) appears at rank 11 in the queue — shown with ⏸ Sell Last badge.

**Capital Pool displayed:** ~$96,633 (excludes TSLA blocked proceeds)

---

## Q3: What Does the Reduction Queue Show Today?

The Reduction Queue shows the top 10 CRA capital sources by priority:

1. **TSLA** at rank 1 — blocked by DO_NOT_SELL (shown with 🔒 badge, reduced opacity). This is correct: TSLA is the highest-urgency reduction candidate, and the blocked state is disclosed rather than hidden.
2. Ranks 2–10 are all EXECUTABLE reduction candidates across TAX_AWARE_EXIT, OVERWEIGHT_REDUCTION, and LOW_CONVICTION_REDUCTION categories.
3. No DEFER-priority sources appear in the top 10.
4. Pool header shows "$96,633 est. pool" and "1 blocked by policy".

## Q4: Are Any Protected Assets Visible?

**Yes — TSLA is visible with its blocked state disclosed.**

This is intentional design: hiding TSLA from the Reduction Queue would mislead the operator about the portfolio's true reduction picture. TSLA is the highest-urgency reduction candidate (RPS=85, VERY_BEARISH, overweight node) and the operator should understand it exists and is blocked by their own policy.

The 🔒 Blocked badge + reduced opacity makes the blocked state immediately clear. The UX-PA-06 "To unblock" guidance in the PAP provides the action path.

**No other protected assets appear in the top 10.** MU (DO_NOT_SELL via TSLA rec propagation) has RPS=9 and would appear at a low rank if present at all — the multi-symbol policy propagation from the REDUCE_OVERWEIGHT rec does not affect MU's individual CRA capital source entry (the CRA builder evaluates policy per-symbol independently).

---

## Verification Checklist

| Check | Status |
|---|---|
| Reduction Queue section renders after DQ | ✓ HTML section added |
| Placeholder shows while CRA loads | ✓ `renderReductionQueuePlaceholder()` in `renderResults()` |
| Renders on CRA load | ✓ Hook in `loadCRAProposal()` |
| Sources sorted by priority then proceeds | ✓ `_RQ_PRIORITY_ORDER` sort |
| Blocked assets shown with badge | ✓ `rq-policy-blocked` class, reduced opacity row |
| SELL_LAST shown with badge | ✓ `rq-policy-deferred` class |
| Pool total shown | ✓ `rq-pool-badge` in header |
| FVI data shown when available | ✓ `fviBadge` from `_lastAnalysisData.fvi_data` |
| Advisory note present | ✓ "guidance only, not trade instructions" |
| No CW-DAS changes | ✓ No changes to deployment_queue.py |
| No RPS changes | ✓ No changes to rec generation |
| No CRA logic changes | ✓ No changes to capital_source_builder.py |
| No PAP changes | ✓ No changes to recommendations.py |
| No policy changes | ✓ No changes to operator_policy.py |
| `escHtml()` on all dynamic content | ✓ Applied to symbol, category, evidence |
