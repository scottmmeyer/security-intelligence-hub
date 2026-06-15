# PIS Architecture Overview
**Project:** PIS-001 — Portfolio Change Detection, Decision Lineage, and Reconciliation Framework
**Date:** 2026-06-12

## Purpose

PIS is the portfolio intelligence layer that explains what changed in the portfolio, why it changed, and what information is still missing.

SIH remains the decision engine:
- ESS
- Zacks
- Danelfin
- FMP
- CW-DAS
- DIL
- PAP
- CRA
- Recommendations

PIS is the outcome engine:
- portfolio snapshots
- change detection
- decision lineage
- benchmark comparison
- attribution
- reconciliation prompts

## Core Design Constraint

PIS must never alter SIH scores or recommendation logic.

It is read-only with respect to SIH intelligence outputs.

## Phase 1 Scope

Phase 1 uses Fidelity portfolio download files only.

No transaction imports.
No tax lots.
No dividend imports.
No manual accounting.

## Primary Questions

PIS Phase 1 answers:
- What changed?
- Why did it change?
- What information is missing?

## Architecture Summary

1. Fidelity portfolio files are ingested into immutable portfolio snapshots.
2. Each new snapshot is compared with the prior snapshot to generate structured change events.
3. Change events are matched against SIH recommendation history to establish decision lineage.
4. Unmatched changes are routed to a missing-information queue.
5. Benchmark history is consumed from SIH, not owned by PIS.
6. Attribution is added later, after snapshot history and lineage are stable.

## System Boundaries

### Owned by PIS
- portfolio snapshot history
- position snapshot history
- change detection
- event classification
- decision lineage matching
- reconciliation queue for unknown changes

### Owned by SIH
- benchmark history storage
- recommendations
- deployment queue
- reduction queue
- PAP
- CRA
- DIL
- score generation

### Shared contract boundary
- PIS reads SIH outputs
- PIS writes outcome metadata and reconciliation state
- PIS does not push back into scoring or ranking surfaces

## Recommended Phase Order

1. Portfolio snapshot history
2. Change detection
3. Decision lineage
4. Benchmark comparison
5. Attribution
6. Transactions and tax lots, optional future phase

## Architecture Recommendation

Use Fidelity as the portfolio source of truth for Phase 1 snapshot acquisition.
Use SIH as the source of truth for recommendation history and benchmark history.
Use PIS as the read-only analysis layer that explains realized portfolio change.
