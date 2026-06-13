# Lineage Confidence Model

## Purpose

Convert recommendation ancestry evidence into a deterministic confidence tier for operators.

## Confidence tiers

### HIGH

- direct symbol match
- direction match (`BUY`/`REDUCE`)
- recommendation age <= 7 days
- no competing symbol+direction recommendation in same 7-day window

Interpretation: highly likely causal recommendation.

### MEDIUM

- direct symbol + direction match within 30 days
- OR directional theme-level match within 30 days

Interpretation: plausible recommendation ancestry with moderate ambiguity.

### LOW

- weak timing symbol-level match (31-90 days)
- OR theme-level-only ancestry signal

Interpretation: weak but non-zero lineage signal.

### NONE

- no qualifying recommendation

Interpretation: currently unexplained portfolio change.

## Determinism guarantees

- fixed date windows (7/30/90)
- fixed direction normalization rules
- fixed tie-break order (confidence then recency)
- persisted CSV outputs for reproducibility

## Operational use

- supports operator question: "why did this trade likely occur?"
- explicitly surfaces uncertainty via confidence tier and unmatched list
- avoids performance/outcome judgment in this phase
