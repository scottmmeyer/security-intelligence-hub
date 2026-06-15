# Funding Dashboard Design

## Objective

Make policy-aware funding and reduction decisions visible in the Portfolio Alignment UI with minimal operator friction.

## Updated Surfaces

1. CRA source cards
2. CRA deployment target cards

## Source Card Additions

1. `Reduction Score`
2. `Reduction Reason`
3. `Policy Alignment` text

These appear under proceeds metadata so operators can compare source quality directly.

## Target Card Additions

1. primary funding source symbol/category/score
2. selection rationale
3. alternatives considered
4. policy alignment reason

## Visual Design Intent

1. Keep existing CRA card hierarchy intact.
2. Add explanatory metadata as compact secondary text.
3. Preserve readability and scan speed for ranked decisions.

## API/UI Contract Assumptions

Target payload fields:

1. `funding_source_symbol`
2. `funding_source_category`
3. `funding_source_score`
4. `funding_source_reason`
5. `funding_source_alternatives[]`
6. `funding_policy_alignment_reason`

Source payload fields:

1. `reduction_score`
2. `reduction_reason`
3. `policy_alignment_reason`

## Empty-State Behavior

If funding metadata is missing, cards render without the new blocks (no hard failure).

## Acceptance Signals

1. Operators can identify selected source and alternatives from card view.
2. Operators can see policy rationale without opening logs or source code.
3. Existing CRA rendering remains stable.
