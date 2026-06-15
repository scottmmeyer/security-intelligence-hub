# Historical Coverage Analysis

## Coverage Metrics
- analysis runs inspected: 235
- unique snapshot identities: 68
- valid-date snapshot identities: 67
- invalid-date snapshot identities: 1
- unique valid snapshot dates: 17
- date span: 2026-05-21 to 2026-06-11

## Duplication Profile
Observed many repeated reruns against the same underlying portfolio snapshot identity.

Evidence:
- multiple PAR run_ids share the same portfolio_snapshot_id
- top source file repetition: Portfolio_Positions_May-29-2026.csv and variants

Implication:
- migration should deduplicate on snapshot identity
- expected migrated snapshot count is much lower than run count

## Attribute Coverage by Question
- account value: available (total_market_value)
- holdings: available (holdings.csv)
- cash: available as cash-equivalent holdings and adjusted_cash fields in snapshot metadata
- cost basis: available (cost_basis in holdings.csv)
- gains/losses: available in raw Fidelity uploads; not retained in canonical PM holdings.csv
- allocation: available in canonical holdings classifications and alignment artifacts
- other fields: provider signals, decomposition metadata, operational state, run lineage

## Immediate PIS Feature Enablement if PM historical snapshots are present
- value timeline: yes
- change detection: partial foundation only; detector workflow not implemented in current PIS module
- benchmark comparison: not in current PIS storage/service API
- decision lineage: partial; run-level lineage available, full recommendation-trade-outcome linkage not implemented in PIS module

## Post-Migration Snapshot Count Estimate
- practical immediate count (valid-date identities): 67
- potential count if malformed snapshot_date is repaired for the one invalid identity: 68
