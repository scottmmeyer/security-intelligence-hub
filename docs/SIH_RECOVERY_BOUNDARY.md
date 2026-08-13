# SIH Recovery Boundary

This document records the controlled operational rehydration boundary for the
recovery worktree. It is provenance-only documentation and must not be consumed
as active runtime state, scoring input, or gating configuration.

## Boundary Facts

- `LAST_GIT_VERIFIED_PRE_WIPE_SIH_BASELINE` = `81c0d574d01c3cc6b7bc48f91bd81ee9e4705d73`
- Recovery code status = `VALIDATED_WITH_ENVIRONMENT_GAPS`
- `PRE_WIPE_PRIVATE_HISTORY_GAP` = present and explicit
- `FIRST_POST_RECOVERY_SIH_RUN` = `UNSET`

## Recovery Process Note

During the local rehydration work, transient regenerable scaffolding was briefly
created in the primary worktree and then specifically removed. No pre-existing
user data was removed, no source/config/scoring/runtime logic changes remain,
and the primary worktree returned to a clean state.

## Historical Context Preserved Only

The following symbols are retained only as user-confirmed pre-wipe context:

- VRT
- TSLA
- JBL
- CIEN
- MKSI
- FSLR
- MTZ

Classification: `USER_CONFIRMED_PRE_WIPE`

This context is `HISTORICAL_OPERATOR_CONTEXT`, not `CURRENT_ACTIVE_OPERATOR_STATE`.

## Unavailable Private Originals

The following original artifacts are unavailable from currently known recovery
sources and remain intentionally absent:

- `data/portfolio_ingestion/analysis_runs/PAR-20260530-3A136D4F/holdings.csv`
- `data/operator/portfolio_alignment_state.json`
- `data/operator/cra_draft.json`
- original PIS history partitions
- original replay history partitions
- original analytical-universe history partitions
- original SMR provider capture
- original SPCX provider capture
- original MKSI provider capture
- original Fidelity statement sources not already Git-backed

Classification: `ORIGINAL_NOT_RECOVERED`

## Safe Local Scaffolding

The following runtime surfaces may be created locally without implying recovery
of historical truth:

- `data/current/`
- transient cache directories required by local tooling
- derived indexes and disposable runtime outputs produced by new executions

These must be treated as regenerated runtime artifacts, never as recovered
pre-wipe history.

## Must Remain Absent Unless Separately Approved

- active operator policy state
- CRA draft state
- manual-review blocks
- historical PIS/replay/universe partitions represented as originals
- provider captures represented as originals

## Operational Boundary Rule

Any future post-recovery run must be labeled as new runtime output and must not
be allowed to masquerade as reconstructed private history.