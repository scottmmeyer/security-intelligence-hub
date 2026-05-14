# Outcome Visualization Prototype UI (WP-05A)

## Purpose

This is a minimal local UI proof for the WP-04/WP-05A replay contracts.
It is intentionally lightweight and uses static HTML + JavaScript.

## Inputs

The UI reads these files directly from repository paths:

- data/current/replay_performance_series.csv
- data/current/replay_inputs.csv
- data/current/replay_availability.csv
- data/current/replay_matrix.csv
- data/current/analytical_universe.csv
- config/benchmark_category_registry.yaml
- config/investable_vehicle_registry.yaml

## Run Locally

Option 1: runner script

```bash
/Users/scottmmeyer/Projects/security-intelligence-hub/.venv/bin/python scripts/run_outcome_ui.py
```

Then open:

- http://127.0.0.1:8765/ui/outcome_visualization/index.html

Option 2: manual static server from repo root

```bash
cd /Users/scottmmeyer/Projects/security-intelligence-hub
/Users/scottmmeyer/Projects/security-intelligence-hub/.venv/bin/python -m http.server 8765
```

Then open the same URL above.

## Behavior

- Filters: geography, market cap, industry (ALL), timeframe (1Y), top N
- Lines: Benchmark, ETF/Fund, Full Universe, Top-N Strategy
- If replay_performance_series is empty for matching replay filters, the UI shows an explicit empty-state message and still shows replay/filter metadata.
- If all points are from a single timestamp, the UI switches to point-in-time mode.
- If multiple timestamps are available, the UI renders cumulative line mode.
- Status labels are emitted per series: pending, initialized, insufficient_history, unavailable.
- Replay availability panel always shows explicit per-category coverage status and dependencies.

## Current WP-05A Scope Limitation

WP-05A integrates benchmark and ETF/fund historical curves.
Full Universe and Top-N Strategy stock-derived curves remain unavailable until WP-05B.
