# SDLC Governance

## Governance Objective

Establish a deterministic, reproducible, and artifact-driven SDLC for Security
Intelligence Hub with calm incremental delivery.

## Core Governance Rules

- Deterministic processing over opaque orchestration.
- Explicit contracts over implicit assumptions.
- Immutable historical records over in-place mutation.
- Waypoint-scoped delivery over parallel speculative initiatives.
- Observable run artifacts over ad hoc operator knowledge.

## Required Artifacts

- navigation_state.yaml
- master_plan.md
- wdd_log.md
- domain configuration registries in config/
- architecture and philosophy documents in docs/

## Change Control

- Every significant change records intent, action, result, and drift assessment.
- Architectural boundary changes require updates to both architecture and
  navigation artifacts.
- Out-of-scope implementation is deferred with explicit TODOs.

## Reproducibility Expectations

- Inputs and outputs are path-bounded and version-controlled.
- Configuration remains declarative and human-reviewable.
- Transformations are deterministic for identical inputs.

## Operational Observability Baseline

- runs/ captures run-level logs and manifest metadata.
- validation/ modules own deterministic quality checks.
- Historical datasets are append-oriented and audit-friendly.