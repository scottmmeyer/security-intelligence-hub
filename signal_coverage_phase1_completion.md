# SIGNAL-COVERAGE-01 Phase 1 Completion

## Scope

Phase 1 remediates the two active P1 defects identified in the SIGNAL-COVERAGE-01 audit:

- SIGNAL-COVERAGE-01a — Danelfin smart-refresh path could exclude held equity positions
- SIGNAL-COVERAGE-01b — Yahoo smart-refresh path could exclude held equity positions

Non-goals preserved:

- No scoring formula changes
- No CW-DAS weight changes
- No recommendation logic changes
- No research-universe expansion beyond coverage governance

## Root Cause

The defect pattern was architectural rather than provider-specific.

`run_outcome_ui.py` invokes:

`refresh_signals.py --smart`

In smart mode, Danelfin and Yahoo previously built their refresh sets from `_smart_universe_symbols()`, which contains only:

- BULLISH / VERY_BULLISH symbols
- NEUTRAL symbols with raw ESS >= 6.5

That design optimized research-universe efficiency, but holdings were not treated as a first-class constraint. As a result, a currently held position could move from bullish to neutral/bearish and silently fall out of the refresh set.

## Remediation Architecture

Phase 1 adopts the Mandatory Holdings Coverage Rule for the active smart-refresh providers.

### Danelfin

`_refresh_danelfin()` now accepts:

`forced_symbols: set[str] | None = None`

When `smart=True`:

1. Load current equity holdings from the latest PAR `holdings.csv` via `_load_portfolio_equity_holdings()`
2. Build the smart universe from `_smart_universe_symbols(_BASE_UNIVERSE)`
3. Prepend forced holdings with `_merge_forced_symbols(...)`
4. Preserve smart filtering for non-held symbols

### Yahoo

`_refresh_yahoo()` now uses the same architecture:

- `forced_symbols: set[str] | None = None`
- holdings loaded dynamically
- forced holdings prepended ahead of smart-refresh symbols
- smart filtering preserved for non-held symbols

### Shared Helper

`_merge_forced_symbols(base_symbols, forced_symbols)`

This helper guarantees:

- forced holdings always included
- forced holdings fetched first
- no duplicates
- smart mode remains intact for the rest of the universe

## UI Refresh Path Decision

Decision: **Keep smart mode. Add mandatory holdings. Do not switch to full-universe mode.**

Reasoning:

- Smart mode still provides runtime efficiency for non-held symbols
- Mandatory holdings coverage eliminates the governance blind spot
- Switching the UI path to full-universe mode would solve the defect, but at unnecessary runtime cost
- The Zacks remediation already established the correct pattern: optimize research coverage, never optimize away holdings coverage

Result:

`/api/signal-refresh` can continue using `--smart` safely because Danelfin and Yahoo now force-include holdings internally.

## Governance Standard

Phase 1 implements the Mandatory Holdings Coverage Rule for the active smart-refresh providers:

> If a symbol is currently held in the portfolio, that symbol must receive refresh coverage regardless of smart-refresh filtering.

Applied in this phase to:

- Danelfin
- Yahoo
- Zacks was already remediated in ZACKS-REFRESH-UNIVERSE-01

## Runtime Impact

The audit identified 37 held equity positions excluded from Danelfin and Yahoo smart-refresh.

Phase 1 adds those holdings back only when they are not already in the smart set.

Expected impact:

- Danelfin: modest increase relative to smart mode, still materially below full-universe refresh
- Yahoo: modest increase relative to smart mode, still materially below full-universe refresh
- Smart mode preserved for all non-held symbols

This keeps operator-triggered refresh efficient while closing the governance gap.

## Test Coverage

Added:

`tests/test_signal_coverage_phase1.py`

The tests validate, in smart mode, that:

- Danelfin refresh includes all dynamically loaded current equity holdings
- Yahoo refresh includes all dynamically loaded current equity holdings
- a non-held, low-priority smart-refresh exclusion still remains excluded
- holdings are loaded dynamically from a temporary PAR `holdings.csv`
- no symbols are hardcoded in the test assertions

Focused test result:

- `2 passed`

## Remaining Gaps After Phase 1

Phase 1 closes the active Danelfin/Yahoo smart-refresh defects.

Remaining provider gaps from the audit:

- ESS still has passive coverage risk if Fidelity/StarMine omits a held symbol from the incoming file
- `refresh_portfolio_signals.py` still uses a hardcoded `_PORTFOLIO_SYMBOLS` list and should be remediated separately
- Mandatory Holdings Coverage is not yet uniformly encoded as an automated invariant test across every provider cache

## Outcome

Phase 1 completes the P1 remediation objective:

- Held positions can no longer be excluded from Danelfin refresh due to smart filtering
- Held positions can no longer be excluded from Yahoo refresh due to smart filtering
- Smart refresh remains active and efficient for non-held symbols
- Recommendation logic and scoring logic remain unchanged
