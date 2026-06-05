# Phase 23.0C — Final Verdict

**Date**: 2026-06-03  
**Status**: IMPLEMENTATION COMPLETE — PENDING RUNTIME VALIDATION

## What Was Built

Phase 23.0C replaces the Phase 23.0A Tax-Aware Actions framework with a four-category **Portfolio Action Pipeline**. This is an architectural correction — the original framework used tax context as the primary filter with signal as modifier, which inverted the correct decision hierarchy.

The new pipeline uses signal authority and allocation mandate as primary drivers, with tax context deferred to a future layer (Phase 23.0D, requiring cost basis enrichment of the overlay).

## Components Delivered

| Component | Description | Status |
|-----------|-------------|--------|
| C1 | Field mapping repair (`recommended_action` → `opportunity_flag`) | ✅ |
| C2 | Strategic Exit — operator-designated exit management with persistent API | ✅ |
| C3 | Allocation Reduction — REDUCE_OVERWEIGHT node membership logic | ✅ |
| C4 | Funding Sources — conviction-protected exclusions + cross-reference | ✅ |
| C5 | UI — accordion categories, priority badges, strategic exit manager | ✅ |
| API | `/api/operator/strategic-exits` GET + POST | ✅ |

## Architectural Decisions

**Conviction protection**: HIGH_CONVICTION_ANCHOR and CORE_CONVICTION_LEADER tiers from the deployment queue are excluded from Cat 4 (Funding Sources). They can appear in Cat 3 (Allocation Reduction) with a 🔒 protection badge — because they may still be in overweight nodes, but the note says to reduce via index vehicles, not direct position reduction.

**Cat 2 always visible**: The Strategic Exit Manager (add/remove UI) is always rendered in Cat 2, even when `strategic_exit_symbols` is empty. This makes the feature discoverable.

**Re-render on state change**: Strategic exit add/remove both trigger full pipeline re-render. Tax state saves also trigger re-render.

## Deferred (Phase 23.0D+)

- Loss harvest category (requires `cost_basis`, `market_value`, `holding_days` on overlay)
- Gain deferral logic (long-term vs. short-term treatment)
- Tax budget visualization (capacity/projected)

These fields exist in `holdings.csv` but are not currently surfaced to `SecurityIntelligenceOverlay`.

## Known Architecture Gap

The `_computePortfolioActions` function computes Cat 4 purely from ESS/overlay data. It does not have access to absolute dollar position sizes (only `percent_of_portfolio`). Liquidity ranking by dollar value would require `market_value` field on overlay.

## Server

URL: http://localhost:8765/ui/portfolio_alignment/  
Launch: `PYTHONPATH=. .venv/bin/python3 scripts/run_outcome_ui.py --port 8765`
