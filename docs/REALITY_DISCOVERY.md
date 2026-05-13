# Reality Discovery

## Historical Context Notice

This document is a forensic snapshot for the first controlled real-ingestion
attempt on 2026-05-13 (run 001) before provider-native adapter hardening was
completed.

- It should be interpreted as historical evidence, not as the current runtime
  operating baseline.
- Current governed runtime behavior and storage contracts are defined by
  WP-03.4 implementation, partitioned history paths, and persistence
  verification controls.

## Execution Context

- Discovery date: 2026-05-13
- Trigger: First controlled real ESS ingestion execution
- Baseline dirty inventory source: `git status --short --untracked-files=all`
- Baseline dirty count: 71 paths

## Classification Framework

Each dirty path was classified into exactly one category:

1. `EXPECTED_GENERATED`
2. `RUNTIME_ARTIFACT`
3. `GOVERNANCE_UPDATE`
4. `HYGIENE_VIOLATION`
5. `UNEXPECTED_DIRTY`

## Classification Summary

- `EXPECTED_GENERATED`: 0
- `RUNTIME_ARTIFACT`: 7
- `GOVERNANCE_UPDATE`: 11
- `HYGIENE_VIOLATION`: 48
- `UNEXPECTED_DIRTY`: 5

## Post-Cleanup Working-Tree Classification (Current)

Current working-tree inventory after hygiene hardening: 30 paths.

- `HYGIENE_VIOLATION`: 4
- `RUNTIME_ARTIFACT`: 7
- `GOVERNANCE_UPDATE`: 14
- `UNEXPECTED_DIRTY`: 5
- `EXPECTED_GENERATED`: 0

Current `HYGIENE_VIOLATION` entries are deliberate staged deletions of
historically tracked `.DS_Store` files:

- `data/.DS_Store`
- `incoming/.DS_Store`
- `incoming/ess/.DS_Store`
- `src/.DS_Store`

## Runtime Artifact Observations

- Run-level evidence was generated under governed paths in `runs/`.
- Stage-level evidence was generated under `runs/stage_manifests/`.
- Intake evidence for the controlled run exists under `incoming/ess/`.
- Runtime evidence behavior aligns with append-only lineage expectations.

## Manifest Generation Behavior

- Controlled run generated a run log, run manifest, validation report, and stage
  manifests.
- Manifest behavior is deterministic and auditable.
- No evidence suggests runtime orchestration drift in artifact placement.

## Runtime Evidence Boundaries

Preserved runtime evidence is constrained to governed directories and includes:

- `incoming/ess/non_starmine_zacks/starmine_zacks.csv`
- `incoming/ess/starmine/SecurityExtract_ESS_2026May13.csv`
- `runs/logs/RUN-REAL-ESS-20260513-001.log`
- `runs/manifests/RUN-REAL-ESS-20260513-001_manifest.json`
- `runs/manifests/RUN-REAL-ESS-20260513-001_validation_report.json`
- `runs/stage_manifests/RUN-REAL-ESS-20260513-001_benchmark_validation.json`
- `runs/stage_manifests/RUN-REAL-ESS-20260513-001_ess_intake.json`

## Repository Governance Observations

- Hygiene violations were heavily concentrated in `.DS_Store`, `*.pyc`, and
  `__pycache__/` pollution.
- `.gitignore` did not exist and allowed local runtime/editor byproducts to
  appear as workspace drift.
- Controlled runtime evidence remained separable from hygiene pollution.

## .gitignore Hardening Applied

Added repository-level `.gitignore` rules for:

- `__pycache__/`
- `*.pyc`
- `.DS_Store`
- local temp and editor cache artifacts

Governed runtime evidence directories (`runs/`, `incoming/ess/`, `data/history/`)
were intentionally not ignored.

## Hygiene Lessons Learned

- Append-only evidence preservation and hygiene cleanup must be decoupled.
- Deterministic classification before cleanup prevents accidental evidence loss.
- Runtime artifact governance must be explicit and versioned.

## Full Baseline Classification (All Dirty Paths)

### GOVERNANCE_UPDATE

