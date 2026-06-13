# Recommendation Lineage Design (PIS-003)

## Objective

Given an observed portfolio change in PIS, identify the most likely historical SIH recommendation that caused it and assign a deterministic confidence level.

## Scope

- Read-only lineage matching only.
- No recommendation generation changes.
- No SIH scoring/ranking changes.
- No portfolio mutation.

## Inputs

Observed changes are sourced from PIS-002 outputs:

- `data/history/pis/changes/change_records.csv`
- `data/history/pis/changes/change_summary.csv`

Candidate recommendation evidence is sourced from historical PAR artifacts:

- `recommendations.json`
- `deployment_plan.json`
- `ucf_verdicts.json`

under `data/portfolio_ingestion/analysis_runs/<run_id>/`.

## Processing Module

- `src/pis/recommendation_lineage.py`

Core entrypoint:

- `compute_recommendation_lineage(...)`

Read models:

- `pis_lineage_latest(...)`
- `pis_lineage_for_snapshot(...)`
- `pis_lineage_summary(...)`

## Persistence

Lineage artifacts are persisted to:

- `data/history/pis/lineage/lineage_records.csv`
- `data/history/pis/lineage/lineage_summary.csv`

## API Surface

Added endpoints:

- `/api/pis/lineage/latest`
- `/api/pis/lineage/{snapshot_id}`
- `/api/pis/lineage-summary`

Routes are implemented in `scripts/run_outcome_ui.py`.

## UI Surface

Added dashboard sections in `ui/pis_dashboard/`:

1. Latest Recommendation Matches
2. Unmatched Changes
3. Lineage Summary
4. Recommendation Source Breakdown

## Source Taxonomy

Matched recommendations are normalized into source buckets:

- `PAP`
- `CRA`
- `DEPLOYMENT_QUEUE`
- `REDUCTION_QUEUE`
- `DIL`
- `OTHER`

This supports operator explainability and future attribution workflows.
