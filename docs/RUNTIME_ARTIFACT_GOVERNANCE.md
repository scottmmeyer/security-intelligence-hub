# Runtime Artifact Governance

## 1. Runtime Artifact Philosophy

Runtime artifacts are deterministic execution evidence, not disposable noise.
Artifacts that represent historical lineage, validation outcomes, and run-state
truth are preserved as governed records.

## 2. Governed Runtime Directories

- `runs/logs/` for run-level logs.
- `runs/manifests/` for run-level manifest artifacts.
- `runs/stage_manifests/` for per-stage execution manifests.
- `data/history/` for append-only historical publication records.
- `incoming/ess/` for controlled intake evidence used in deterministic runs.

## 3. Append-Only Runtime Evidence Philosophy

- Published runtime evidence is append-only.
- Existing run evidence is not overwritten in place.
- Corrections are represented by new artifacts linked by lineage metadata.

## 4. Manifest Retention Philosophy

- Run manifests and stage manifests are retained as deterministic audit records.
- Manifests are treated as historical truth for what happened during execution.
- Manifest removal is disallowed unless explicitly governed and documented.

## 5. Snapshot Retention Philosophy

- Historical snapshots are immutable publication evidence.
- Snapshot files are never retroactively mutated.
- Any correction requires a new append event with explicit lineage.

## 6. Hygiene Exclusion Rules

The following are never retained as repository evidence:

- `.DS_Store`
- `*.pyc`
- `__pycache__/`
- editor swap files and local temp artifacts

These are local environment noise and must be excluded via `.gitignore`.

## 7. .pyc And Cache Handling

- Python bytecode and cache directories are local-only runtime byproducts.
- Cache pollution must be removed during hygiene hardening.
- Repository policy enforces ignore rules to prevent recurrence.

## 8. Generated Artifact Lineage Philosophy

- Generated runtime artifacts are valid only when they carry deterministic
  lineage context (`run_id`, `snapshot_date`, provider/source provenance).
- Ungoverned helper outputs and unexplained generated files are classified as
  drift and require explicit triage.
- Runtime evidence boundaries are enforced before governance closeout.
