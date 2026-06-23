# REFRESH-HEALTH-02A Part G - Existing Audit Reconciliation Addendum

Date: 2026-06-17
Prior baseline: MU and VRT present through merged/overlay stages; FIS present in merged state with overlay working-set nuance.

## Re-check Findings

1. MU
- Present in current merged signal snapshot as STARMINE_COVERED from intake-20260617-060959-starmine.
- Still appears in stale warning examples from old warning artifact.

2. VRT
- Present in current merged signal snapshot as STARMINE_COVERED from intake-20260617-060959-starmine.
- Still appears in stale warning examples from old warning artifact.

3. FIS
- Present in current merged signal snapshot as STARMINE_COVERED from intake-20260617-060959-starmine.
- Overlay context remains dependent on latest PAR working set and symbol applicability; no evidence that warning-layer staleness resolved this nuance.

4. Warning artifact status
- ess_coverage_warning.json remains stale (mtime predates reprocess merge) and retains legacy semantics.

## Did Reprocess Change Prior Conclusions?

Short answer: No material change to root conclusions.

- Reprocess successfully regenerated partitions and merged signal state.
- It did not clear dashboard ESS warning because warning artifact used by API/UI was not regenerated in lockstep.
- Therefore, prior forensic conclusion remains valid: symbol presence is not the issue for MU/VRT/FIS; warning-path state and timing are the issue.

## Resolution Status Statement

Did the reprocess resolve anything?
- It resolved merged-state freshness for signal_snapshot.csv.
- It did not resolve warning presentation because warning artifact remained stale.

Are previous findings still valid?
- Yes. Prior findings stand.