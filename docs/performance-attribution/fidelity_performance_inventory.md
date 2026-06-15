# FIDELITY PERFORMANCE INVENTORY
**Date:** 2026-06-12
**Purpose:** Inventory of Fidelity return and attribution inputs relevant to SIH

## What Fidelity already provides

### 1) Portfolio Performance View
Fidelity's account performance page provides portfolio returns by time window.

Observed/expected return windows:
- 1D
- 5D
- 1M
- 3M
- YTD
- 1Y
- 3Y
- 5Y
- Since inception

Typical location in Fidelity UI:
- Accounts
- Performance
- Select account
- Choose time period

Accessibility:
- Visible in the Fidelity web UI to the operator
- Not currently machine-ingested by SIH
- Can be captured manually or via export if Fidelity offers a downloadable performance report in the current account setup

Automation feasibility:
- Manual entry: high feasibility, low complexity
- CSV ingestion: medium feasibility, depends on Fidelity export format stability
- Browser automation: low-to-medium feasibility and brittle

### 2) Portfolio Position Export
Fidelity's position export is already usable in SIH via `incoming/portfolio/`.

Useful fields:
- Symbol
- Current Value
- Today's Gain/Loss Dollar
- Today's Gain/Loss Percent
- Total Gain/Loss Dollar
- Total Gain/Loss Percent
- Cost Basis Total
- Percent Of Account
- Quantity

What it can support:
- 1D contribution
- approximate short-window return attribution
- trade return since entry basis

What it cannot support:
- authoritative 3M/YTD/1Y portfolio returns
- benchmark comparison
- full transaction-aware attribution

### 3) Transaction History
Fidelity can provide transaction history exports with buys, sells, dividends, splits, and other corporate actions.

Automation feasibility:
- Useful for future phase-2 trade attribution
- Not required for initial display-only dashboard
- Higher ingestion complexity than position export or performance page capture

### 4) Benchmark Views
Fidelity performance views already include benchmark comparison options such as:
- S&P 500
- Total Market
- ACWI ex-US

Automation feasibility:
- Good as a human-readable source of truth
- Better as a validation source than as the primary SIH benchmark model

## Recommendation from the inventory

- Use Fidelity as the authoritative source for long-window portfolio returns.
- Use SIH internal computation for short-window approximation and contribution analysis.
- Treat Fidelity export and performance views as complementary inputs, not competing systems.
