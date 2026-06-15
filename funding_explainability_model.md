# Funding Explainability Model

## Objective

Provide deterministic, machine-readable explanation of funding decisions attached to recommendations and deployment targets.

## Sources of Truth

1. Recommendation rationale text produced by PAP/CRA.
2. CRA deployment annotations (`funding_source_*` fields).
3. AI-003 extraction logic in allocation explainability engine.

## Extracted Funding Drivers

1. `funding_source`
2. `funding_alternatives`
3. `funding_policy_alignment`

## Parsing Contract

Expected rationale clauses:

1. `Funding source: ... (~X% available).`
2. `Alternatives considered: ... .`
3. `Policy alignment: ... .`

Extractor behavior is deterministic and tolerant to case variation.

## Output Example

A recommendation explanation funding block contains:

1. selected source type and symbols
2. available percentage
3. alternatives list
4. policy alignment text

## Consistency Guarantees

1. Funding explanations are derived from persisted recommendation rationale, not inferred from transient UI state.
2. Same inputs produce same extracted funding drivers.
3. Missing clauses degrade gracefully (partial drivers emitted, no crash).

## Operator Value

This model answers:

1. why this source was selected
2. what alternatives were considered
3. how policy alignment influenced the decision
