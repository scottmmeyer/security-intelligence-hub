# Operational Refresh Enforcement

## Objective

Mandatory Holdings Coverage is now enforced at the provider submission layer for:

- Zacks
- Danelfin
- Yahoo

without changing:

- scoring formulas
- CW-DAS weights
- recommendation ranking logic

## Enforcement Model

Refresh submission now works in two stages:

1. Load the canonical active holdings baseline.
2. Filter that baseline to provider-applicable symbols before constructing the provider refresh execution set.

Shared helper:

- `load_provider_applicable_symbols()` in `src/portfolio/holdings_coverage.py`

Refresh entrypoints:

- `scripts/refresh_signals.py::_refresh_zacks()`
- `scripts/refresh_signals.py::_refresh_danelfin()`
- `scripts/refresh_signals.py::_refresh_yahoo()`

## Current Live Denominators

- Active holdings baseline: `74`
- Provider-applicable holdings: `58`
- Explicitly not applicable: `16`

## Current Live Cache Status

The enforcement code is fixed, but the current provider caches still reflect pre-fix refresh outcomes:

| Provider | Applicable | Covered Today | Stale | Missing | Not Applicable | Status |
|---|---:|---:|---:|---:|---:|---|
| Zacks | 58 | 34 | 22 | 0 | 16 | DEGRADED |
| Danelfin | 58 | 32 | 22 | 0 | 16 | DEGRADED |
| Yahoo | 58 | 15 | 22 | 0 | 16 | DEGRADED |

This means the code path is corrected, but a fresh operational run is still required to bring the live cache into compliance.

## Acceptance Status

- Applicable holdings are now included in provider refresh submission sets by construction.
- Non-applicable holdings are not silently skipped; they are classified explicitly.
- The previous `34 submitted / 40 skipped` framing is replaced by:
  - `58 applicable`
  - `16 not applicable`
  - remaining gaps described as stale/failed current cache state, not denominator ambiguity.