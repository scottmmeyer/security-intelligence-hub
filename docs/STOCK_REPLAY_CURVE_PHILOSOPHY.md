# Stock Replay Curve Philosophy (WP-05D)

## Purpose

The Stock Replay Curve Foundation extends the replay engine with two stock-derived
performance series:

- **FULL_UNIVERSE** — An equal-weight composite of all symbols in the filtered
  analytical universe during the replay window.
- **TOP_N_STRATEGY** — An equal-weight composite of the top-N symbols selected
  at snapshot time, with the basket frozen for the full replay window.

These curves allow direct quantitative comparison between the systematic selection
strategy and its benchmark/investable-vehicle alternatives.

---

## Design Principles

### 1. No-Lookahead Guarantee

Symbol selection for TOP_N_STRATEGY is always derived from data available at
`snapshot_date`. The selected symbol basket is frozen in `ReplaySelection.selected_symbols`
before any price data is fetched. Market returns during the replay window play
no role in selection.

### 2. Equal-Weight Composites

All stock curves use equal-weight averaging across available symbols. At each
date the composite return is:

```
composite_return(t) = mean(cumulative_return_i(t) for all i with data at t)
```

Symbols without a price on a given date are excluded from that date's average
rather than zeroed out.

### 3. Coverage Tracking

Every stock curve carries a `coverage_status` field drawn from a fixed vocabulary:

| Status | Meaning |
|---|---|
| `AVAILABLE` | Coverage fraction ≥ threshold; curves are reliable |
| `PARTIAL` | Coverage fraction below threshold but non-zero |
| `MISSING_MARKET_DATA` | Too many symbols have no price data |
| `INSUFFICIENT_HISTORY` | Symbols exist but have fewer than `MINIMUM_CURVE_POINTS` data points |
| `FAILED` | No symbols or fatal provider error |

Coverage thresholds:
- `FULL_UNIVERSE_COVERAGE_THRESHOLD = 0.60` — 60% of requested symbols must have data
- `TOP_N_COVERAGE_THRESHOLD = 0.80` — 80% of top-N basket must have data

### 4. Symbol Safety Limits

`MAX_SYMBOLS_PER_CATEGORY = 500` caps the number of symbols fetched in a single
full-universe request. If the universe exceeds this cap, symbols are truncated
after sorting by composite_score descending. The `symbols_truncated` flag on
`StockCurveResult` is set to `True`.

### 5. Batch Provider Pattern

`YahooHistoricalPriceProvider.get_batch_prices()` issues a single multi-ticker
`yfinance.download()` call rather than N sequential single-ticker requests.
The per-symbol `get_symbol_series()` path is available as a fallback when the
batch API is unavailable or returns empty results.

### 6. Evidence Summary

At the end of each replay run, `replay_evidence_summary.json` is written to the
replay partition directory. This artifact records:
- Final cumulative returns for all four series (BENCHMARK, INVESTABLE_VEHICLE,
  FULL_UNIVERSE, TOP_N_STRATEGY)
- Delta of top-N strategy vs benchmark and vs investable vehicle
- Coverage status and missing/partial symbol lists
- Selected symbol basket

See [REPLAY_EVIDENCE_SUMMARY_CONTRACT.md](./REPLAY_EVIDENCE_SUMMARY_CONTRACT.md).

---

## Backward Compatibility

All new parameters on `build_performance_series()` have `None` defaults.
If `full_universe_curve_result` and `top_n_curve_result` are both `None`,
the function falls back to the pre-WP-05D provider-based path and no
FULL_UNIVERSE or TOP_N_STRATEGY rows are written.

`PerformanceSeries.coverage_status` defaults to `"AVAILABLE"` so existing
rows produced before WP-05D remain valid.
