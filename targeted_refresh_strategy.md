# SIGNAL-COVERAGE-06: Targeted Refresh Strategy

## Target Set Construction

Coverage-repair mode builds a target set from provider coverage symbols where:

- `applicable = true`
- classification in `{STALE, MISSING, FAILED}`

Targets are deduplicated and sorted for stable execution.

## Why This Strategy

- Repairs mandatory holdings gaps without unnecessary broad refresh load
- Preserves provider quota and latency by avoiding compliant symbols
- Maintains clear accountability: submitted symbols are directly tied to failed coverage classifications

## Distinction from Research Refresh

- Research-refresh mode remains broad (smart set + forced holdings)
- Coverage-repair mode is narrow (only degraded applicable holdings)

This split preserves prior stale-provider behavior while adding deterministic holdings-gap remediation.

## Validation Coverage

Phase 6 tests assert:

- fresh provider + degraded coverage triggers `coverage_repair`
- fresh provider + compliant coverage skips
- missing applicable holdings are submitted
- stale provider still uses `research_refresh`
