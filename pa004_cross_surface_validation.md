# PA-004 Cross-Surface Validation

Repository: security-intelligence-hub  
Date: 2026-06-09

## Validation Evidence from Latest PAR (PAR-20260529-76C900C3)

### TSLA (DO_NOT_SELL)

| Surface | Before PA-004 Fix | After PA-004 Fix | Expected |
|---|---|---|---|
| Deployment Queue | BLOCKED_BY_POLICY ✓ | BLOCKED_BY_POLICY ✓ | BLOCKED_BY_POLICY |
| security_overlays.csv | BLOCKED_BY_POLICY ✓ | BLOCKED_BY_POLICY ✓ | BLOCKED_BY_POLICY |
| recommendations.json REDUCE_OVERWEIGHT | BLOCKED_BY_POLICY ✓ | BLOCKED_BY_POLICY ✓ | BLOCKED_BY_POLICY |
| PAP Cat 1 | routes to cat5 ✓ | routes to cat5 ✓ | cat5 (suppressed) |
| PAP Cat 3 (Allocation Reduction) | **appeared without block** ✗ | routes to cat5 ✓ | cat5 (suppressed) |
| PAP Cat 4 (Funding Sources) | **not explicitly blocked** ✗ | excluded ✓ | excluded |

**TSLA consistency: PASS across all surfaces after fix.**

### DODFX (SELL_LAST)

| Surface | Before PA-004 Fix | After PA-004 Fix | Expected |
|---|---|---|---|
| Deployment Queue | tail-ranked in sell cohort ✓ | tail-ranked ✓ | DEFERRED_BY_POLICY |
| security_overlays.csv (flag=HOLD) | EXECUTABLE ✓* | EXECUTABLE ✓* | EXECUTABLE* |
| recommendations.json REDUCE_OVERWEIGHT | DEFERRED_BY_POLICY ✓ | DEFERRED_BY_POLICY ✓ | DEFERRED_BY_POLICY |
| PAP Cat 3 (Allocation Reduction) | **appeared without deferral** ✗ | DEFERRED_BY_POLICY, tail-ranked ✓ | DEFERRED_BY_POLICY |
| PAP Cat 4 (Funding Sources) | **no priority gate** ✗ | LAST_RESORT priority ✓ | Last in priority |

*DODFX overlay execution_state is correctly EXECUTABLE when opportunity_flag=HOLD (no sell-context). The SELL_LAST policy correctly does not block hold actions.

**DODFX consistency: PASS across all surfaces after fix.**

## Summary

| Surface | Pre-fix TSLA | Post-fix TSLA | Pre-fix DODFX | Post-fix DODFX |
|---|---|---|---|---|
| Deployment Queue | ✓ | ✓ | ✓ | ✓ |
| security_overlays.csv | ✓ | ✓ | ✓* | ✓* |
| recommendations.json | ✓ | ✓ | ✓ | ✓ |
| PAP Cat 1 | ✓ | ✓ | n/a | n/a |
| PAP Cat 3 | ✗ | ✓ | ✗ | ✓ |
| PAP Cat 4 | ✗ | ✓ | ✗ | ✓ |

**All remaining inconsistencies resolved. No conflicting advisory outputs.**
