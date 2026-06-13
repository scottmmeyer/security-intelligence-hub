# PIS-004B Canonical Daily Snapshot Selection Design

## Scope
Stage B introduces a derived canonical daily portfolio state layer.

Included:
- Deterministic canonical daily selector
- Governance-gated candidate eligibility
- Canonical persistence output
- Canonical APIs and dashboard section
- Timeline conversion to canonical daily values
- Change detection recompute from canonical daily series
- Lineage recompute from canonical-based change outputs

Excluded:
- Any mutation/deletion of immutable snapshot history
- Any modification of snapshot inventory semantics

## New Module
Implemented: src/pis/canonical_daily.py

Primary responsibilities:
- Evaluate governance status for each snapshot candidate per date
- Apply eligibility gate: PASS preferred, WARNING fallback, REJECT excluded
- Rank eligible candidates deterministically
- Persist one canonical row per date

## Selection Contract
Per-date canonical output row:
- snapshot_date
- canonical_snapshot_id
- selection_policy
- selection_reason
- governance_status
- source_file
- portfolio_value
- cash
- position_count

## Deterministic Ranking
Within eligible candidates:
1. Latest ingestion timestamp (max created_at_utc)
2. Highest governance rank (PASS > WARNING > REJECT)
3. Snapshot ID lexical order as deterministic tie-break

No random behavior is used.

## Persistence
Output path:
- data/history/pis/canonical/canonical_daily_snapshots.csv

Properties:
- Derived analytical layer only
- Rebuilt from immutable index + governance rules
- Does not alter historical snapshot partitions or index rows

## API Additions
Added endpoints:
- /api/pis/canonical/latest
- /api/pis/canonical/history
- /api/pis/canonical-summary

## Dashboard Additions
Added section:
- Section 7: Canonical Daily Portfolio State

Displays:
- Date
- Selected Snapshot
- Governance Status
- Portfolio Value
- Selection Reason

## Conversions
Timeline conversion:
- src/pis/storage.py now renders timeline from canonical daily rows.

Change conversion:
- src/pis/change_detection.py now computes from canonical-selected snapshots only.

Lineage conversion:
- src/pis/recommendation_lineage.py consumes canonical-derived change outputs.
