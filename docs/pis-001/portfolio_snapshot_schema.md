# Portfolio Snapshot Schema
**Project:** PIS-001
**Date:** 2026-06-12

## Canonical Schema Proposal

PIS should model portfolio state in two levels:
- portfolio snapshot
- position snapshot

## Table 1: Portfolio Snapshot

Represents the whole portfolio at a point in time.

### Fields
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
- created_at_utc
- ingestion_status
- lineage_source

### Notes
- `portfolio_value` should equal the sum of all position market values, including cash-like rows.
- `equity_value` should sum non-cash positions only.
- `cash_value` should isolate money market, sweep, and other cash-equivalent positions.
- `lineage_source` should reference the Fidelity file and the upstream SIH snapshot used for reconciliation.

## Table 2: Position Snapshot

Represents one holding within a portfolio snapshot.

### Fields
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

### Notes
- `weight` is `market_value / portfolio_value`.
- `position_state` should distinguish active holdings from cash-equivalent or non-analyzable rows.
- The schema must retain source fields even when PIS derives additional values.

## Keys

- Primary snapshot key: `snapshot_id`
- Position primary key: `snapshot_id + account_id + symbol`
- Change detection should compare the same account across consecutive snapshot_dates.

## Recommended Derived Fields

- delta_shares
- delta_market_value
- delta_weight
- delta_price
- position_change_type
- lineage_match_id
- lineage_confidence
- reconciliation_status

## Design Principle

The snapshot schema should be append-only and immutable.
New data creates new snapshot rows. Existing snapshots are never overwritten.
