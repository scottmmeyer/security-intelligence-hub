# Recommendation Reasoning Model

## Purpose

Explain why a recommendation exists using only deterministic, already-persisted recommendation inputs.

## Primary Reason

`primary_reason` is the first sentence of the recommendation's existing `rationale`.

This makes the explanation:
- deterministic
- directly derived from actual recommendation output
- free of post-hoc generative interpretation

## Supporting Reasons

`supporting_reasons` are assembled from:
- additional rationale sentences
- `evidence_summary`
- `reasoning_trace`
- severity
- drift magnitude when present

## Signal Drivers

Signal drivers are surfaced only when actual values exist in stored artifacts.

Currently supported sources:
- CW-DAS
- ESS
- Zacks
- Danelfin
- Yahoo, when persisted analyst consensus exists for the run

## Policy Drivers

Policy drivers include:
- rec-level `execution_state`
- `mandate_drift_label`
- `mandate_urgency`
- per-symbol policy state from `symbol_execution_states`

## Funding Drivers

Funding drivers are surfaced only when recommendation rationale already includes explicit funding-source lineage.

## Explainability Guarantee

The model explains decisions already made. It does not synthesize new justifications.
