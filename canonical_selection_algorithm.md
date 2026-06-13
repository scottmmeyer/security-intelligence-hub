# Canonical Selection Algorithm

## Inputs
- Snapshot index rows from data/history/pis/pis_snapshot_index.csv
- Governance evaluation rules from src/pis/governance.py

## Candidate Classification
For each snapshot row:
1. Evaluate governance status: PASS, WARNING, or REJECT.
2. Group rows by snapshot_date.

## Eligibility Gate
Per date:
1. Eligible set A: all PASS candidates.
2. If A is empty, eligible set B: all WARNING candidates.
3. If A and B are empty, no eligible candidate for that date.

REJECT candidates are excluded from selection.

## Ranking
For eligible candidates, compute deterministic sort key:
1. created_at_utc (latest first)
2. governance rank (PASS > WARNING > REJECT)
3. snapshot_id lexical tie-break

Selected canonical candidate = max(rank key).

## Selection Policy Values
- PASS_THEN_LATEST_INGESTION
- WARNING_FALLBACK_THEN_LATEST_INGESTION
- NO_ELIGIBLE_CANDIDATE

## Selection Reason Values
Examples:
- Selected latest-ingested PASS candidate.
- No PASS candidate available; selected latest WARNING candidate.
- All candidates for this date were REJECT.

## Output File
data/history/pis/canonical/canonical_daily_snapshots.csv

One row per date with deterministic selection fields and canonical portfolio metrics.

## Downstream Usage
- Timeline reads canonical rows only.
- Change detection compares canonical rows only.
- Lineage uses canonical-derived change artifacts only.
