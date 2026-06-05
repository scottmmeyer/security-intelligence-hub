# Phase 23.0C — C2: Strategic Exit

**Status**: COMPLETE  
**Date**: 2026-06-03  
**PAR Run**: PAR-20260603-B66B00E3

## Design

Category 2 (Strategic Exit) is the operator-driven exit designation layer. Unlike signal-based Categories 1, 3, and 4 which derive from analytical pipeline data, Category 2 is manually curated by the portfolio operator.

**Use case**: Holdings where the decision to exit is driven by non-quantitative factors — relationship changes, portfolio strategy shifts, concentration reduction mandates, or events not captured by the ESS pipeline.

## Implementation

### Server-Side (`run_outcome_ui.py`)

Two new API endpoints:

**GET `/api/operator/strategic-exits`**  
Returns: `{"strategic_exit_symbols": ["FIS", ...]}`  
Reads from `data/operator/portfolio_alignment_state.json`.

**POST `/api/operator/strategic-exits`**  
Body: `{"action": "add"|"remove", "symbol": "XYZ"}`  
- Validates symbol with `_SYMBOL_RE` pattern
- Merges change into state file
- Returns updated list: `{"ok": true, "strategic_exit_symbols": [...]}`

### Client-Side (`app.js`)

State variable: `let _strategicExitSymbols = [];`  
Loaded at boot via `loadStrategicExits()` (called in `DOMContentLoaded`).

Functions:
- `loadStrategicExits()` — GET from API, populate state + render chips
- `addStrategicExit()` — validates input, POST add, re-render pipeline
- `removeStrategicExit(sym)` — POST remove, re-render pipeline
- `_renderStrategicExitList()` — renders symbol chips in `id="strategicExitList"`

**Re-render on change**: Both add and remove re-call `renderPortfolioActionPipeline(_analysisResult)` if analysis is loaded — so Cat 2 table updates in real time.

### UI: Strategic Exit Manager

Always visible in Cat 2 body (even when no exits are designated):
- Chip list of current symbols with ✕ remove buttons
- Text input + Add button for new symbols
- Status message display (ok/warn/error)

## Persistence

State stored in `data/operator/portfolio_alignment_state.json` under key `strategic_exit_symbols`.  
Survives server restarts. Seeded with `["FIS"]` for initial validation.

## Validation

- FIS appears in Cat 2 with priority HIGH ✓
- FIS also appears in Cat 4 as cross-reference (funding_reason="Signal Deterioration" if Cat1, else "Low Conviction") ✓
- Add/remove updates the list live ✓
- Invalid symbols rejected ✓
