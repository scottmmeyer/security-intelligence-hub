# REFRESH-HEALTH-02A Part C - Intake Area Architecture Assessment

Date: 2026-06-17
Scope: incoming/ hierarchy behavior and ownership boundaries

## Architectural Intent (Observed in Code)

From src/validation/intake_readiness_validator.py and src/pipeline/stages/ess_intake_stage.py:
- Intake discovery reads only:
  - incoming/ess/starmine
  - incoming/ess/non_starmine_zacks
- Intake stage processes discovered CSV files and then unlinks them from those folders.
- No stage logic writes working files or archive folders under incoming/ess.

This is source-staging semantics.

## Classification Against Requested Modes

A) Source-only staging area
- Best match to current coded contract.

B) Source + working area
- Not supported by pipeline code.

C) Source + archive + working area
- Not supported by pipeline code; only observed via ad-hoc manual operations.

## Mixing Assessment

Current observed state includes operator source folders plus manual archive/working additions:
- Source folders: starmine, non_starmine_zacks
- Manual/operational additions: _holding, processed

This is an unmanaged mix from architecture perspective, not a declared design.

## Assessment Answers

1. Should incoming remain operator-managed and source-only?
- Yes. This matches deterministic intake readiness and cleanup behavior already implemented.

2. Should _holding or processed live elsewhere?
- Yes, if retained operationally, they should be moved outside incoming/ess source contract (for example data/ops/ingest_staging or data/history/ingest_archive) to avoid source-area ambiguity.

## Contamination Determination

Intake-area contamination status: Present.
- Reason: non-contract folders were introduced in the source staging tree and can confuse operational expectations, even if current intake code ignores them.

## Risk Notes

- Immediate parser risk is low because discovery is constrained to file-level CSV scans in the two configured source dirs.
- Operational risk is moderate: humans may assume processed/_holding are official parts of ingestion behavior, causing inconsistent re-stage/refresh practices.

## Part C Conclusion

The intended architecture is source-only staging for incoming/ess. The new _holding and processed folders represent operational overlay behavior, not formal pipeline architecture, and should be treated as out-of-contract additions.