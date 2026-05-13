# Artifact Registry Philosophy

## Artifacts as Historical Evidence

Artifacts are evidence that a pipeline stage produced deterministic outputs.
Each artifact record is tied to run lineage and stage provenance.

## Deterministic Outputs

- Identical inputs and contracts must produce equivalent artifact records.
- Artifact naming and paths are explicit and reviewable.
- Placeholder checksums are supported until checksum generation is implemented.

## Immutable Run Evidence

- Run manifests and artifact records are append-oriented historical evidence.
- Evidence is never rewritten in-place after publication.
- Corrections are captured as new run artifacts with new run_id values.

## Reproducibility Philosophy

- Artifact metadata preserves source paths and producing stages.
- Validation summaries document quality state at production time.
- Reproducibility is grounded in explicit manifests, not operator memory.

## Lineage Tracking

- artifact_name and artifact_path identify what was produced.
- producing_stage identifies where it was produced.
- lineage_notes preserve deterministic context for future audits.

## Future ML Traceability Requirements

- ML datasets must be derivable from lineage-backed artifacts only.
- Training and evaluation runs must reference immutable run evidence.
- Snapshot and artifact lineage must remain point-in-time consistent.