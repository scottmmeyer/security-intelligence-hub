# PIS Data Ownership Model
**Date:** 2026-06-12

## Ownership Summary

| Data Item | Owner | Rationale |
|---|---|---|
| Portfolio snapshots | PIS | Core portfolio state history is the primary PIS substrate. |
| Position snapshots | PIS | Position-level state is needed for change detection and lineage. |
| Change events | PIS | These are derived outcome objects produced by PIS logic. |
| Decision lineage | PIS | PIS is responsible for connecting outcomes to recommendations. |
| Reconciliation queue | PIS | Missing or unresolved changes belong in PIS workflow. |
| Benchmark history | SIH | SIH already owns market data, benchmark persistence, and history contracts. |
| Recommendation history | SIH | Recommendations are SIH outputs and should remain authoritative there. |
| Provider history | SIH | Provider signal lineage is an SIH concern, not a PIS concern. |
| Run history | Shared | Run metadata is cross-cutting and should remain common platform evidence. |

## Ownership Details

### Portfolio snapshots
Owned by PIS because they are the foundational state records for portfolio outcome analysis.

### Position snapshots
Owned by PIS because they are the atomic units used for change detection and event classification.

### Change events
Owned by PIS because they are derived from snapshot comparison and are not an upstream intelligence artifact.

### Decision lineage
Owned by PIS because the lineage question belongs to outcome analysis, not signal generation.

### Reconciliation queue
Owned by PIS because unresolved portfolio changes are part of the outcome-review workflow.

### Benchmark history
Owned by SIH because benchmark data is part of the shared market-data substrate already implemented there.

### Recommendation history
Owned by SIH because the recommendation layer is the source of truth for what the system advised.

### Provider history
Owned by SIH because provider mappings, signal freshness, and signal coverage belong to the intelligence layer.

### Run history
Shared because both SIH and PIS need consistent lineage and replay references.

## Boundary Rule

PIS may read SIH-owned intelligence history, but it may not mutate it.

SIH may export artifacts that PIS consumes, but PIS should not write back into SIH decision surfaces.
