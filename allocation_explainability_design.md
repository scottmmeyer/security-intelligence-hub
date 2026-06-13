# Allocation Explainability Design

## Objective

Add a deterministic explainability layer that explains existing recommendations without changing recommendation generation.

## Implementation

New engine:
- `src/sih/allocation_explainability.py`

Persistence:
- `data/history/explanations/recommendation_explanations.csv`
- `data/history/explanations/explanation_summary.csv`

APIs:
- `/api/explanations/latest`
- `/api/explanations/{recommendation_id}`
- `/api/explanations/summary`

UI:
- additive explainability block on recommendation cards in `ui/portfolio_alignment/`

## Inputs

Explainability is derived from persisted recommendation artifacts and adjacent run outputs:
- `recommendations.json`
- `run_metadata.json`
- `analyst_consensus.json` when available
- recommendation drilldown holdings embedded in `recommendations.json`
- policy annotations embedded on recommendation dicts

## Deterministic Output Model

Per recommendation:
- `recommendation_id`
- `symbol`
- `recommendation_type`
- `primary_reason`
- `supporting_reasons`
- `signal_drivers`
- `policy_drivers`
- `funding_drivers`
- `philosophy_drivers`
- `explanation_version`

## Design Notes

- Primary reason comes from the first sentence of the existing recommendation rationale.
- Supporting reasons come from remaining rationale sentences, evidence summary, reasoning trace, severity, and drift.
- Signal drivers are exposed only from values already present in artifacts.
- Policy drivers are exposed only from stored execution-state and mandate metadata.
- Funding drivers are extracted only when the recommendation rationale already embeds funding-source lineage.
- Philosophy ranking is deterministic and recommendation-type-based.

## Historical Backfill

`refresh_allocation_explanations()` scans all analysis runs and builds explanations for existing recommendation history without regenerating recommendations.

## Non-goals

This layer does not modify:
- recommendation generation
- CW-DAS scoring
- PAP logic
- CRA logic
- DIL logic
- funding algorithms
