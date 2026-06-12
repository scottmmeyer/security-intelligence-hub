# SIGNAL-COVERAGE-02 Completion

## Scope

This change implements ESS coverage drop detection only.

- No ESS scoring changes
- No CW-DAS changes
- No recommendation logic changes

## Root Cause

ESS is externally sourced from Fidelity / StarMine. SIH cannot force provider coverage.

Before this change, if a currently held position had ESS coverage on a prior day and
then disappeared from the latest incoming StarMine file, SIH emitted no warning.
The prior ESS value remained in place, which created silent stale ESS.

## Detection Architecture

Phase 2 introduces a structured warning artifact:

- `data/current/ess_coverage_warning.json`

The artifact is produced during ESS intake after successful persistence.

Detection logic:

1. Load current equity holdings from the latest PAR `holdings.csv`
2. Build the incoming StarMine symbol set from the current intake payload
3. Load prior ESS-covered symbols from `data/current/signal_snapshot.csv`
4. Detect true coverage drops:
   - symbol is currently held
   - symbol had prior ESS coverage
   - symbol is absent from the latest incoming StarMine file
5. Emit `ESS_COVERAGE_GAP` details with:
   - symbol
   - company name
   - last ESS date
   - current ESS posture
   - days stale

## UI Integration

Two existing provider-health surfaces now consume the same artifact.

### Outcome UI

`/api/signal-status` now includes an `ess` provider entry.

When gaps exist:

- badge state becomes `FRESH_PARTIAL`
- the provider health pill shows an ESS coverage warning
- example symbols are displayed inline

### Portfolio Alignment

`signal_source_metadata` now includes:

- `ess_refresh_date`
- `ess_coverage_warning`

The Signal Freshness panel now renders an ESS Coverage Warning block when held
positions are absent from the latest ESS file.

## Test Coverage

Added stage-level tests validating:

1. Holding present in incoming ESS file → no warning
2. Holding absent but previously ESS-covered → warning generated
3. Multiple absent holdings → grouped warning with examples

## Runtime Impact

Negligible.

Detection is a local comparison across:

- latest PAR holdings
- incoming normalized ESS rows
- current signal snapshot

No provider calls were added.

## Outcome

SIH can now detect ESS coverage loss on held positions.
Silent ESS coverage drops are no longer invisible.