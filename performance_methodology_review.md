# Performance Methodology Review (Fidelity vs SIH)

Date: 2026-06-17  
Scope: PERF-VAL-01 foundational methodology assessment

## Fidelity Performance Metrics Visible in Position Export

Fidelity position CSVs in this repository include:
- Current Value
- Today Gain/Loss Dollar
- Today Gain/Loss Percent
- Total Gain/Loss Dollar
- Total Gain/Loss Percent
- Cost Basis Total
- Percent Of Account

These are position-level metrics and do not directly provide audited portfolio 1Y return methodology inputs.

## Fidelity UI Performance Metrics Referenced in Validation

Observed Fidelity values provided for this validation:
- 1-Year Return: 48.73%
- S&P 500: 27.95%
- Excess Return: +20.78%

## Likely Fidelity Methodology: TWRR (Most Probable)

Most likely Fidelity portfolio performance calculation in the UI context is time-weighted return (TWRR), potentially with account-class specific presentation variants.

Why TWRR is most likely:
- Brokerage performance dashboards typically isolate manager/investment performance from client cash timing.
- Benchmark comparison (portfolio vs S&P 500) is most naturally aligned to TWRR-style reporting.
- Fidelity already tracks event-level account activity and corporate actions needed for a robust TWRR chain.

Alternative methodology possibility:
- MWRR/IRR may be used in some account performance views, but this is less likely for direct benchmark-relative performance panels.

Conclusion:
- Fidelity is most likely reporting a cash-flow-adjusted TWRR-like performance figure for 1Y benchmark comparison, not a simple beginning/end snapshot ratio.

## Treatment Assessment by Component

### Deposits
Expected Fidelity treatment:
- Neutralized for manager-performance reporting in TWRR windows by subperiod segmentation.

SIH current capability:
- No complete transaction ledger surfaced for deposit events in current validation data layer.

### Withdrawals
Expected Fidelity treatment:
- Neutralized similarly via event-aware subperiod chaining.

SIH current capability:
- No complete withdrawal event ledger available for audited reconstruction.

### Dividends
Expected Fidelity treatment:
- Included in account return via reinvestment/cash credit accounting in subperiod calculations.

SIH current capability:
- Dividend/distribution events are not available as a complete explicit ledger in the validated dataset.

### Distributions
Expected Fidelity treatment:
- Included in performance stream according to account event timing.

SIH current capability:
- Not available as complete explicit event series for return chain reconstruction.

### Cash Positions
Expected Fidelity treatment:
- Cash balances included in total portfolio value and performance series.

SIH current capability:
- Cash appears in snapshots when present, but historical consistency is not complete across the 1Y horizon.

### Pending Activity
Expected Fidelity treatment:
- Accounted according to settlement status and posting rules inside Fidelity engine.

SIH current capability:
- Pending activity appears in some operational handling, but full event-level posting effects are not represented in current return-validation inputs.

## Methodology Implication for PERF-VAL-01

To reproduce Fidelity 1Y performance with high confidence, SIH needs:
- Continuous 1Y (or longer) daily/effective valuation history
- Event-complete flow ledger (deposits, withdrawals, dividends, distributions)
- Explicit policy for pending/settlement timing
- Cash-included total return chain

Without these, SIH can compute a defensible short-window snapshot return but not a full-confidence Fidelity-equivalent 1Y return.
