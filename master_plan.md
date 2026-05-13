# Security Intelligence Hub Master Plan

## Current Execution State

1. WP-01 - COMPLETE
2. WP-02 - IN PROGRESS
3. WP-02.5 - NOT STARTED
4. WP-03 - NOT STARTED
5. WP-04 - NOT STARTED

## Waypoint Roadmap

1. WP-01 - Control Plane Foundation
2. WP-02 - Benchmark Intelligence Foundation
3. WP-02.5 - Macro Intelligence Foundation
4. WP-03 - ESS Intake Foundation
5. WP-04 - Security Master Foundation

## Waypoint Deliverables

### WP-01 - Control Plane Foundation
- Repository scaffolding with deterministic domain boundaries
- Architecture, governance, and navigation documents
- Initial configuration registries and canonical model placeholders

### WP-02 - Benchmark Intelligence Foundation
- Authoritative benchmark registry with deterministic mappings
- Benchmark snapshot and outcome contracts with run lineage fields
- Immutable benchmark history scaffolding in data/history/benchmarks/
- Fail-closed benchmark validation for registry and lineage integrity

### WP-02.5 - Macro Intelligence Foundation
- Macro snapshot schema and taxonomy conventions
- Market regime vocabulary and contract documentation

### WP-03 - ESS Intake Foundation
- Isolated intake zones for StarMine and non-StarMine Zacks universes
- Deterministic normalization contracts and validation boundaries

### WP-04 - Security Master Foundation
- Canonical security model enrichment and validation rules
- Security-type and region classification consistency checks

## Success Criteria

- Every waypoint has explicit in-scope and out-of-scope boundaries.
- Artifacts are deterministic, versioned, and reproducible.
- Provider semantics remain isolated from canonical domain models.
- Historical records are append-only and immutable by policy.
- Downstream consumers can rely on exported intelligence contracts.

## Dependency Chain

1. WP-01 enables governance and reproducible execution boundaries.
2. WP-02 depends on WP-01 contracts for deterministic registries.
3. WP-02.5 depends on WP-02 baseline benchmark context.
4. WP-03 depends on WP-01 through WP-02.5 for normalization context.
5. WP-04 depends on WP-03 intake contracts and canonical classifications.

## WP-02 Success Criteria

- Benchmark registry passes deterministic validation with explicit errors.
- Snapshot lineage contracts enforce run_id and source consistency.
- Historical benchmark artifacts are append-oriented and immutable by policy.
- Unit tests cover valid registry, malformed entries, and duplicate mappings.