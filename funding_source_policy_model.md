# Funding Source Policy Model

## Objective

Select funding sources for new deployment using a deterministic, policy-aware ranking that is explainable to operators.

## Candidate Classes

1. `EXCESS_CASH`
2. `TRIM_CANDIDATE`
3. `OVERWEIGHT_REDUCTION`

## Ranking Principles

1. Preserve liquidity optionality by using excess cash first when available above reserve floor.
2. Prefer exits/reductions in weaker-signal names over neutral/positive names.
3. Prefer reducing overweight drift where it repairs allocation alignment.
4. Keep tie-breakers deterministic and stable.

## Scoring Model

For each candidate source:

$$
\text{score} = \text{base(type)} + f(\text{available}) + f(\text{signal}) + f(\text{drift}) + f(\text{conviction penalty})
$$

Base priorities are type-dependent and bounded by additive adjustments.

## Deterministic Ordering

Ordered by:

1. descending policy score
2. priority band
3. category/source type
4. symbol lexicographic tie-break

## Output Contract

Primary source fields:

1. `funding_source_symbol`
2. `funding_source_category`
3. `funding_source_score`
4. `funding_source_reason`
5. `funding_policy_alignment_reason`

Alternatives:

- `funding_source_alternatives[]` (top non-selected candidates)

## Operator Explainability

Every selected source emits:

1. why selected
2. why alternatives were not selected
3. policy alignment statement

## Failure/Edge Behavior

1. If no eligible source exists, recommendation remains valid but funding summary marks external capital required.
2. If cash is present but below reserve floor, cash is not treated as primary excess-cash source.
