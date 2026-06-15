# Allocation Reduction Model

## Objective

Rank reduction candidates (sell-side sources) to fund deployments while respecting allocation drift repair and signal quality.

## Inputs

1. CRA source candidates from source builder.
2. Deployment queue context (high-conviction symbols/nodes).
3. Source attributes: category, priority, estimated proceeds, ESS/signal direction, overweight drift, tax/policy flags.

## Category Weighting

Higher preference:

1. signal deterioration / bearish names
2. overweight reductions with significant drift
3. low-conviction reductions

Blocked policy sources are excluded from deployable pool.

## Score Composition

$$
\text{reduction score} = w_c + w_p + w_{proceeds} + w_{signal} + w_{drift} - w_{conflict}
$$

Where:

1. $w_c$: category intent weight
2. $w_p$: priority band weight
3. $w_{proceeds}$: available proceeds utility
4. $w_{signal}$: bearish deterioration preference
5. $w_{drift}$: overweight repair preference
6. $w_{conflict}$: penalty if source conflicts with high-conviction deployment queue

## Deterministic Tie-Breaking

1. descending reduction score
2. descending estimated proceeds
3. symbol ascending

## Output Fields

Per source:

1. `reduction_score`
2. `reduction_reason`
3. `policy_alignment_reason`

These fields are surfaced in CRA API and UI for operator review.

## Governance Notes

Model is additive and advisory. It does not execute trades and does not alter PIS foundation pipelines.
