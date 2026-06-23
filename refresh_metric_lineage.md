# Refresh Metric Lineage

This maps each visible Refresh Health metric to its true universe, API field, and source code path.

## Metric Lineage Table

| UI element | Current value | Universe measured | Source API field(s) | Source file(s) |
| --- | --- | --- | --- | --- |
| Zacks provider card rows | 484/502 rows (96.4%) | Provider cache rows with sourced_date equal to today inside latest_zacks.csv | zacks.with_data_count, zacks.attempted_count, zacks.coverage_pct from /api/signal-status | [scripts/run_outcome_ui.py](scripts/run_outcome_ui.py), [ui/outcome_visualization/app.js](ui/outcome_visualization/app.js) |
| Danelfin provider card rows | 56/56 rows (100.0%) | Provider cache rows with sourced_date equal to today inside latest_danelfin.csv | danelfin.with_data_count, danelfin.attempted_count, danelfin.coverage_pct | [scripts/run_outcome_ui.py](scripts/run_outcome_ui.py), [ui/outcome_visualization/app.js](ui/outcome_visualization/app.js) |
| Yahoo provider card rows | 56/56 rows (100.0%) | Provider cache rows with sourced_date equal to today inside latest_yahoo_supplemental.csv | yahoo.with_data_count, yahoo.attempted_count, yahoo.coverage_pct | [scripts/run_outcome_ui.py](scripts/run_outcome_ui.py), [ui/outcome_visualization/app.js](ui/outcome_visualization/app.js) |
| ESS card warning | fresh - partial, warning count 1 (SIMO) | ESS coverage status in current signal snapshot | ess.badge_state, ess.coverage_warning_count, ess.coverage_warning_examples | [scripts/run_outcome_ui.py](scripts/run_outcome_ui.py), [ui/outcome_visualization/app.js](ui/outcome_visualization/app.js) |
| Active progress line | [447/2518] Fetching Zacks data for MTN | Active provider task batch for current refresh stage (provider-specific pending list) | /api/signal-refresh/status.last_log_line | [src/scoring/fetch_zacks_scores.py](src/scoring/fetch_zacks_scores.py), [scripts/run_outcome_ui.py](scripts/run_outcome_ui.py), [ui/outcome_visualization/app.js](ui/outcome_visualization/app.js) |
| Active mode label in poll text | Rebuild Research Universe in progress | Active background job mode, not dropdown selection | /api/signal-refresh/status.mode | [scripts/run_outcome_ui.py](scripts/run_outcome_ui.py), [ui/outcome_visualization/app.js](ui/outcome_visualization/app.js) |
| Most Recent Refresh card | Refresh Portfolio Signals - Submitted 168 - Succeeded 168 | Last completed refresh report persisted on disk | /api/signal-refresh/status.last_report | [scripts/run_outcome_ui.py](scripts/run_outcome_ui.py), [ui/outcome_visualization/app.js](ui/outcome_visualization/app.js) |
| Holdings baseline summary | Baseline PAR-20260618-C4D023BA - Active holdings 69 | Latest PAR holdings baseline | portfolio_holdings_coverage.run_id, portfolio_holdings_coverage.active_holdings_baseline | [src/portfolio/holdings_coverage.py](src/portfolio/holdings_coverage.py), [scripts/run_outcome_ui.py](scripts/run_outcome_ui.py), [ui/outcome_visualization/app.js](ui/outcome_visualization/app.js) |
| Applicable holdings | 54 | Provider-applicable active holdings only | portfolio_holdings_coverage.providers.<provider>.applicable_holdings | [src/portfolio/holdings_coverage.py](src/portfolio/holdings_coverage.py), [ui/outcome_visualization/app.js](ui/outcome_visualization/app.js) |
| Covered today | 54 | Applicable holdings with sourced_date equal to today and primary data present | portfolio_holdings_coverage.providers.<provider>.covered_today | [src/portfolio/holdings_coverage.py](src/portfolio/holdings_coverage.py), [ui/outcome_visualization/app.js](ui/outcome_visualization/app.js) |
| Within threshold | 54 | Applicable holdings within threshold_days window | portfolio_holdings_coverage.providers.<provider>.covered_within_threshold | [src/portfolio/holdings_coverage.py](src/portfolio/holdings_coverage.py), [ui/outcome_visualization/app.js](ui/outcome_visualization/app.js) |
| Decision Readiness | MEDIUM | Holdings compliance states plus ESS state | Derived in browser from ess.badge_state and portfolio_holdings_coverage.providers.<provider>.status | [ui/outcome_visualization/app.js](ui/outcome_visualization/app.js) |

## Core Finding

The section mixes at least three universes at once:

1. Holdings universe (54 applicable / 69 active in baseline).
2. Provider today-row universe (for example 484/502 for Zacks).
3. Active refresh batch universe (for example 447/2518 during rebuild stage).

Because these appear side by side without explicit universe labels, operator interpretation is currently ambiguous.
