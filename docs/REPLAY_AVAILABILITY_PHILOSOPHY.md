# Replay Availability Philosophy

## Purpose

Replay availability is an explicit governance contract, not an inferred UI state.
The platform must always communicate whether a replay category is available,
partially available, blocked, or intentionally not generated.

## Contract

Availability is published to data/current/replay_availability.csv with
operator-diagnosable dependency detail.

Required fields:

- geography
- market_cap_bucket
- industry
- benchmark_available
- vehicle_available
- stock_replay_available
- top_n_available
- replay_generated
- replay_status
- missing_dependencies
- generated_at_utc

## Status Semantics

Allowed replay_status values:

- AVAILABLE
- PARTIAL
- NOT_GENERATED
- MISSING_MAPPING
- MISSING_MARKET_DATA
- BLOCKED

## UI Rules

- UI must not treat unavailable replay categories as generic empty data.
- Availability status and missing dependencies must be visible before chart
  rendering decisions.
- Unsupported categories remain visible and explicitly labeled by status.

## Non-Goals

Replay availability does not imply stock replay or top-N strategy availability
in WP-05B. Those dimensions remain explicit false-state contracts until later
waypoints.
