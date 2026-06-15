# Phased Implementation Roadmap
**Project:** PIS-001
**Date:** 2026-06-12

## Phase 1 — Portfolio Snapshot History

Goal:
- persist Fidelity portfolio downloads as immutable portfolio snapshots

Deliverables:
- snapshot metadata model
- position snapshot model
- parser validation
- append-only storage

## Phase 2 — Change Detection

Goal:
- compare consecutive snapshots and emit structured events

Deliverables:
- NEW_POSITION
- POSITION_INCREASE
- POSITION_REDUCTION
- POSITION_EXIT
- CASH_INCREASE
- CASH_DECREASE
- POSITION_WEIGHT_CHANGE

## Phase 3 — Decision Lineage

Goal:
- connect detected changes to SIH recommendation history

Deliverables:
- recommendation-to-trade mapping
- confidence scoring
- lineage evidence summary
- unresolved event routing

## Phase 4 — Benchmark Comparison

Goal:
- compare portfolio performance against SIH-owned benchmark history

Deliverables:
- benchmark pull contract
- portfolio vs benchmark display
- alpha calculation

## Phase 5 — Attribution

Goal:
- explain which holdings and decisions contributed to the outcome

Deliverables:
- contribution by holding
- allocation effect
- trade outcome tracking
- concentration outcome tracking

## Phase 6 — Transactions and Tax Lots

Goal:
- optionally add richer accounting detail later

Deliverables:
- transaction import
- tax lot support
- dividend handling
- cash-flow normalization

## Recommended Order

1. snapshot history
2. change detection
3. decision lineage
4. benchmark comparison
5. attribution
6. transactions and tax lots later

## Why this order

This sequence keeps PIS useful early while avoiding over-designing for data Fidelity does not currently provide in a reliable machine-ingestible form.