- `master_plan.md`
- `navigation_state.yaml`
- `wdd_log.md`
- `docs/ARCHITECTURE_CONSISTENCY_CHECKLIST.md`
- `docs/CANONICAL_TERMINOLOGY.md`
- `docs/PROVIDER_LINEAGE_PHILOSOPHY.md`
- `docs/SECURITY_IDENTITY_PHILOSOPHY.md`
- `docs/SNAPSHOT_CONSISTENCY_RULES.md`
- `docs/TEMPORAL_INTEGRITY_PHILOSOPHY.md`
- `scripts/validate_architecture_consistency.py`
- `tests/test_architecture_consistency_validator.py`

### RUNTIME_ARTIFACT

- `incoming/ess/non_starmine_zacks/starmine_zacks.csv`
- `incoming/ess/starmine/SecurityExtract_ESS_2026May13.csv`
- `runs/logs/RUN-REAL-ESS-20260513-001.log`
- `runs/manifests/RUN-REAL-ESS-20260513-001_manifest.json`
- `runs/manifests/RUN-REAL-ESS-20260513-001_validation_report.json`
- `runs/stage_manifests/RUN-REAL-ESS-20260513-001_benchmark_validation.json`
- `runs/stage_manifests/RUN-REAL-ESS-20260513-001_ess_intake.json`

### UNEXPECTED_DIRTY

- three legacy root-level helper artifacts (resolved in final helper drift pass)
- `run_pipeline.py`
- `run_pipeline_ess.py`

### HYGIENE_VIOLATION

- `data/.DS_Store`
- `incoming/.DS_Store`
- `incoming/ess/.DS_Store`
- `src/.DS_Store`
- `.DS_Store`
- `data/history/.DS_Store`
- `incoming/ess/starmine/.DS_Store`
- `runs/.DS_Store`
- `src/models/.DS_Store`
- `src/normalize/.DS_Store`
- `src/pipeline/.DS_Store`
- `src/validation/.DS_Store`
- `tests/.DS_Store`
- `scripts/__pycache__/validate_architecture_consistency.cpython-314.pyc`
- `src/__pycache__/__init__.cpython-314.pyc`
- `src/__pycache__/__init__.cpython-39.pyc`
- `src/history/__pycache__/__init__.cpython-39.pyc`
- `src/history/__pycache__/signal_snapshot_manager.cpython-39.pyc`
- `src/models/__pycache__/__init__.cpython-314.pyc`
- `src/models/__pycache__/__init__.cpython-39.pyc`
- `src/models/__pycache__/canonical_models.cpython-314.pyc`
- `src/models/__pycache__/canonical_models.cpython-39.pyc`
- `src/models/__pycache__/pipeline_models.cpython-314.pyc`
- `src/models/__pycache__/pipeline_models.cpython-39.pyc`
- `src/models/__pycache__/run_metadata.cpython-314.pyc`
- `src/models/__pycache__/run_metadata.cpython-39.pyc`
- `src/normalize/__pycache__/__init__.cpython-39.pyc`
- `src/normalize/__pycache__/ess_normalizer.cpython-39.pyc`
- `src/normalize/__pycache__/market_cap_normalizer.cpython-39.pyc`
- `src/pipeline/__pycache__/__init__.cpython-314.pyc`
- `src/pipeline/__pycache__/__init__.cpython-39.pyc`
- `src/pipeline/__pycache__/execution_summary.cpython-314.pyc`
- `src/pipeline/__pycache__/execution_summary.cpython-39.pyc`
- `src/pipeline/__pycache__/pipeline_runner.cpython-314.pyc`
- `src/pipeline/__pycache__/pipeline_runner.cpython-39.pyc`
- `src/pipeline/__pycache__/stage_registry.cpython-314.pyc`
- `src/pipeline/__pycache__/stage_registry.cpython-39.pyc`
- `src/pipeline/stages/__pycache__/__init__.cpython-39.pyc`
- `src/pipeline/stages/__pycache__/ess_intake_stage.cpython-39.pyc`
- `src/validation/__pycache__/__init__.cpython-39.pyc`
- `src/validation/__pycache__/benchmark_validator.cpython-39.pyc`
- `src/validation/__pycache__/ess_validator.cpython-39.pyc`
- `src/validation/__pycache__/market_cap_validator.cpython-39.pyc`
- `tests/__pycache__/test_architecture_consistency_validator.cpython-314-pytest-8.3.5.pyc`
- `tests/__pycache__/test_benchmark_foundation.cpython-39-pytest-8.4.1.pyc`
- `tests/__pycache__/test_ess_intake_foundation.cpython-39-pytest-8.4.1.pyc`
- `tests/__pycache__/test_market_cap_classification.cpython-39-pytest-8.4.1.pyc`
- `tests/__pycache__/test_pipeline_observability.cpython-39-pytest-8.4.1.pyc`

