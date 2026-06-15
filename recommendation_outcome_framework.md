# Recommendation Outcome Framework

## Framework Layers

1. Canonical portfolio history
2. Change detection between canonical dates
3. Recommendation lineage matching
4. Outcome attribution and aggregation

## Why This Framework

- Preserves existing governance and canonical selection rules.
- Avoids introducing new data dependencies.
- Produces actionable operator views by recommendation and source.

## Entity Definitions

- Attribution Record: one matched recommendation-change pair.
- Snapshot Attribution Summary: aggregate outcome metrics for one snapshot date.
- Recommendation Ranking: aggregate directional attribution by recommendation ID.
- Source Performance: aggregate outcomes by recommendation source.

## Read-model Artifacts

- `attribution_records.csv`: record-level deterministic evidence.
- `attribution_summary.csv`: snapshot-level deterministic summary.

## API Read-model Surfaces

- `latest`: current snapshot attribution details and rankings.
- `history`: snapshot-by-snapshot attribution summary rows.
- `summary`: aggregate totals and source-level performance across history.

## Operator Use

- Identify strongest and weakest recommendation outcomes quickly.
- Compare source reliability via win rates and directional contribution.
- Preserve auditability from summary back to record-level evidence.
