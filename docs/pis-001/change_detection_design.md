# Change Detection Design
**Project:** PIS-001
**Date:** 2026-06-12

## Purpose

Compare yesterday's portfolio snapshot to today's portfolio snapshot and emit structured change events.

## Event Types

### NEW_POSITION
A symbol appears today that did not exist yesterday.

Example:
- Yesterday: `ARW = 0 shares`
- Today: `ARW = 50 shares`

### POSITION_INCREASE
A held symbol has higher shares today.

Example:
- Yesterday: `VRT = 100`
- Today: `VRT = 150`

### POSITION_REDUCTION
A held symbol has lower shares today but remains held.

Example:
- Yesterday: `VRT = 150`
- Today: `VRT = 100`

### POSITION_EXIT
A symbol was held yesterday and is absent today or has gone to zero.

Example:
- Yesterday: `VEA = 200`
- Today: `VEA = 0`

### CASH_INCREASE / CASH_DECREASE
Cash-equivalent balance increased or decreased relative to prior snapshot.

### POSITION_WEIGHT_CHANGE
The weight changed even if shares stayed flat, typically because portfolio value changed or cash moved.

## Detection Rules

1. Align snapshots by account and symbol.
2. Classify symbols into the event types above.
3. Compute deltas for shares, market value, and weight.
4. Separate cash-equivalent symbols from operating cash if Fidelity presents them as holdings.
5. Preserve unmatched rows as candidate reconciliation items.

## Structured Event Model

Recommended fields:
- event_id
- snapshot_date_from
- snapshot_date_to
- account_id
- symbol
- event_type
- shares_before
- shares_after
- market_value_before
- market_value_after
- weight_before
- weight_after
- delta_shares
- delta_market_value
- delta_weight
- source_files
- detection_reason
- lineage_match_id
- lineage_confidence
- resolution_status

## Classification Priority

- If shares move from 0 to >0, classify as NEW_POSITION.
- If shares move from >0 to 0, classify as POSITION_EXIT.
- If shares increase, classify as POSITION_INCREASE.
- If shares decrease, classify as POSITION_REDUCTION.
- If only weight changes, classify as POSITION_WEIGHT_CHANGE.
- If cash changes, emit CASH_INCREASE or CASH_DECREASE.

## Output Principle

The detector should be deterministic, snapshot-based, and explainable.
It should not infer business intent by itself; it should only identify the mechanical change first.
