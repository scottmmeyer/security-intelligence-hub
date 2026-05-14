# Replay Evidence Summary Contract (WP-05D)

## File Location

```
data/history/replays/snapshot_date=<date>/replay_id=<id>/replay_evidence_summary.json
```

Also referenced via `replay_evidence_summary_path` in `replay_matrix.csv`.

---

## Schema

All fields are present. Fields with no data available carry `null`.

| Field | Type | Description |
|---|---|---|
| `replay_id` | string | Unique replay identifier |
| `replay_mode` | string | `HISTORICAL_VALIDATION`, `FORWARD_SIMULATION`, or `CURRENT_RECOMMENDATION` |
| `start_date` | string | ISO date — replay window start |
| `end_date` | string | ISO date — replay window end |
| `geography` | string | Filter geography (e.g. `US`) |
| `market_cap_bucket` | string | Filter market-cap bucket (e.g. `LARGE`) |
| `industry` | string | Filter industry (e.g. `ALL`) |
| `benchmark_symbol` | string | Benchmark ticker or index identifier |
| `investable_vehicle_symbol` | string | ETF/fund ticker |
| `full_universe_symbol_count` | int | Number of symbols in the filtered universe |
| `top_n` | int | N used for top-N selection |
| `selected_symbols` | string[] | Symbols in the frozen top-N basket |
| `missing_price_symbols` | string[] | Symbols for which no price data was available |
| `partial_price_symbols` | string[] | Symbols with fewer data points than the minimum |
| `benchmark_final_return` | float \| null | Terminal cumulative return for BENCHMARK series |
| `investable_vehicle_final_return` | float \| null | Terminal cumulative return for INVESTABLE_VEHICLE series |
| `full_universe_final_return` | float \| null | Terminal cumulative return for FULL_UNIVERSE series |
| `top_n_strategy_final_return` | float \| null | Terminal cumulative return for TOP_N_STRATEGY series |
| `strategy_vs_benchmark_delta` | float \| null | `top_n_strategy_final_return − benchmark_final_return` |
| `strategy_vs_vehicle_delta` | float \| null | `top_n_strategy_final_return − investable_vehicle_final_return` |
| `full_universe_coverage_status` | string | Coverage status for FULL_UNIVERSE curve |
| `top_n_coverage_status` | string | Coverage status for TOP_N_STRATEGY curve |
| `coverage_status` | string | Aggregate coverage status: `AVAILABLE`, `PARTIAL`, or `FAILED` |
| `generated_at_utc` | string | ISO-8601 UTC timestamp of generation |

---

## Coverage Status Vocabulary

| Value | Meaning |
|---|---|
| `AVAILABLE` | Sufficient data; curve is reliable |
| `PARTIAL` | Data present but below coverage threshold |
| `MISSING_MARKET_DATA` | Too many symbols returned no data from provider |
| `INSUFFICIENT_HISTORY` | Symbols have fewer than `MINIMUM_CURVE_POINTS` data points |
| `FAILED` | No data or fatal error |

---

## Aggregate Coverage Logic

The top-level `coverage_status` field is computed from `full_universe_coverage_status`
and `top_n_coverage_status`:

- If either is `FAILED` or `MISSING_MARKET_DATA` → `FAILED`
- Else if either is `PARTIAL` or `INSUFFICIENT_HISTORY` → `PARTIAL`
- Else → `AVAILABLE`

---

## UI Usage

The UI loads `replay_evidence_summary.json` via the path in `replay_matrix.csv`
(`replay_evidence_summary_path` column). It renders:

- **Stock Coverage panel** — coverage_status, selected_symbols, missing/partial lists
- **Return Comparison table** — final returns for all four series with strategy deltas

If the file cannot be fetched, the UI shows a graceful fallback message.

---

## Backward Compatibility

Replays generated before WP-05D do not have a `replay_evidence_summary.json`.
The UI handles this with a `catch(() => null)` fetch and renders a fallback message.
The `replay_evidence_summary_path` column in `replay_matrix.csv` will be empty for
pre-WP-05D rows.
