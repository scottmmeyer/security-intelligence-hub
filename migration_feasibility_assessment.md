# Migration Feasibility Assessment

## Scope
Assess whether Portfolio Manager historical snapshots can be imported into PIS using current contracts.

## Feasibility Verdict
Feasible with high confidence for PIS Phase 1 objectives.

## Evidence
- Canonical PM artifacts already exist per run (snapshot.json + holdings.csv).
- Canonical PIS registration service exists and consumes canonical SIH snapshot/holding objects.
- Snapshot identity deduplication semantics are already implemented in PIS append-only storage.

## Compatibility Findings
- Required PIS Phase 1 fields are available from PM artifacts and map cleanly.
- PM has additional analytics fields that current PIS storage does not persist.
- Raw Fidelity gain/loss columns exist in archive uploads but are not carried through PM canonical holdings.csv.

## Risks
1. Malformed snapshot_date values in a small number of runs (observed: 2 runs, 1 unique snapshot identity).
2. Large rerun duplication volume requires identity-level deduplication to avoid inflation.
3. Potential expectations mismatch around gain/loss if users assume those raw fidelity columns are in canonical PM holdings.

## Controls
- Enforce snapshot_id deduplication.
- Validate snapshot_date format during migration and report invalid runs.
- Keep migration reporting explicit: registered, duplicate, invalid, failed.

## Direct Answers
- Can PM historical snapshots be mapped into current PIS schema without loss?
  - Without loss for PIS Phase 1 required fields: yes.
  - Without loss for all PM enriched fields/raw gain-loss columns: no (schema extension required).
- Which PM fields are not yet in PIS?
  - Classification, provider-score, and decomposition fields listed in portfolio_manager_to_pis_mapping.md.
- Which PIS fields are not in PM by name?
  - account_id, snapshot_id, percent_of_account, source_percent_of_account, cost_basis_total (mapped transforms).
