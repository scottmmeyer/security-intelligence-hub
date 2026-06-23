# Decision Readiness Gap Analysis

## What the Current Readiness Model Measures

The current Decision Readiness panel is driven from `/api/signal-status`, and that endpoint only merges holdings coverage plus the current ESS warning state into the UI.

Evidence:

- [scripts/run_outcome_ui.py](scripts/run_outcome_ui.py) populates `portfolio_holdings_coverage` from `summarize_holdings_coverage(...)` and attaches `holdings_status`, `holdings_applicable`, `holdings_covered_today`, `holdings_stale`, and `holdings_missing`.
- [ui/outcome_visualization/app.js](ui/outcome_visualization/app.js) calls `/api/signal-status` and renders `Readiness: ...` from that payload.

## Gap

That means the current readiness score is holdings-oriented, not candidate-oriented.

It can therefore report `HIGH` or `MEDIUM` while recommendation candidates remain stale, because candidate freshness is not part of the readiness calculation.

## Current Evidence

- The top deployment queue and UCF queue are fresh on the core ranking signals.
- The broader recommendation universe still contains stale ETF-oriented items.
- FMP is stale across the merged research universe.
- The panel still renders `Readiness: MEDIUM` because SIMO is the only current ESS warning.

## Conclusion

Decision Readiness currently reflects holdings readiness plus ESS posture, not full candidate readiness.
