# PRA-IMPL-02A Funding Depletion Design

## Problem

Prior PRA-IMPL-02 behavior selected funding sources per target using static ranking. Capacity was not consumed across targets, so multiple targets could pick the same top source even when proceeds should be exhausted.

## Design goals

- Deterministic source capacity depletion across deployment targets
- Preserve existing reduction scoring/ranking formulas
- Preserve conviction penalties
- Preserve self-funding exclusion
- Preserve deterministic ordering

## Implementation

Modified function:

- `src/portfolio/cra/funding_policy.py`
- `annotate_deployments_with_funding_plan(...)`

### New behavior

1. Build actionable sources sorted by existing deterministic key:
   - `-reduction_score`, `-estimated_proceeds`, `symbol`
2. Initialize mutable capacity ledger:
   - `remaining_capacity[symbol] = estimated_proceeds`
3. Process deployment targets in existing order (earlier targets first).
4. For each target:
   - exclude self-funding symbol
   - select only candidates with `remaining_capacity > 0`
   - consume capacity progressively by target `suggested_amount`
   - choose first contributing source as primary annotation
   - compute alternatives from still-eligible, still-funded candidates
5. If no funded candidate remains, keep target unchanged.

## Why this is safe

- No changes to CRA reduction score formula
- No changes to recommendation selection criteria
- No changes to governance/PIS/attribution logic
- No randomness introduced

## Determinism

Given identical `sources` and `deployments`, outputs remain stable because:

- source order is deterministic
- target order is deterministic
- capacity updates are pure sequential arithmetic
- tie-breaks remain symbol-based
