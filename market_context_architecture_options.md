# Market Context Architecture Options

Project: Security Intelligence Hub (SIH)  
Assessment: MCI Architecture Options  
Date: 2026-06-06

## Q3) What Is Realistically Detectable in a Deterministic System?

### Deterministic and Defensible
- broad regime classification from explicit thresholds
- volatility/rate/credit shock flags
- sector-wide stress versus idiosyncratic divergence likelihood scores
- scheduled-event windows

### Not Deterministically Defensible (without advanced causal inference)
- single-cause attribution for individual security moves
- event narrative certainty labels
- counterfactual statements such as "stock would have risen absent X"

## Q4) Interaction with Existing SIH Components

### CW-DAS
- Recommended v1 interaction: none (read-only contextual overlay)
- Rationale: avoid double counting and preserve tested scoring behavior.

### Dislocation Framework
- Recommended v1 interaction: context panel adjacent to dislocation panel; no tier mutation.
- Rationale: dislocation is security-level evidence; MCI is market-state context.

### STI
- Recommended v1 interaction: optional informational confidence ribbon only.
- Rationale: STI recommendations remain governed by existing deterministic evidence.

### PAP
- Recommended v1 interaction: add run-level market-state metadata for operator interpretation.

### CRA
- Recommended v1 interaction: no automatic source/target changes; show context advisory only.

### PMI
- Recommended v1 interaction: conceptually aligned as interpretation layer; MCI can be modeled similarly to PMI governance (interpretation without mutating underlying calculations).

## Architecture Options

### Option 1: Run-Level Context Service (Preferred)
- Build MCI snapshot once per run date.
- Persist to mci_snapshot artifact with evidence vector.
- UI consumes snapshot in multiple panels.
- Pros: deterministic, auditable, reusable, low coupling.
- Cons: requires new artifact lifecycle and schema governance.

### Option 2: Inline On-Demand Computation
- Compute context at UI/API request time.
- Pros: lower storage footprint.
- Cons: reproducibility risk and hidden drift if market data revises.

### Option 3: Hybrid Snapshot + Event Overlay
- Deterministic snapshot + optional curated event tags.
- Pros: balances rigor and operator usability.
- Cons: event tags require strong governance to avoid narrative drift.

## Recommended Technical Shape (No Implementation)

1. New immutable model: MarketContextSnapshot
- as_of_date
- regime_label
- stress_flags (vol/rates/credit/breadth)
- event_window_flags
- confidence_score (for context reliability, not alpha prediction)
- evidence map and source metadata

2. Storage
- Derived artifact per run date under deterministic naming.

3. API exposure
- run-level context block only; no score mutation fields.

4. UI
- single MCI strip and expandable evidence drawer.

5. Auditability
- each label must map to explicit threshold calculations.
