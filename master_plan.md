# Security Intelligence Hub Master Plan

## Current Execution State

1. WP-01 - COMPLETE
2. WP-01.5 - COMPLETE
3. WP-02 - COMPLETE
4. WP-02.5 - NOT STARTED
5. WP-03 - COMPLETE
6. WP-03.1 - COMPLETE
7. WP-03.2 - COMPLETE
8. WP-03.4 - COMPLETE
9. WP-03.5 - COMPLETE
10. WP-04 - COMPLETE
11. WP-04.1 - COMPLETE
12. WP-05A - COMPLETE
13. WP-05B - COMPLETE

## Waypoint Roadmap

1. WP-01 - Control Plane Foundation
2. WP-01.5 - Pipeline Observability Foundation
3. WP-02 - Benchmark Intelligence Foundation
4. WP-02.5 - Macro Intelligence Foundation
5. WP-03 - ESS Intake Foundation
6. WP-03.1 - Runtime Governance Hardening
7. WP-03.2 - Fidelity ESS Adapter And Base Universe Generation
8. WP-03.4 - Partitioned Historical Persistence And Verification
9. WP-03.5 - Architecture Hardening And Canonical Terminology Foundation
10. WP-04 - Analytical Universe And Replay Foundation
11. WP-04.1 - Outcome Visualization Prototype UI
12. WP-05A - Benchmark And ETF Historical Curve Foundation
13. WP-05B - Replay Coverage Expansion And Availability Governance

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

### WP-03.5 - Architecture Hardening And Canonical Terminology Foundation
- Canonical terminology dictionary with deterministic non-overlapping definitions
- Security identity philosophy guardrails and point-in-time identity principles
- Temporal integrity philosophy and no-leakage benchmark alignment rules
- Provider lineage philosophy and canonical normalization boundary constraints
- Snapshot consistency rules with explicit propagation and immutability contracts
- Lightweight architecture consistency validator and deterministic tests

### WP-03.4 - Partitioned Historical Persistence And Verification
- Authoritative latest outputs in data/current for signal snapshot and base universe
- Immutable run-partitioned history writes under data/history/signals and data/history/universe
- Append-only signal and universe index artifacts for run-level retrieval
- Deterministic persistence verification for physical rows, run-row isolation,
  lineage fields, and index integrity
- ESS stage persistence summaries with explicit pass/fail accounting

### WP-04 - Analytical Universe And Replay Foundation
- Analytical universe row contract for UI-ready category filtering and replay
	selection
- Configurable benchmark-category registry and separate investable-vehicle
	registry mappings
- Deterministic point-in-time top-N replay selection scaffolding with explicit
	no-lookahead semantics
- Replay performance-series contracts for BENCHMARK, INVESTABLE_VEHICLE,
	FULL_UNIVERSE, and TOP_N_STRATEGY lines
- Immutable replay partition outputs and current replay contract exports for
	future UI graphing
- Validation and deterministic tests for mapping completeness, replay
	reproducibility, and series shape contracts

### WP-04.1 - Outcome Visualization Prototype UI
- Lightweight local UI prototype for replay output visualization
- Local filter controls for geography, market-cap bucket, industry, timeframe,
	and top-N strategy size
- Graph scaffolding for Benchmark, ETF/Fund, Full Universe, and Top-N Strategy
	lines
- Explicit empty-state UX when replay contracts exist but performance history
	series are not yet populated
- Local static-server runner and usage documentation without heavyweight
	frontend tooling

### WP-05A - Benchmark And ETF Historical Curve Foundation
- Yahoo-backed historical providers for benchmark and investable vehicle curves
- Adjusted-close and cumulative-return persistence contracts for benchmark and
	ETF/fund outputs
- Historical replay-window validation that blocks future end-date windows
- Fail-closed validators for missing history, malformed rows, duplicates, and
	insufficient curve depth
- UI fallback behavior for empty-state, single-timestamp point-in-time, and
	multi-date cumulative line rendering
- Explicit scope boundary preserving full-universe/top-N stock curves as
	deferred work

### WP-05B - Replay Coverage Expansion And Availability Governance
- Replay matrix generation for category-scoped coverage expansion
- Availability registry publication with explicit replay status contracts
- Mapping completeness validators for required benchmark and ETF/fund symbols
- UI availability panel and governed unsupported-category disclosure
- Replay metadata, availability metadata, and matrix reference persistence
- Validation/test expansion for replay/UI consistency and coverage governance

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
6. WP-03.4 depends on WP-03.2 provider adaptation and canonical row production.
7. WP-04 depends on WP-03 intake contracts and canonical classifications.
8. WP-04 depends on WP-03.4 persistence integrity and immutable history contracts.
9. WP-04 depends on WP-03.5 terminology and architecture hardening guardrails.
10. WP-04.1 depends on WP-04 replay contract outputs and mapping registries.
11. WP-05A depends on WP-04.1 contract-driven visualization baseline and
	WP-04 replay selection semantics.
12. WP-05B depends on WP-05A historical curve foundation and extends category
  coverage with explicit availability governance.

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

### WP-03.2 - Fidelity ESS Adapter And Base Universe Generation
- Fidelity provider-native schema contracts and adapter layer
- Deterministic provider-to-canonical mapping with provenance lineage
- Fail-closed mapping validation with explicit malformed/unmapped visibility
- Canonical base universe append contracts and lineage registry
- ESS stage row accounting for discovered, validated, normalized, rejected,
  and appended records

## WP-03.5 Success Criteria

- Canonical terminology is explicitly defined and reused across architecture docs.
- Security identity, temporal integrity, provider lineage, and snapshot
	consistency philosophies are documented with deterministic boundaries.
- Architecture consistency validator detects missing foundational docs and
	terminology or principle drift through lightweight deterministic checks.
- Unit tests cover required document presence, terminology integrity, snapshot
	consistency rule coverage, and governance artifact detection.
- Governance artifacts reflect the hardened foundation prior to WP-04 expansion.

## WP-03.4 Success Criteria

- Current authoritative outputs are emitted deterministically in data/current.
- Immutable historical partitions are created by snapshot_date and run_id.
- Index rows are appended once per run with valid lineage path references.
- Persistence verification fails closed for row-count mismatches, malformed rows,
  run isolation violations, or missing lineage fields.
- ESS stage reports deterministic persistence validation summaries in manifests.