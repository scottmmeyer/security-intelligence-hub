# Portfolio Manager History Inventory

## Sources Inspected
- incoming/portfolio/
- data/portfolio_ingestion/archive/
- data/portfolio_ingestion/analysis_runs/*

## Forensic Counts
- incoming/portfolio CSV files: 2
- archived CSV files: 234
- archived Portfolio_Positions CSV files: 217
- analysis runs with snapshot.json: 235

## Date Coverage
From canonical run snapshots (snapshot.json):
- valid snapshot_date min: 2026-05-21
- valid snapshot_date max: 2026-06-11
- unique valid snapshot dates: 17
- malformed snapshot_date values: 2 runs with value CONCENTRATED_ALPHA

## Unique Snapshot Availability
From analysis_runs/snapshot.json:
- unique portfolio_snapshot_id total: 68
- unique portfolio_snapshot_id with valid date: 67
- unique portfolio_snapshot_id with invalid date: 1 (PSNAP-CONCENTRATED_ALPHA-661E79F41FDD)

## Historical Fidelity File Evidence
Raw header (sample from incoming/portfolio/Portfolio_Positions_May-29-2026.csv):
- Account Number
- Account Name
- Symbol
- Description
- Quantity
- Last Price
- Last Price Change
- Current Value
- Today's Gain/Loss Dollar
- Today's Gain/Loss Percent
- Total Gain/Loss Dollar
- Total Gain/Loss Percent
- Percent Of Account
- Cost Basis Total
- Average Cost Basis
- Type

## Snapshot Attributes Available in Portfolio Manager Artifacts
Snapshot-level (snapshot.json):
- portfolio_snapshot_id
- snapshot_date
- account_name
- total_market_value
- holding_count
- source_file
- source_format
- ingestion_status
- normalization_warnings
- created_at_utc
- run_id
- adjusted_cash_mv
- adjusted_deployable_mv
- adjusted_deployable_pct
- settlement_adjustment

Holding-level (holdings.csv):
- symbol, description, quantity, market_value, percent_of_portfolio
- cost_basis
- classification: asset_class, geography, market_cap_bucket, mega_subtier, sector, industry
- provider fields: composite_score, ess_score_text, zacks_rating, danelfin_score
- decomposition fields: exposure_* mixes, decomposition_* fields, strategic_role
- operational fields: operational_state, is_cash_equivalent, safe_to_offset_cash

## Direct Answers
1. Historical Fidelity portfolio files exist in both incoming/portfolio and data/portfolio_ingestion/archive.
2. Canonical PM snapshot history covers 2026-05-21 through 2026-06-11 (valid dates).
3. Unique PM portfolio snapshots available: 68 total identities, 67 immediately valid for migration.
4-10. PM historical artifacts include account value, holdings, cash-equivalent indicators, cost basis, gain/loss in raw Fidelity files, and allocation/classification metadata in canonical holdings.
