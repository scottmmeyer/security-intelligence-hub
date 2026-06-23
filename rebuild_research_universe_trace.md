# Rebuild Research Universe Trace

## Entry Path

- UI/API trigger: `POST /api/signal-refresh` in `scripts/run_outcome_ui.py`
- Rebuild mode dispatch: `refresh_mode == "rebuild_research_universe"`
- Worker script: `scripts/refresh_signals.py --mode rebuild_research_universe --smart --report-path ...`

## Universe Construction

For Zacks, Danelfin, and Yahoo, rebuild mode uses `_all_universe_symbols(_BASE_UNIVERSE)`.
`_BASE_UNIVERSE` points to `data/current/base_equity_universe.csv`.

Current base-universe row count: `2790` data rows (`2791` file lines including header).
Current analytical-universe unique symbol count: `2473`.

This means rebuild targets the base-equity universe, not the analytical-universe file directly.

## Provider Processing

- Zacks rebuild branch: `_refresh_zacks(... refresh_mode == REBUILD_RESEARCH_UNIVERSE)`
- Danelfin rebuild branch: `_refresh_danelfin(... refresh_mode == REBUILD_RESEARCH_UNIVERSE)`
- Yahoo rebuild branch: `_refresh_yahoo(... refresh_mode == REBUILD_RESEARCH_UNIVERSE)`
- FMP refresh path is separate and uses `_all_universe_symbols()` with its own freshness rules

## Submitted / Refreshed / Failed Semantics

`_compute_provider_metrics()` records:

- submitted
- skipped_already_covered
- retried_failed_checkpoint
- refreshed
- skipped
- failed

for Zacks, Danelfin, and Yahoo.

## Important Observation

FMP is reported differently in `ensure_signals_fresh_with_report()`:

- its report section is hardcoded to `submitted = 0`, `refreshed = 0`, `failed = 0`, `skipped = 0`
- but `_refresh_fmp()` can still fetch full-universe daily or quarterly datasets

So the machine-readable report understates FMP processing detail.

## Conclusion

Yes, rebuild mode is intended to process the full base-equity universe for Zacks, Danelfin, and Yahoo.
The low research-universe freshness score therefore reflects stale provider dates or denominator mismatch, not a candidate-only refresh design.
