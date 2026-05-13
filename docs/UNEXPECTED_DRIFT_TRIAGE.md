# Unexpected Drift Triage

## Purpose

Document unresolved operational drift artifacts that were intentionally excluded
from governed WP-03.1 staging pending formal architectural review.

## Triage Policy

- Files in this document remain preserved for traceability.
- Files in this document are excluded from governed staging.
- No normalization, deletion, or promotion occurs without explicit review.

## Drift Items

### 1. Legacy Root Helper Artifact Cluster

- Observed purpose (inferable): Ad hoc root-level diagnostics with unclear
  governance ownership.
- Why classified as unexpected: Not registered under governed script policy and
  outside canonical tooling paths.
- Potential architectural domain: Operational diagnostics.
- Operational risk assessment: Low to Medium.
  Root-level helper drift can bypass deterministic review boundaries.
- Final disposition status:
  Resolved. Reusable read-only diagnostics were moved to scripts/diagnostics,
  and scratch/corrupted helpers were removed.

### 2. run_pipeline.py

- Filename: `run_pipeline.py`
- Observed purpose (inferable): Local pipeline run launcher/helper.
- Why classified as unexpected: Execution entrypoint not yet referenced by
  active governance artifacts for WP-03.1 closeout.
- Potential architectural domain: Runtime execution interface.
- Operational risk assessment: Medium.
  Ungoverned execution entrypoints can create non-deterministic run paths.
- Recommended future disposition:
  Review against canonical runner boundaries; if approved, document and test as
  governed entrypoint, else deprecate/remove.

### 3. run_pipeline_ess.py

- Filename: `run_pipeline_ess.py`
- Observed purpose (inferable): ESS-focused pipeline run launcher/helper.
- Why classified as unexpected: Not currently declared in governance contracts
  as a sanctioned runtime entrypoint.
- Potential architectural domain: Runtime execution interface.
- Operational risk assessment: Medium.
  Specialized entrypoints can diverge from canonical control-plane behavior.
- Recommended future disposition:
  Require architectural review for runner parity and deterministic boundary
  compliance; then either promote with documentation or remove.

## Deferred Triage Rationale

These files were intentionally isolated because purpose, ownership, and
architectural trust boundary were not formally validated within WP-03.1 scope.
