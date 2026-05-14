# Historical Market Data Philosophy

## Purpose

Define deterministic storage and provider boundaries for historical market data
used by replay return generation.

## Core Principles

- Historical prices are point-in-time records and must remain append-only in
  partitioned history.
- Current outputs are mutable latest snapshots for convenience consumption.
- Provider ingestion must preserve source attribution and ingestion timestamp.
- Missing coverage is explicit and validated; no silent backfill assumptions.
- Provider abstraction is mandatory to avoid lock-in.

## Storage Contracts

Current mutable files:

- data/current/security_prices.csv
- data/current/benchmark_returns.csv
- data/current/investable_vehicle_returns.csv

Immutable historical partitions:

- data/history/prices/symbol=<SYMBOL>/prices.csv
- data/history/benchmarks/benchmark_id=<ID>/benchmark_returns.csv
- data/history/investable_vehicles/vehicle_id=<ID>/vehicle_returns.csv

## Determinism Rules

- Date values must be ISO-8601 and monotonic within each series.
- Duplicate symbol/date, benchmark/date, and vehicle/date rows are prohibited.
- Return calculations use adjusted close for continuity across corporate events.
- Historical data ingestion cannot mutate previously recorded rows.
