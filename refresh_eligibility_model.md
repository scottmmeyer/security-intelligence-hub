# SIGNAL-COVERAGE-06: Refresh Eligibility Model

## Inputs

Per provider:

- `research_stale`: latest provider sourced date differs from today
- `coverage.status`: COMPLIANT, DEGRADED, or NON_COMPLIANT
- `coverage.symbols`: per-symbol classification including applicability

## Decision Logic

1. If `research_stale = true`:
   - mode = `research_refresh`
   - run smart refresh set plus forced applicable holdings

2. Else if `research_stale = false` and coverage has stale/missing/failed applicable symbols:
   - mode = `coverage_repair`
   - run only stale/missing/failed applicable holdings

3. Else:
   - mode = `skip_compliant`
   - no provider fetch submitted

## Guarantees

- "Provider fresh" no longer implies "refresh skip"
- Holdings degradation has authority to trigger repair refresh
- Research staleness path keeps existing behavior and scope

## Output Metrics

Each provider emits:

- `state` (`RESEARCH_FRESH_*` or `RESEARCH_STALE_*`)
- `mode`
- `submitted`, `refreshed`, `skipped`, `failed`
- `coverage_before`, `coverage_after`
- `runtime_sec`
