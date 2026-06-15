# Portfolio Manager to PIS Mapping

## Mapping Basis
Source artifacts:
- data/portfolio_ingestion/analysis_runs/<PAR>/snapshot.json
- data/portfolio_ingestion/analysis_runs/<PAR>/holdings.csv

Target schema:
- src/pis/storage.py SNAPSHOT_HEADERS
- src/pis/storage.py POSITION_HEADERS
- src/pis/storage.py INDEX_HEADERS

## Core Mapping
Snapshot:
- PM portfolio_snapshot_id -> PIS snapshot_id
- PM snapshot_date -> PIS snapshot_date
- PM account_name -> PIS account_name
- PM source_file -> PIS source_file
- PM run_id -> PIS source_run_id
- PM source_format -> PIS source_format
- PM total_market_value -> PIS portfolio_value
- PM holding_count -> PIS holding_count
- PM ingestion_status -> PIS ingestion_status
- PM created_at_utc -> PIS created_at_utc
- PM normalization_warnings -> PIS warnings

Position:
- PM portfolio_snapshot_id -> PIS snapshot_id
- PM snapshot_date -> PIS snapshot_date
- PM account_name -> PIS account_name
- PM symbol, description, quantity, market_value -> same semantic PIS fields
- PM percent_of_portfolio -> PIS percent_of_account
- PM percent_of_portfolio -> PIS source_percent_of_account
- PM cost_basis -> PIS cost_basis_total
- PM security_type -> PIS security_type
- PM operational_state -> PIS operational_state
- PM is_cash_equivalent -> PIS is_cash_equivalent
- PM source_file -> PIS source_file
- PM created_at_utc -> PIS created_at_utc

## Can PM map to PIS without loss?
For PIS Phase 1 required fields: Yes.
For all PM enriched analytics fields: No (subset is intentionally not persisted in current PIS position schema).

## Fields in PM but not currently persisted in PIS POSITION_HEADERS
- asset_class
- geography
- market_cap_bucket
- mega_subtier
- sector
- industry
- benchmark_id
- investable_vehicle_id
- composite_score
- ess_score_text
- zacks_rating
- danelfin_score
- strategic_role
- exposure_geography_mix
- exposure_market_cap_mix
- exposure_mega_subtier_mix
- exposure_sector_mix
- exposure_style_mix
- exposure_thematic_mix
- decomposition_method
- decomposition_version
- decomposition_timestamp
- decomposition_confidence
- decomposition_source
- decomposition_confidence_tier
- safe_to_offset_cash
- portfolio_snapshot_id (name differs; mapped into snapshot_id)
- percent_of_portfolio (name differs; mapped into percent_of_account/source_percent_of_account)

## Fields in PIS POSITION_HEADERS not present by name in PM holdings.csv
- account_id (PIS synthetic value)
- snapshot_id (mapped from PM portfolio_snapshot_id)
- percent_of_account (mapped from PM percent_of_portfolio)
- source_percent_of_account (mapped from PM percent_of_portfolio)
- cost_basis_total (mapped from PM cost_basis)

## Gains/Loss Mapping Note
Raw Fidelity files contain gain/loss fields, but canonical PM holdings.csv does not retain those gain/loss columns. A no-loss migration of raw gain/loss requires extending PIS schema or preserving a raw-attribute sidecar.
