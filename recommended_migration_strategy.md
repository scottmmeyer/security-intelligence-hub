# Recommended Migration Strategy

## Recommendation
Use Strategy C: Hybrid.

## Why Hybrid (C) over A or B
- A (one-time only) does not protect against future out-of-band historical loads.
- B (incremental only) does not remediate existing historical gap.
- C resolves historical debt immediately and maintains continuity thereafter.

## Strategy C Plan
1. One-time historical import:
- Import all valid historical PM snapshot identities.
- Deduplicate by portfolio_snapshot_id.
- Validate and report invalid artifacts.

2. Incremental synchronization:
- Continue automatic registration on new upload/analyze events.
- Add optional periodic reconciliation scan for newly discovered historical runs if needed.

## Expected Counts
From current forensic inventory:
- total historical run artifacts: 235
- unique snapshot identities: 68
- immediately migratable identities (valid date): 67
- after malformed-date remediation: 68

## Immediate Functional Impact
After migration, PIS immediately has enough data for:
- value timeline population

After migration, still requires additional PIS feature implementation for:
- robust change detection
- benchmark comparison
- full decision lineage (recommendation -> trade -> outcome)

## Final Operational Recommendation
Run historical import for all PAR runs now, then keep incremental registration enabled for new analyses.
