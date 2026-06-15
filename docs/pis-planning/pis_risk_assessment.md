# PIS Risk Assessment
**Date:** 2026-06-12

## Architectural Risks

### 1) Boundary drift
If PIS starts writing back into SIH recommendation artifacts, the separation of concerns breaks.

Mitigation:
- enforce read-only access to SIH intelligence outputs
- keep PIS writes confined to PIS-owned artifacts

### 2) Model duplication
If PIS recreates SIH history or benchmark storage, the repository will develop duplicate sources of truth.

Mitigation:
- SIH owns benchmark history and recommendation history
- PIS only consumes them

### 3) Over-designed lineage
If lineage matching is made too strict too early, the unresolved queue will become noisy.

Mitigation:
- start with confidence scoring and human reconciliation
- keep matching explainable

## Scaling Risks

### 1) Snapshot volume
Snapshot history will grow with every portfolio file.

Mitigation:
- append-only partitions
- snapshot-date partitioning
- account-based subpartitioning where needed

### 2) Event volume
Change events can multiply quickly when many symbols move at once.

Mitigation:
- keep event records compact
- store only meaningful deltas

### 3) Benchmark history reuse
Benchmark data should remain centralized to avoid duplicate fetches.

Mitigation:
- consume SIH-owned benchmark history

## Governance Risks

### 1) Decision feedback leakage
PIS must not influence SIH recommendation generation.

Mitigation:
- hard boundary: PIS is analysis only

### 2) Misclassification of unexplained changes
User reconciliation prompts may initially be incomplete.

Mitigation:
- provide explicit unresolved states
- allow user overrides

## Future Migration Risks

### Could PIS later become a separate service?

Yes, but only if the repository structure is kept clean now.

What makes extraction feasible later:
- PIS namespace isolation under `src/pis/`
- PIS-specific storage under `data/history/pis/`
- PIS-specific tests and docs boundaries
- read-only dependency on SIH intelligence outputs
- shared contracts kept narrow and explicit

What would make extraction hard:
- sharing mutable internal state with SIH
- mixing PIS artifacts into SIH scoring paths
- duplicate benchmark storage
- entangled UI routes and side effects

## Verdict on Future Separation

PIS can later become a standalone service without major redesign if the current planning is followed.
The key is to keep the boundary strict from day one.
