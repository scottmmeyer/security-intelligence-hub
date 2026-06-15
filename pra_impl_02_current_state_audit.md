# PRA-IMPL-02 Current State Audit

## Scope

Objective: implement policy-aware funding source selection and allocation reduction ranking as additive behavior in CRA/PAP/explainability/UI layers.

Constraint honored: no PIS foundation components were modified.

## Baseline State Before PRA-IMPL-02

1. CRA capital sources were category/priority tagged but not policy-scored.
2. Deployment targets did not carry explicit funding-source primary/alternative recommendations.
3. PAP funding selection was heuristic and summary-level, with limited deterministic rationale output.
4. AI-003 funding explainability depended on free-text rationale and only extracted basic funding-source metadata.
5. Portfolio Alignment UI did not surface reduction score, policy-alignment rationale, or funding alternative comparisons.

## Implemented Changes

## CRA Source Scoring

- Added deterministic source scoring and rationale in `src/portfolio/cra/funding_policy.py` via:
  - `score_reduction_candidates(...)`
  - `annotate_deployments_with_funding_plan(...)`
- Integrated scoring into source build pipeline:
  - `src/portfolio/cra/capital_source_builder.py`
- Integrated deployment funding annotations into proposal builder:
  - `src/portfolio/cra/rotation_proposal_builder.py`

## Data Contract Extensions

- Extended CRA source and deployment payload models with additive fields:
  - reduction reason/score
  - policy alignment reason
  - deployment funding primary source
  - deployment funding alternatives
- Files:
  - `src/portfolio/models.py`
  - `src/portfolio/cra/models.py`

## PAP Funding Selection

- Upgraded `identify_funding_sources(...)` in `src/portfolio/recommendations.py` to:
  - score and rank sources deterministically
  - preserve cash-first behavior when excess cash exists
  - emit explicit primary source, alternatives, and policy-alignment summary text

## Explainability

- Extended AI-003 parser in `src/sih/allocation_explainability.py` to extract:
  - `funding_source`
  - `funding_alternatives`
  - `funding_policy_alignment`

## UI Visibility

- Updated `ui/portfolio_alignment/app.js` to render:
  - source-level reduction score/reason/policy alignment
  - target-level funding source, reason, alternatives, and policy alignment

## Where Philosophy Influence Ends

1. Philosophy/policy influence is limited to additive recommendation metadata and deterministic ranking weights.
2. Core PIS ingestion, canonical selection, change detection, lineage, and benchmark attribution engines are unchanged.
3. Allocation execution remains operator-governed; no autonomous trade execution was introduced.

## Determinism Summary

Deterministic ordering is enforced by explicit sort keys (score, priority band, category, symbol). Tie-breaking is stable and reproducible.

## Audit Conclusion

PRA-IMPL-02 current state is additive, deterministic, and operator-visible. Integration points are complete across CRA, PAP, explainability, and UI surfaces without violating PIS foundation boundaries.
