# PIS Phase 1 Implementation Plan
**Date:** 2026-06-12

## Phase 1 Goal

Build immutable portfolio snapshot history from Fidelity portfolio download files.

## Phase 1 Data Model

### PortfolioSnapshot
Required fields:
- snapshot_id
- snapshot_date
- account_id
- account_name
- source_file
- source_format
- portfolio_value
- equity_value
- cash_value
- holding_count
- ingestion_status
- created_at_utc
- lineage_source

### PositionSnapshot
Required fields:
- snapshot_id
- snapshot_date
- account_id
- account_name
- symbol
- description
- shares
- price
- market_value
- weight
- cost_basis
- gain_loss_dollar
- gain_loss_percent
- total_gain_loss_dollar
- total_gain_loss_percent
- security_type
- position_state
- source_file
- created_at_utc

## Ingestion Flow

1. Operator drops Fidelity portfolio file into the existing incoming portfolio lane.
2. PIS parser validates the export and normalizes the file into snapshot records.
3. A deterministic snapshot id is generated.
4. Portfolio snapshot and position snapshot records are written to immutable history partitions.
5. Validation emits warnings for duplicate symbols, zero-value rows, and unusual totals.
6. PIS publishes the snapshot metadata for downstream change detection.

## Storage Format

Use append-only CSV or equivalent row-oriented immutable storage under `data/history/pis/`.

Recommended partitioning:
- snapshot date
- run id
- account id where needed

## APIs

No Phase 1 public UI or production API should be built yet.

The only required contracts are internal read-only functions or service boundaries that allow later phases to read snapshot history.

Recommended internal endpoints or accessors, if introduced later:
- load latest portfolio snapshot
- load snapshot history by account
- load snapshot by snapshot id

## UI Requirements

Phase 1 should not build a user interface.

At most, Phase 1 may require future design hooks for:
- snapshot list view
- snapshot detail view
- change history entry points

## Test Strategy

Phase 1 should be validated with deterministic tests for:
- Fidelity file parsing
- field detection
- snapshot id stability
- duplicate symbol handling
- cash row handling
- append-only storage behavior
- immutability of prior snapshots

## Acceptance Criteria

Phase 1 is complete when:
- Fidelity files can be turned into stable portfolio snapshot records
- positions are normalized consistently
- snapshot outputs are immutable
- the snapshot history can support Phase 2 change detection without redesign
