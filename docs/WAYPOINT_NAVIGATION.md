# Waypoint Navigation

## Purpose

Waypoint navigation provides deterministic progression through delivery phases.
Each waypoint constrains scope, declares explicit contracts, and prevents
architectural drift.

## Active Waypoints

1. WP-01 - Control Plane Foundation
2. WP-02 - Benchmark Intelligence Foundation
3. WP-02.5 - Macro Intelligence Foundation
4. WP-03 - ESS Intake Foundation
5. WP-03.1 - Runtime Governance Hardening
6. WP-03.2 - Fidelity Adapter And Base Universe Foundation
7. WP-03.4 - Partitioned Historical Persistence Foundation
8. WP-03.5 - Architecture Hardening And Terminology Foundation
9. WP-04 - Security Master Foundation

## Navigation Contract

- The active waypoint is recorded in navigation_state.yaml.
- Each waypoint declares objective, in-scope, out-of-scope, and next action.
- Work cannot advance to a new waypoint without closure evidence in wdd_log.md.
- Cross-waypoint changes require explicit dependency declaration.
- Multi-unit commit execution must preserve deterministic staging boundaries by
	unit scope.

## Completion Rules

A waypoint is complete when:

- Deliverables listed in master_plan.md are present and reviewable.
- Architecture boundaries remain intact.
- Drift assessment confirms no out-of-scope implementation leakage.

## Drift Prevention

- Avoid speculative implementation beyond active waypoint boundaries.
- Preserve provider abstraction and snapshot immutability constraints.
- Record TODO markers for future work instead of premature implementation.
- Keep runtime evidence governance separate from hygiene and documentation
	governance.