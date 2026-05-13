# Unexpected Drift Triage

## Purpose

Document unresolved operational drift artifacts that were intentionally excluded
from governed WP-03.1 staging pending formal architectural review.

## Triage Policy

- Files in this document remain preserved for traceability.
- Files in this document are excluded from governed staging.
- No normalization, deletion, or promotion occurs without explicit review.

## Drift Items

### 1. iecho

- Filename: `iecho`
- Observed purpose (inferable): Unknown executable or helper artifact.
- Why classified as unexpected: Not referenced by governance docs, pipeline
  contracts, or waypoint deliverables.
- Potential architectural domain: Unknown / operational tooling.
- Operational risk assessment: Medium.
  Unknown binary/script behavior and provenance can bypass deterministic SDLC
  controls.
- Recommended future disposition:
  Perform explicit provenance and content inspection; if legitimate, relocate to
  a governed tooling path with documentation and tests, otherwise remove.

### 2. inspect_ess.py

- Filename: `inspect_ess.py`
- Observed purpose (inferable): Ad hoc ESS inspection helper.
- Why classified as unexpected: Not part of documented pipeline/stage runtime
  contracts and no governance registration.
- Potential architectural domain: Operational diagnostics.
- Operational risk assessment: Low to Medium.
  Useful for diagnostics but can drift into undocumented runtime behavior.
- Recommended future disposition:
  Either formalize under governed scripts/docs as read-only diagnostics or
  archive/remove after triage.

### 3. inspect_ess_csvs.py

- Filename: `inspect_ess_csvs.py`
- Observed purpose (inferable): Batch CSV inspection helper for ESS inputs.
- Why classified as unexpected: Undocumented helper outside current waypoint
  contract scope.
- Potential architectural domain: Operational diagnostics.
- Operational risk assessment: Low to Medium.
  Similar risk to other ad hoc helpers if used in production flows.
- Recommended future disposition:
  Consolidate with diagnostic tooling policy and add explicit usage boundary;
  otherwise remove.

### 4. run_pipeline.py

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

### 5. run_pipeline_ess.py

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