### EXPECTED_GENERATED

- none in this baseline inventory

## Cleanup Actions Applied

- Removed all baseline `HYGIENE_VIOLATION` paths listed above.
- Preserved all `RUNTIME_ARTIFACT` paths for historical evidence.
- Preserved `UNEXPECTED_DIRTY` paths for explicit follow-up triage.

## Unexplained Drift Findings

The following files remain unexplained by current waypoint scope and require
intent confirmation before commit:

- three legacy root-level helper artifacts (resolved in final helper drift pass)
- `run_pipeline.py`
- `run_pipeline_ess.py`

## Final Controlled Cleanup Summary (WP-03.1)

- Hygiene cleanup was executed only after deterministic per-file classification.
- Runtime evidence under governed directories was preserved unchanged.
- Historically tracked `.DS_Store` files were converted into explicit staged
  deletions for hygiene enforcement.
- `.gitignore` hardening was applied to prevent future cache/bytecode metadata
  pollution from entering dirty-state governance flows.

## Governed Staging Summary (WP-03.1)

Staged scope is constrained to:

- governance and documentation updates,
- runtime governance artifacts,
- approved runtime evidence,
- hygiene-governance deletions.

Excluded scope is constrained to unresolved operational drift artifacts pending
formal review.

## Unresolved Drift Preservation Rationale

- Unexplained files were not deleted to preserve operational traceability.
- Unexplained files were not staged to preserve architectural trust boundaries.
- Triage deferral is intentional until architectural domain ownership and risk
  posture are explicitly confirmed.

## Additional Operational Lessons Learned

- A clean repository is not the primary objective; controlled evidence is.
- Runtime evidence and hygiene artifacts must be governed by separate policies.
- Staging boundaries are as important as cleanup boundaries for deterministic
  SDLC control.

## Runtime Governance Outcome

- Runtime artifact generation is now documented and bounded by policy.
- Hygiene policy is codified through ignore controls and explicit removal rules.
- Unresolved drift remains visible, isolated, and reviewable.

## ESS Processing Output Verification

### Verification Conclusion

Conclusion: **C. REAL ESS PROCESSING PARTIALLY OCCURRED**.

What executed:

- ESS input files were discovered from configured intake lanes.
- CSV files were opened and rows were loaded.
- Fail-closed validation executed and produced explicit errors.

What did not execute:

- Canonical normalization did not complete for any row.
- Snapshot append did not execute for any row.
- History and lineage artifact registration did not occur for ESS stage output.

Root cause of stop condition:

- Incoming provider exports do not satisfy required canonical ESS columns
  (`snapshot_date`, `provider`, `source_file`, and universe-specific fields).
- Validation failed on required-column checks and row-level canonical field
  checks, blocking normalization and append operations by design.

### Deterministic Evidence

- Run status: `FAILED`
- Stage status: `benchmark_validation=COMPLETE`, `ess_intake=FAILED`
- Run error count: `9893`
- Input row counts observed by validation report:
  - starmine: `2473`
  - non_starmine_zacks: `368`
- Snapshot rows appended: `0`
- Snapshot rows after run: `0`

### Artifact Output Table

