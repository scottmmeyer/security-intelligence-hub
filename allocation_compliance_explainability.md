# Allocation Compliance Explainability

Repository: security-intelligence-hub  
Date: 2026-06-09

## Purpose

This document defines the explainability framework for allocation compliance indicators in the Allocation Intelligence panel.

## Two Distinct Compliance Concepts

### Strategic Target Compliance

**What it evaluates:** Does the proposed allocation planning model satisfy policy constraints?

**Data source:** `strategic_allocation_targets.csv` — the planned target percentages for each allocation node.

**Validators checked:**
- hierarchy_sums — do the target percentages sum correctly?
- policy_bounds — do asset class L1 nodes stay within asset class ceilings?
- concentration_ceilings — does the combined micro-cap target stay below 5%? Does mega cap stay below 50%?
- recalculation_churn — is the delta between old and new targets within the governance threshold?

**What a PASS means:** The allocation model itself is internally consistent and policy-compliant. It does not mean the portfolio currently holds those percentages.

### Current Portfolio Compliance

**What it evaluates:** Do the actual holdings in the portfolio today satisfy policy ceilings?

**Data source:** Latest PAR (Portfolio Analysis Run) alignment data — actual_pct per allocation node computed from current holdings.

**Checks performed:**
- Actual micro-cap combined vs 5% ceiling
- Actual mega-cap concentration vs 50% ceiling
- Actual digital assets vs 8% ceiling
- Actual cash vs floor

**What ADVISORY means:** Actual holdings exceed a policy ceiling by less than 3 percentage points. This is typical portfolio drift — natural movement as prices change. No immediate action required but operator should be aware.

**What OVER means:** Actual holdings exceed a policy ceiling by 3+ percentage points. This represents meaningful drift from the strategic target and may warrant rebalancing consideration.

## Why Both Can Be Correct Simultaneously

A portfolio can have Strategic Target Compliance = PASS and Current Portfolio Compliance = OVER when:

1. The strategic target for micro-cap is set at 2.21% (below the 5% ceiling → PASS)
2. The current portfolio holds approximately 6.5% in micro-cap securities (above the 5% ceiling → OVER)
3. The gap (4.29pp) represents portfolio drift — the portfolio has not yet been adjusted to reach the strategic target

This is a normal operational state. The planning model is valid (PASS). The portfolio has drifted from it (OVER). The operator should consider rebalancing toward the strategic target as a long-term objective.

## Drift Analysis

The gap between strategic target and actual holdings is the allocation drift.

Current example (micro-cap):
- Strategic target: 2.21%
- Actual holdings: ~6.5%
- Drift: +4.29pp above target (and +1.5pp above policy ceiling)

Severity: ADVISORY (1.5pp above ceiling, less than 3pp threshold for a hard warning)
