# security-intelligence-hub

Security Intelligence Hub is the canonical platform for normalized market signals,
provider analytics, historical trend tracking, and portfolio intelligence
integration.

## Status

This repository is in Phase 1 foundation scaffolding and WDD initialization.
The current implementation establishes architecture boundaries, deterministic
SDLC contracts, navigation waypoints, benchmark scaffolding, ESS intake lanes,
and canonical placeholder models.

## Vision

The platform is designed to provide:

- Normalized ingest pipelines for heterogeneous security market signals.
- Provider-level quality and performance analytics.
- Historical trend analysis for decision support.
- Portfolio intelligence integration for operational workflows.

## Planned Core Domains

- Data ingestion and schema normalization.
- Signal scoring and enrichment.
- Provider benchmarking and confidence tracking.
- Time-series storage and trend analytics.
- API and dashboard surfaces for portfolio consumers.

## Phase 1 Scope

- Control plane foundation and waypoint navigation state.
- Benchmark intelligence foundation for US and international dimensions.
- Macro intelligence schema scaffolding.
- ESS intake foundation with split StarMine and non-StarMine Zacks lanes.
- Security master canonical model placeholders.

## Phase 1 Non-Goals

- No scraping or external ingestion automation yet.
- No machine learning or predictive pipelines yet.
- No dashboards or UI layers yet.
- No microservices, orchestration engines, or runtime state machines.

## Repository Layout

Current repository contents:

- `config/` - deterministic registries for providers, benchmark mappings, and
	classification constants.
- `docs/` - architecture, governance, benchmark, and waypoint contracts.
- `incoming/` - intake landing zones for ESS and manual files.
- `data/` - storage boundaries for raw, normalized, history, derived, and
	export data products.
- `src/` - canonical model and domain package boundaries.
- `navigation_state.yaml` - active waypoint state.
- `master_plan.md` - waypoint roadmap and dependency chain.
- `wdd_log.md` - deterministic WDD run log.

Suggested near-term structure:

- `src/` - application and domain logic.
- `data/` - sample datasets and fixtures.
- `docs/` - design notes, ADRs, and architecture references.
- `tests/` - unit, integration, and system tests.

## Getting Started

Until scaffolding is added, clone and track this repository as the source of
truth for architecture and planning.

```bash
git clone https://github.com/scottmmeyer/security-intelligence-hub.git
cd security-intelligence-hub
pip install -r requirements.txt
```

## Next Steps

- WP-02: finalize benchmark registry identifiers and history contracts.
- WP-02.5: define macro snapshot vocabulary and regime labels.
- WP-03: implement deterministic ESS file validation and normalization stubs.
- WP-04: expand security master validation and classification rules.

## License

License information will be added as the project baseline is finalized.
