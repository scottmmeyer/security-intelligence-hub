# ACTION-LATENCY-01 — PRIM Missed-Trim Escalation Review

## Root Cause / Process Issue

PRIM-like scenarios can be under-escalated when a holding already has active trim intent but remains in a passive review posture while adverse price movement accumulates. Existing SIH output showed reduction-candidate evidence, but there was no explicit display-only latency state to distinguish:

- normal trim candidate
- aging trim signal with no action
- post-signal adverse move requiring explicit operator review

## Why PRIM Is Different From MU

PRIM-like profile (escalate candidate):

- active reduction intent (`TRIM_WATCH` / `SIGNAL_DETERIORATION` / bearish stack)
- no follow-through action observed after signal generation
- large adverse move after trim signal age window

MU-like control profile (no escalation by default):

- conviction-protected label (`CORE_CONVICTION_LEADER` / `HIGH_CONVICTION_ANCHOR`)
- not in active trim-intent path
- down move alone is insufficient for missed-action escalation

## Current Data Feasibility

### Available now (sufficient for initial display-only implementation)

- Trim/reduction intent signals:
  - UCF labels from `ucf_verdicts.json`
  - overlay flags/signals from `security_overlays.csv`
  - CRA categories/source intent from capital source outputs
- Price context:
  - 1D/5D/1M returns and 52W range from `price_context_by_symbol`
- Historical recommendation/action context:
  - first-seen reduction candidates from recommendation lineage candidates
  - action statuses (`FOLLOWED`, `PARTIALLY_FOLLOWED`, `IGNORED`, etc.) from PIS action attribution

### Gaps (known caveats)

- Action attribution is recommendation-centric and does not model explicit operator "mark reviewed" workflow state.
- First-seen date is inferred from recommendation artifacts; quality depends on historical artifact completeness.

## Proposed Display-Only Escalation Model

Status taxonomy:

- `NONE`
- `ACTION_DUE`
- `TRIM_SIGNAL_AGING`
- `MISSED_ACTION_REVIEW`

Primary trigger shape:

- Active reduction intent (trim/watch/bearish deterioration path)
- No acted status after signal
- Signal age >= window (default 7 days)
- Plus adverse move threshold breach for `MISSED_ACTION_REVIEW`:
  - 1D <= -8%
  - 5D <= -10%
  - 1M <= -20%

Governance:

- Display-only/advisory
- No changes to CW-DAS, ESS, CRA ranking, UCF ranking, PAP, replay, or recommendation generation

## What Was Implemented

### New module

- `src/portfolio/action_latency.py`
  - Computes per-symbol display-only action-latency state
  - Uses existing recommendation lineage + action attribution outputs
  - Adds adverse-move trigger evidence

### Runner integration (payload only)

- `src/portfolio/runner.py`
  - Adds `action_latency_by_symbol` to run output payload
  - Adds `action_latency_by_symbol` to loaded historical run payload
  - Uses existing overlays/fidelity/ucf/price context as inputs
  - No ranking/allocation/scoring mutation

### UI integration (portfolio alignment)

- `ui/portfolio_alignment/app.js`
  - Reduction Queue row badge for action-latency status
  - Profile panel block: "Action Latency Review"
  - DIL reduction posture override for:
    - `MISSED_ACTION_REVIEW`
    - `TRIM_SIGNAL_AGING`
    - `ACTION_DUE`

## Files Changed

- `src/portfolio/action_latency.py` (new)
- `src/portfolio/runner.py`
- `ui/portfolio_alignment/app.js`
- `tests/test_action_latency_01.py` (new)

## Tests Run

- `PYTHONPATH=. ./.venv/bin/pytest -q tests/test_action_latency_01.py tests/test_7_5f_deployment_actionability.py tests/test_pis_action_attribution.py`
  - Result: 89 passed
- `node --check ui/outcome_visualization/app.js`
  - Result: pass (no syntax errors)
- `node --check ui/portfolio_alignment/app.js`
  - Existing project-level issue surfaced (`await` usage in non-async context) unrelated to this feature area.

## Confirmation of No Algorithm Changes

No changes were made to:

- scoring models
- allocation/ranking engines
- recommendation generation logic
- CW-DAS
- ESS/Zacks/Danelfin signal pipelines
- CRA queue ordering
- UCF algorithm
- PAP logic
- replay logic

Only additive display/advisory classification and UI rendering were introduced.

## Recommendation: Implement Now vs Defer

Recommendation: Implement now (done) as a display-only escalation layer.

Reasoning:

- Sufficient existing data for a practical first version
- Addresses operator visibility gap for PRIM-like misses
- Preserves governance by avoiding any automatic action or ranking changes

Future enhancement path:

- Add explicit operator review workflow state (`mark reviewed`, `override rationale`, SLA timers)
- Add event-aware post-earnings trigger fields when available
- Add explicit timeline charting of signal age vs drawdown in PIS dashboard
