# PIS-004A Governance Design and Implementation

## Scope
Stage A establishes snapshot governance only.

Included:
- Deterministic snapshot governance classification
- Governance persistence output
- Governance API endpoints
- Governance dashboard section
- Deterministic test coverage and regression verification

Excluded:
- Canonical daily snapshot selection (Stage B)
- Change detection recomputation
- Lineage recomputation
- Historical data mutation

## Architecture
### Governance engine
New module: src/pis/governance.py

Core responsibilities:
- Evaluate account scope
- Evaluate portfolio value sanity
- Evaluate source lineage quality
- Return deterministic governance verdict

Evaluation output contract:
- status: PASS or WARNING or REJECT
- reasons: list of deterministic reason codes
- scope_valid: boolean
- value_valid: boolean
- source_valid: boolean

### Persistence
Output path:
- data/history/pis/governance/snapshot_governance.csv

Output schema:
- snapshot_id
- snapshot_date
- governance_status
- reasons
- scope_valid
- value_valid
- source_valid

### APIs
Added:
- /api/pis/governance/latest
- /api/pis/governance-summary

Behavior:
- Endpoints compute governance from snapshot index deterministically
- Endpoints persist latest governance CSV output
- Endpoints do not alter historical snapshot partitions

### Dashboard
Updated PIS dashboard to include Section 6: Snapshot Governance.

Displays:
- PASS count
- WARNING count
- REJECT count
- snapshots evaluated
- detailed snapshot governance table

## Determinism and Priority Model
Rule precedence:
1. REJECT when account scope invalid or reject-value threshold exceeded
2. WARNING when warning-band value or source artifact is present and no reject condition exists
3. PASS when all checks are clean

Reason codes are stable and machine-readable.

## Configurability
Governance settings are centralized in SnapshotGovernanceConfig, including:
- expected account scope tokens
- disallowed account class tokens
- value warning and reject thresholds
- known source artifact patterns

## Implementation Summary
Implemented files:
- src/pis/governance.py
- scripts/run_outcome_ui.py
- ui/pis_dashboard/index.html
- ui/pis_dashboard/app.js
- tests/test_pis_governance_stage_a.py
- tests/test_pis_ui_phase1_dashboard.py
