# Fidelity Portfolio File Inventory
**Project:** PIS-001
**Date:** 2026-06-12

## Scope

This inventory documents the Fidelity portfolio download inputs available for PIS Phase 1.

Current evidence in the workspace includes Fidelity portfolio position exports such as:
- [incoming/portfolio/Portfolio_Positions_May-21-2026.csv](../../incoming/portfolio/Portfolio_Positions_May-21-2026.csv)
- [incoming/portfolio/Portfolio_Positions_May-29-2026.csv](../../incoming/portfolio/Portfolio_Positions_May-29-2026.csv)

## Exact Available Fields

The current Fidelity export header includes:
- Account Number
- Account Name
- Symbol
- Description
- Quantity
- Last Price
- Last Price Change
- Current Value
- Today's Gain/Loss Dollar
- Today's Gain/Loss Percent
- Total Gain/Loss Dollar
- Total Gain/Loss Percent
- Percent Of Account
- Cost Basis Total
- Average Cost Basis
- Type

## Field Notes

### Account
- Present as `Account Number` and `Account Name` in the current sample export.
- Some Fidelity exports may use combined account naming, but the parser should tolerate the split form first.

### Symbol
- Unique security identifier in the row.
- Cash sweep or placeholder positions may appear as Fidelity-specific symbols such as `SPAXX**` or `--`-style placeholders in some exports.

### Shares
- Exposed as `Quantity` in the Fidelity file.
- This is the source for position count and change detection.

### Price
- Exposed as `Last Price`.
- Useful for approximate mark-to-market analysis.

### Market Value
- Exposed as `Current Value`.
- This is the primary weight denominator for snapshot math.

### Cost Basis
- Exposed as `Cost Basis Total`.
- Critical for trade return approximation and future lineage.

### Gain/Loss
- Exposed both as dollar and percent variants:
  - `Today's Gain/Loss Dollar`
  - `Today's Gain/Loss Percent`
  - `Total Gain/Loss Dollar`
  - `Total Gain/Loss Percent`
- Useful for sanity checks and current-position outcome display.

### Cash Positions
- Fidelity shows cash-like exposure in the same holdings file.
- In the current sample, `SPAXX**` appears as a money-market sweep row.
- PIS should treat cash as a first-class portfolio position for snapshot math and change detection.

## Accessibility

- File source: Fidelity portfolio download export
- Operator access: manual download
- SIH/PIS access: file ingestion from `incoming/portfolio/`
- Existing SIH parser support: yes, through `src/portfolio/ingestion.py`

## Automation Feasibility

- Manual file drop: fully feasible today
- Automated ingestion of the file itself: feasible once download delivery is standardized
- Browser automation of Fidelity UI: possible but brittle and not recommended for Phase 1

## What Is Not Present in the File

- transaction history
- buys/sells ledger
- dividend ledger
- tax lot detail
- benchmark returns
- explicit cash-flow events such as deposits and withdrawals

## Conclusion

Fidelity portfolio download files are sufficient to build a Phase 1 PIS snapshot history and change detector, but not sufficient to fully explain cash-flow-aware long-window performance without later enhancement.
