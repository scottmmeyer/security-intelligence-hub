# ATTRIBUTION METHODOLOGY ASSESSMENT
**Date:** 2026-06-12
**Purpose:** Feasibility assessment of attribution methods for SIH

## Executive Assessment

SIH can do useful attribution with existing data, but only some forms are sufficiently accurate for operator-facing display.

Best-fit model for Phase 1:
- portfolio return for short windows: approximate internally
- long-window portfolio return: Fidelity-reported
- contribution analysis: Weight × Security Return
- benchmark comparison: S&P 500 primary, Total Market secondary, ACWI reference

## Method Options

### Option A: Fidelity-calculated returns
Best for:
- 3M
- YTD
- 1Y
- 3Y
- 5Y

Pros:
- authoritative calculations
- accounts for cash flows, dividends, and corporate actions
- operationally realistic because Fidelity already computes it

Cons:
- SIH cannot yet ingest the full performance report automatically
- depends on operator input or export availability

Verdict:
- recommended as source of truth for long windows

### Option B: Internal return reconstruction
Inputs:
- holdings snapshots
- security return series
- transaction history
- dividends
- deposits and withdrawals

Pros:
- fully under SIH control
- supports deeper analysis later
- can be automated over time

Cons:
- materially more complex
- needs cash-flow normalization
- requires consistent daily history to be accurate over long windows

Verdict:
- feasible later, but not the best Phase 1 source of truth

### Option C: Weight × Return approximation
Formula:
- Contribution = Weight × Security Return

Inputs already present in SIH:
- `percent_of_portfolio`
- short-window security returns from price context

Pros:
- simple
- explainable
- enough for contributor/detractor views
- operationally realistic today

Cons:
- approximate only
- does not fully normalize for intra-period trades, dividends, and cash flows

Verdict:
- best fit for display-only contribution analysis in Phase 1

## Required Data by Use Case

### Contribution to return
Minimum required data:
- end-of-period weight or beginning-of-period weight proxy
- security return for the same window

Recommended method:
- Weight × Return

### Trade attribution
Minimum required data:
- cost basis
- quantity
- current price
- approximate entry date or transaction history

Recommended method:
- phase 1: cost-basis-based return since entry
- phase 2: transaction-aware return decomposition

### Allocation attribution
Minimum required data:
- portfolio weights by node
- benchmark weights by node
- benchmark returns by node or sector

Recommended method:
- phase 1: directional allocation impact with simplified weighting
- phase 2: full Brinson-Fachler attribution

## Accuracy Ranking

1. Fidelity-calculated returns for long windows
2. Internal short-window Weight × Return estimates
3. Transaction-aware reconstruction with normalized flows

## Operational Recommendation

Do not replace Fidelity for audited portfolio return numbers.
Use SIH to explain the drivers and decision outcomes around those numbers.
