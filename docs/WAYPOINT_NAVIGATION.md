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
5. WP-04 - Security Master Foundation

## Navigation Contract

- The active waypoint is recorded in navigation_state.yaml.
- Each waypoint declares objective, in-scope, out-of-scope, and next action.
- Work cannot advance to a new waypoint without closure evidence in wdd_log.md.
- Cross-waypoint changes require explicit dependency declaration.

## Completion Rules

A waypoint is complete when:

- Deliverables listed in master_plan.md are present and reviewable.
- Architecture boundaries remain intact.
- Drift assessment confirms no out-of-scope implementation leakage.

## Drift Prevention

- Avoid speculative implementation beyond active waypoint boundaries.
- Preserve provider abstraction and snapshot immutability constraints.
- Record TODO markers for future work instead of premature implementation.