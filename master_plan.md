# Security Intelligence Hub Master Plan

## Current Execution State

1. WP-01 - COMPLETE
2. WP-01.5 - COMPLETE
3. WP-02 - COMPLETE
4. WP-02.5 - NOT STARTED
5. WP-03 - IN PROGRESS
6. WP-04 - NOT STARTED

## Waypoint Roadmap

1. WP-01 - Control Plane Foundation
2. WP-01.5 - Pipeline Observability Foundation
3. WP-02 - Benchmark Intelligence Foundation
4. WP-02.5 - Macro Intelligence Foundation
5. WP-03 - ESS Intake Foundation
6. WP-04 - Security Master Foundation

## Waypoint Deliverables

### WP-01 - Control Plane Foundation
- Repository scaffolding with deterministic domain boundaries
- Architecture, governance, and navigation documents
- Initial configuration registries and canonical model placeholders

### WP-01.5 - Pipeline Observability Foundation
- Run manifest and stage manifest contracts in runs/
- Flat pipeline status semantics and stage result models
- Sequential deterministic runner scaffolding without orchestration engines
- Artifact registry records with lineage metadata and summary rendering
- Future terminal, chat, and dashboard-compatible execution summaries

### WP-02 - Benchmark Intelligence Foundation
- Authoritative benchmark registry with deterministic mappings
- Benchmark snapshot and outcome contracts with run lineage fields
- Immutable benchmark history scaffolding in data/history/benchmarks/
- Fail-closed benchmark validation for registry and lineage integrity

### WP-02.5 - Macro Intelligence Foundation
- Macro snapshot schema and taxonomy conventions
- Market regime vocabulary and contract documentation

### WP-03 - ESS Intake Foundation
- Isolated intake zones for StarMine and non-StarMine analyst universes
- Coverage-domain and ESS schema contracts
- Provenance-aware ESS normalization scaffolding
- Immutable signal snapshot append and lineage registry scaffolding
- ESS pipeline stage integration for manifest-aware execution

### WP-04 - Security Master Foundation
- Canonical security model enrichment and validation rules
- Security-type and region classification consistency checks
- Snapshot-aware market-cap normalization and lineage-aware classification

## Success Criteria

- Every waypoint has explicit in-scope and out-of-scope boundaries.
- Artifacts are deterministic, versioned, and reproducible.
- Provider semantics remain isolated from canonical domain models.
- Historical records are append-only and immutable by policy.
- Downstream consumers can rely on exported intelligence contracts.

## Dependency Chain

1. WP-01 enables governance and reproducible execution boundaries.
2. WP-01.5 depends on WP-01 for deterministic governance boundaries.
3. WP-02 depends on WP-01 and WP-01.5 for observable lineage contracts.
4. WP-02.5 depends on WP-02 baseline benchmark context.
5. WP-03 depends on WP-01 through WP-02.5 for normalization context.
6. WP-04 depends on WP-03 intake contracts and canonical classifications.

## WP-02 Success Criteria

- Benchmark registry passes deterministic validation with explicit errors.
- Snapshot lineage contracts enforce run_id and source consistency.
- Historical benchmark artifacts are append-oriented and immutable by policy.
- Unit tests cover valid registry, malformed entries, and duplicate mappings.

## WP-01.5 Success Criteria

- Run and stage manifests are generated as deterministic historical evidence.
- Pipeline statuses remain flat, explicit, and fail-closed.
- Execution summaries are readable in terminal and chat contexts.
- Artifacts are registered with producing stage and lineage notes.
- Non-goals remain enforced: no DAG orchestration, schedulers, retries, or
	runtime state-machine complexity.

## Market-Cap Classification Alignment Notes

- Canonical internal market-cap framework is currently Fidelity-aligned.
- Classification is snapshot-based and cannot be treated as immutable metadata.
- Provider lineage fields are required for historical reproducibility.
- Future provider divergence is handled through deterministic normalization
  contracts rather than implicit assumptions.

## WP-03 Success Criteria

- ESS schema validation fails closed with explicit row-level errors.
- Coverage-domain assignment remains explicit and deterministic.
- ESS text values and numeric mapping provenance are preserved.
- Signal snapshots append immutably with run lineage metadata.
- ESS stage integrates with sequential pipeline manifests without introducing
	orchestration complexity.