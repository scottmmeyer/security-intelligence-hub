# PIS Final Architecture Recommendation
**Date:** 2026-06-12

## Final Recommendation

Keep PIS inside the existing `security-intelligence-hub` repository as a separate architectural bounded context.

## Recommended Repository Structure

- `src/sih/` for SIH intelligence generation and recommendation logic
- `src/pis/` for portfolio outcome analysis, snapshot history, change detection, and lineage
- `ui/sih/` for existing SIH-facing surfaces
- `ui/pis/` for future PIS-facing surfaces
- `tests/sih/` for SIH tests
- `tests/pis/` for PIS tests
- `docs/sih/` for SIH architecture and governance
- `docs/pis/` for PIS architecture and planning
- `data/history/pis/` for immutable PIS history partitions

## Ownership Model

- SIH owns intelligence generation and benchmark history.
- PIS owns portfolio snapshots, change events, lineage, and reconciliation queue.
- Run metadata is shared platform evidence.

## Storage Recommendation

Use `data/history/pis/`.

This is the correct choice because it matches the repository’s immutable historical storage pattern and cleanly separates PIS from mutable current-state outputs.

## Phase 1 Scope

The first build should only establish:
- Fidelity snapshot ingestion
- portfolio snapshot history
- position snapshot history
- immutable storage
- validation and tests

No UI.
No public APIs.
No transaction imports.
No tax lots.

## Roadmap Recommendation

1. Phase 1: Portfolio Snapshot History
2. Phase 2: Change Detection
3. Phase 3: Decision Lineage
4. Phase 4: Benchmark Comparison
5. Phase 5: Attribution
6. Phase 6: Transactions and Tax Lots

## Decision Answers

### Q1: Is keeping PIS inside the SIH repository the correct decision today?
Yes.

### Q2: What repository structure is recommended?
A strict `src/sih` / `src/pis` split with matching `tests`, `docs`, `ui`, and `data/history/pis` boundaries.

### Q3: What storage architecture is recommended?
An integrated platform history tree under `data/history/pis/`.

### Q4: What is the exact Phase 1 build scope?
Immutable Fidelity snapshot ingestion and storage only.

### Q5: Can PIS later be extracted into a standalone service if needed?
Yes, if the boundary remains strict and PIS does not inherit SIH internals.

### Q6: What should be implemented first after planning is complete?
Portfolio snapshot ingestion and immutable snapshot persistence.

## Bottom Line

PIS should be implemented as a first-class bounded context inside the existing repository, with strict read-only dependence on SIH outputs and a dedicated history tree for its own outcome records.
