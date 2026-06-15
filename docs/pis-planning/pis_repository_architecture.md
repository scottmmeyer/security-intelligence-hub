# PIS Repository Architecture
**Date:** 2026-06-12

## Decision

Keep PIS inside the existing `security-intelligence-hub` repository.

This is the correct decision today because:
- PIS depends on SIH recommendation history, benchmark history, run metadata, and portfolio analysis outputs.
- The data contracts, lineage rules, and storage conventions already exist in this repository.
- The separation needed is architectural and namespace-based, not repository-based.

## Recommended Top-Level Structure

```text
src/
  sih/
    ... existing SIH intelligence and recommendation code ...
  pis/
    models/
    ingestion/
    change_detection/
    lineage/
    reconciliation/
    benchmark/
    outcome/
    services/
    validation/

ui/
  sih/
    ... existing SIH UI surfaces ...
  pis/
    ... future PIS UI surfaces ...

tests/
  sih/
    ... existing SIH tests ...
  pis/
    ... future PIS tests ...

docs/
  sih/
    ... existing SIH architecture and governance docs ...
  pis/
    ... PIS architecture and planning docs ...

data/
  current/
  history/
    pis/
```

## Ownership Boundaries

### SIH namespace
Responsible for:
- intelligence generation
- scoring
- recommendations
- benchmark history generation
- portfolio analysis outputs that feed PIS

### PIS namespace
Responsible for:
- portfolio snapshots
- change detection
- decision lineage
- reconciliation queue
- portfolio outcome explanation
- benchmark comparison display logic

### Shared utilities
Shared code should be limited to truly reusable primitives such as:
- CSV / snapshot validation helpers
- immutable run metadata contracts
- generic lineage and persistence helpers
- benchmark history provider interfaces
- common dataclass / schema helpers

## Shared Models

Recommended shared contracts:
- run metadata
- immutable snapshot metadata
- benchmark history row contracts
- generic lineage record contracts

Recommended PIS-specific contracts:
- portfolio snapshot
- position snapshot
- change event
- lineage match record
- unresolved event record

## Shared Storage

Use a shared platform storage root, but isolate the PIS partition tree:
- SIH historical data stays in existing SIH paths
- PIS historical data lives under `data/history/pis/`

## Design Principle

PIS should be structurally easy to extract later, but not prematurely separated into another repository before its contracts stabilize.
