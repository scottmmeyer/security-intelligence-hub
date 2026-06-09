# AI-002 Allocation Labeling Report

Repository: security-intelligence-hub  
Issue: AI-002 (#30)  
Date: 2026-06-09  
Status: IMPLEMENTED

## What Was Built

Every allocation display on the Allocation Intelligence page now carries an explicit dataset source label.

## Label Applied Per Section

| Section | Label | CSS Class | Dataset |
|---|---|---|---|
| Recalculation Status & Validators | "Strategic Target Recalculation Compliance — validates the allocation model, not current portfolio holdings." | source-strategic | Strategic allocation recalculation pipeline |
| Strategic Allocation Targets (table) | "Strategic Target Allocation — planned target percentages from the current allocation model. Represents where the portfolio is intended to be, not its current state." | source-strategic | Strategic targets CSV / archetype engine |
| Concentration Risk (bars) | "Strategic Target Compliance — bars show strategic target percentages vs policy ceilings. A PASS here means the allocation model is within policy." | source-strategic | Strategic targets |
| Current Portfolio Compliance (new) | "Current Portfolio Allocation — bars show actual portfolio holdings vs policy ceilings. OVER here means the current portfolio exceeds a policy ceiling today." | source-actual | Latest PAR alignment data |
| Effective Allocation Recommendation (chart + table) | "Effective Allocation After Overlays — strategic target percentages adjusted by active tactical momentum overlays. The recommended allocation, not current portfolio state." | source-effective | Strategic targets + tactical overlays |

## Operator Understanding Test

After this change, an operator viewing the page can always answer:
1. "What type of data is this section showing?" — the banner makes it explicit
2. "Why does Concentration Risk show PASS when the compliance section shows OVER?" — the explainability note answers this directly
3. "What are these percentages?" — every table and chart is labelled as Strategic Target, Current Portfolio, or Effective Recommendation

## Before vs After (AI-002)

Before: multiple allocation percentage tables with no source labels; operators had to infer.

After:
- Strategic Allocation Targets table: clearly marked "Strategic Target Allocation"
- Concentration Risk: marked "Strategic Target Compliance"
- Effective Allocation chart: marked "Effective Allocation After Overlays"
- New Current Portfolio Compliance: marked "Current Portfolio Allocation"