| Artifact | Expected Path | Exists? | Row Count | Produced By Stage | Notes |
| --- | --- | --- | --- | --- | --- |
| Raw incoming StarMine file | `incoming/ess/starmine/SecurityExtract_ESS_2026May13.csv` | Yes | 2473 | External input | Discovered and opened by ESS intake stage. |
| Raw incoming non-StarMine file | `incoming/ess/non_starmine_zacks/starmine_zacks.csv` | Yes | 368 | External input | Discovered and opened by ESS intake stage. |
| Validation report | `runs/manifests/RUN-REAL-ESS-20260513-001_validation_report.json` | Yes | N/A | Post-run synthesis | Captures category counts, row counts, append blocked evidence. |
| Normalized ESS output (file) | `N/A (in-memory only if validation passes)` | No | 0 | `ess_intake` | No normalized artifact file is implemented in current stage path. |
| Signal snapshot output | `data/history/signals/signal_snapshots.csv` | Yes | 0 data rows (header only) | `ess_intake` append path | Append blocked by fail-closed validation failure. |
| Signal snapshot history | `data/history/signals/signal_snapshot_history.csv` | Yes | 0 data rows (header only) | `ess_intake` append path | No append events written due validation failure. |
| Lineage registry | `data/history/signals/signal_lineage_registry.csv` | Yes | 0 data rows (header only) | `ess_intake` append path | No lineage rows written due validation failure. |
| Run manifest | `runs/manifests/RUN-REAL-ESS-20260513-001_manifest.json` | Yes | N/A | `pipeline_runner` | Records failed run and aggregated errors. |
| ESS stage manifest | `runs/stage_manifests/RUN-REAL-ESS-20260513-001_ess_intake.json` | Yes | N/A | `pipeline_runner` + `ess_intake` output | Contains explicit validation errors; `artifacts_created=[]`. |

### Dirty-File Status At Verification Time

- Current dirty file count: `32`
- Composition at investigation close:
  - governed staged changes and runtime evidence: `27`
  - unresolved unexpected drift (unstaged): `5`

### Recommended Remediation

- Add deterministic provider-export-to-canonical ESS adapter/mapping step before
  strict canonical validation.
- Keep fail-closed validator unchanged.
- Re-run controlled ESS ingestion after adapter introduction and verify
  non-zero `ess_rows_normalized` and `ess_rows_appended`.

## Fidelity Provider Mapping Findings

### Observed Fidelity Provider-Native Columns

Actual observed Fidelity columns include:

- `Symbol`
- `Company Name`
- `Security Type`
- `Security Price`
- `Equity Summary Score (ESS) from LSEG StarMine`
- `Forward EPS Long Term Growth (3-5 Yrs)`
- `Market Capitalization`
- `Jefferson Research`
- `Zacks Investment Research`
- `McLean Capital Management`

### Deterministic Mapping Behavior

- Provider-native columns are parsed by a Fidelity adapter layer.
- Canonical mapping occurs as a separate step after provider parsing.
- Mapping lineage preserves canonical target to provider-column origin.
- Unmapped provider columns are surfaced explicitly in stage warnings,
  validation summaries, and base-universe lineage registry metadata.

### Normalization Behavior

- Fidelity ESS text categories are normalized into canonical ESS tokens.
- Market-cap provider-native values are parsed from suffix forms (for example
  `$1.74B`, `$933.58M`) into integer USD for canonical bucketing.
- Coverage domain assignment remains deterministic through configured
  universe-to-domain mappings.

### Rejected Row Behavior

- Malformed ESS categories are fail-closed.
- Invalid market-cap values are fail-closed.
- Duplicate symbols within the same provider file are deterministically skipped
  after first-seen selection and surfaced in warnings/row accounting.
- Provider footer and notice rows with non-ticker symbols are deterministically
  classified as non-data and surfaced in warnings/row accounting.
- Missing required provider-native columns are fail-closed.

### Base Universe Outputs Generated

WP-03.2 now defines and populates canonical base-universe outputs under:

- `data/derived/base_universe/base_equity_universe.csv`
- `data/derived/base_universe/base_equity_universe_history.csv`
- `data/derived/base_universe/universe_lineage_registry.csv`

These outputs are append-only and preserve run lineage, provider lineage, and
provider-column mapping visibility.
