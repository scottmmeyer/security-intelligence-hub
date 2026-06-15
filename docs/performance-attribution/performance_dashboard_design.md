# PERFORMANCE DASHBOARD DESIGN
**Date:** 2026-06-12
**Purpose:** Proposed UI layout for portfolio performance attribution in SIH

## Design Principles

- Display-only, explanatory, and operator-facing
- Show outcomes first, then drivers
- Keep fidelity-return numbers and SIH attribution estimates visibly separate
- Use contribution percentages, not raw holding returns, for contributor/detractor panels
- Include explicit benchmark comparison and alpha

## Section A: Portfolio Return

Display the portfolio return across common windows:
- 1D
- 5D
- 1M
- 3M
- YTD
- 1Y

Suggested presentation:
- compact KPI strip
- color-coded positive/negative values
- timestamp for as-of date

## Section B: Benchmark Comparison

Show side-by-side:
- Portfolio
- Benchmark
- Alpha

Example:
- Portfolio: -1.46%
- S&P 500: -1.65%
- Alpha: +0.19%

Recommended benchmark default:
- S&P 500

Secondary benchmark toggle:
- Total Market
- ACWI

## Section C: Top Contributors

Show the holdings that added the most to portfolio return.

Display per row:
- symbol
- contribution %
- optional conviction tag
- optional holding period note

Do not show raw return as the primary column.

## Section D: Top Detractors

Show the holdings that subtracted the most from portfolio return.

Display per row:
- symbol
- contribution %
- optional conviction tag
- optional reduction status
- optional outcome note

## Section E: Allocation Attribution

Show contribution impact from allocation choices such as:
- international overweight
- cash position
- mega-cap underweight
- sector overweights and underweights

Display:
- node
- overweight or underweight amount
- estimated impact
- direction of contribution

This section is explanatory, not an exact institutional Brinson report in Phase 1.

## Section F: Trade Attribution

Show outcome by trade decision.

Examples:
- Bought VRT
- Bought ARW
- Sold VEA

Display:
- since-trade contribution
- outcome label
- contribution impact
- optional holding age or entry basis

## Recommended Layout Order

1. Portfolio return strip
2. Benchmark comparison
3. Top contributors
4. Top detractors
5. Allocation attribution
6. Trade attribution

## UX Notes

- Keep the dashboard readable in one scrollable panel.
- Use a disclaimer banner noting that long-window numbers are Fidelity-reported where applicable.
- Make attribution feel like an explanation of decisions, not a replacement for the decision layer.
