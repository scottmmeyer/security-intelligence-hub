# Market Data Provider Philosophy

## Purpose

Market data provider integrations must isolate provider semantics from canonical
contracts while preserving deterministic lineage and fail-closed behavior.

## Canonicalization Principles

1. Provider-specific schemas are translated into canonical market-data models.
2. Provider transport quirks (including multi-index tabular shapes) are
   normalized before contract emission.
3. Adjusted close semantics are explicit and contract-visible.
4. Source provider identifiers are persisted with every output row.

## Determinism And Scope

- Provider integrations are deterministic for identical symbols, date windows,
  and configuration inputs.
- WP-05A scope is restricted to benchmark and ETF/fund historical curves.
- Full-universe and top-N stock-derived replay curves are explicitly deferred.

## Validation Coupling

Provider outputs are validated before persistence and replay publication:

- malformed dates are blocked,
- duplicates are blocked,
- non-positive adjusted close values are blocked,
- missing or insufficient historical depth is blocked.

## Governance Boundary

Providers are data sources, not orchestration engines. Retry strategy,
autonomous recovery loops, and runtime mutation policies remain outside provider
modules and are governed by explicit control-plane artifacts.
