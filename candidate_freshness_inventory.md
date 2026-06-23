# Candidate Freshness Inventory

This inventory identifies freshness data already present and what can be surfaced without recalculation.

## Existing Candidate and Universe Sources

| Domain | Existing symbol source | Existing freshness fields | Existing API exposure | Gap |
| --- | --- | --- | --- | --- |
| Research universe | data/current/analytical_universe.csv | Symbol roster (no direct provider sourced_date columns in this file) | Aggregate health via /api/signal-status | Needs per-symbol provider join |
| CW-DAS queue | PAR deployment_queue.json | Symbols and scores only | Via PAR artifacts, and queue-related UI/API surfaces | No per-symbol provider freshness fields |
| UCF rankings | PAR ucf_verdicts.json | Symbols and source signal summaries (no provider dates) | Via PAR artifacts | No provider date/state fields |
| CRA deployments | /api/cra/proposal deployments | Symbols and deployment metadata | Direct API available | No provider freshness fields |
| Recommendations | PAR recommendations.json affected_symbols | Candidate symbols by recommendation | Via PAR artifacts | No provider date/state fields |

## Existing Provider Freshness Data (Already Available)

| Provider | File | Per-symbol date field | Per-symbol quality fields |
| --- | --- | --- | --- |
| Zacks | data/signals/zacks/latest_zacks.csv | sourced_date | zacks_rank, zacks_score |
| Danelfin | data/signals/danelfin/latest_danelfin.csv | sourced_date | danelfin_raw, danelfin_score |
| Yahoo | data/signals/yahoo/latest_yahoo_supplemental.csv | sourced_date | price_target, analyst_count, current_price |
| ESS | data/current/signal_snapshot.csv | snapshot_date | signal_coverage_status, starmine_ess_text |
| FMP | data/signals/fmp/latest/latest_fmp_enriched_universe.csv | fmp_sourced_date | fmp_coverage_status and FMP factor columns |

## What Can Be Surfaced Immediately

Without changing algorithms, candidate freshness can be computed by joining candidate symbol lists to the provider latest files above.

No scoring recomputation is required.
