# Phase 23.6 — Capital Rotation Advisor
## Deliverable 3: Rotation Framework

**Date:** 2026-06-04
**Status:** Design Phase

---

## Overview

The Rotation Framework is the core CRA mechanism that bridges capital sources (sell candidates) to deployment targets (CW-DAS queue). It operates as a **read-only composition layer** — it reads from existing system outputs and produces a `RotationProposal` artifact without modifying any upstream scores.

---

## 3.1 Framework Principles

1. **Guidance only.** The CRA produces rotation proposals; the operator makes all execution decisions.
2. **Existing rankings respected.** CW-DAS order is used as-is. The CRA does not re-rank the queue.
3. **No speculative sizing.** Proceeds estimates are derived from current market values and category-specific sizing heuristics. No predictive price modeling.
4. **Policy gates preserved.** Operator policies (DO_NOT_SELL, SELL_LAST, etc.) are surfaced on every capital source record.
5. **Alignment-first allocation.** Available proceeds are allocated to deployment targets in CW-DAS rank order, subject to allocation node constraints.

---

## 3.2 Rotation Proposal Structure

```
RotationProposal
├── proposal_id          str      # stable identifier for this rotation set
├── run_id               str      # parent PAR run_id
├── as_of_date           str      # ISO 8601 date
├── total_capital_pool   float    # sum of estimated_proceeds across all sources
├── sources              list[CapitalSourceRecord]   # from Deliverable 2
├── deployments          list[RotationDeploymentTarget]
├── impact               PortfolioImpactEstimate
└── proposal_status      str      # DRAFT | READY | OPERATOR_REVIEW_REQUIRED
```

```
RotationDeploymentTarget
├── rank                 int      # CW-DAS rank (unchanged)
├── symbol               str
├── deployment_score     float    # CW-DAS score (unchanged)
├── allocation_node      str      # e.g. EQUITIES.US.LARGE
├── suggested_amount     float    # capital allocated from pool (USD)
├── suggested_pct_add    float    # would add X% to current position
├── current_weight_pct   float
├── projected_weight_pct float    # after rotation (guidance only)
├── narrative_tier       str      # CCL or HCA
├── score_breakdown      CwDasBreakdown   # unchanged from queue
└── allocation_note      str      # why this amount was suggested
```

```
PortfolioImpactEstimate
├── alignment_score_before   float    # pre-rotation (from current PAR)
├── alignment_score_after    float    # post-rotation estimate (simple linear model)
├── alignment_delta          float    # signed delta
├── concentration_before     float    # top-5 holding weight sum
├── concentration_after      float    # estimate after rotation
├── concentration_delta      float    # signed delta
├── overweight_nodes_before  list[str]
├── overweight_nodes_after   list[str]
└── impact_narrative         str      # one-sentence human summary
```

---

## 3.3 Capital Pool Assembly

Step 1: **Collect all CapitalSourceRecords** from the five taxonomy categories.

Step 2: **Apply policy gates.**
- Remove any source where `blocked_by_policy = True` (DO_NOT_SELL).
- Mark SELL_LAST sources with a rank modifier (displayed last in source list).

Step 3: **De-duplicate.** If a holding appears in multiple categories, use the highest-priority category record and merge the evidence summaries.

Step 4: **Sort by priority.** URGENT > HIGH > MODERATE > LOW.

Step 5: **Compute total_capital_pool.**
```
total_capital_pool = sum(source.estimated_proceeds for source in filtered_sources)
```

---

## 3.4 Deployment Target Allocation

Step 1: **Read deployment queue** from current PAR `deployment_queue.json` (unchanged CW-DAS ordering).

Step 2: **Filter queue to alignment-improving candidates.**
- Exclude candidates whose `allocation_node` is already at or above target.
- Exclude candidates with `policy_protected = True`.
- Prioritize candidates in underweight allocation nodes.

Step 3: **Allocate capital in CW-DAS rank order.**

For each candidate (rank 1, 2, 3...):
- Compute `headroom_amount = (WARN_POSITION_PCT - current_weight_pct) / 100 × portfolio_mv`
- `suggested_amount = min(headroom_amount, remaining_pool, proportional_share)`
- `remaining_pool -= suggested_amount`
- Stop when `remaining_pool < minimum_lot_size` (configurable, default $500)

Step 4: **Produce RotationDeploymentTargets.**

---

## 3.5 Illustrative Example

**Scenario:** Sell FIS → Buy VRT, ARW, DELL

```
Capital Sources:
┌─────────┬──────────────────────┬──────────────┬──────────────┬──────────┐
│ Symbol  │ Category             │ Est. Proceeds│ Priority     │ Policy   │
├─────────┼──────────────────────┼──────────────┼──────────────┼──────────┤
│ FIS     │ Signal Deterioration │ $12,400      │ HIGH         │ None     │
│         │ (BEARISH, overweight │              │              │          │
│         │ EQUITIES.US.LARGE)   │              │              │          │
└─────────┴──────────────────────┴──────────────┴──────────────┴──────────┘

Capital Pool: $12,400

Deployment Targets (CW-DAS order, top 3 qualifying):
┌──────┬────────┬──────────────────┬────────────────┬────────────────────┐
│ Rank │ Symbol │ CW-DAS Score     │ Allocation Node│ Suggested Amount   │
├──────┼────────┼──────────────────┼────────────────┼────────────────────┤
│  1   │ VRT    │ 92.5 (CCL)       │ US.LARGE       │ $5,800             │
│  3   │ ARW    │ 84.0 (HCA)       │ US.MID         │ $4,100             │
│  7   │ DELL   │ 76.5 (HCA)       │ US.LARGE       │ $2,500             │
└──────┴────────┴──────────────────┴────────────────┴────────────────────┘

Portfolio Impact:
  Alignment score:      62.1 → 67.4   (+5.3 points)
  Concentration top-5:  41.2% → 39.8% (−1.4%)
  Overweight nodes:     EQUITIES.US.LARGE resolved
  Cash remaining:       $0

Impact narrative: "Rotating FIS to VRT/ARW/DELL resolves the US Large overweight,
adds 3 CCL/HCA holdings with replay support, and improves alignment by 5.3 points."
```

---

## 3.6 Alignment Delta Estimation Method

The alignment delta estimate is a **simplified projection only** — not a full re-run of the alignment engine. It uses:

1. Remove source holdings from the virtual portfolio (at their estimated_proceeds weight).
2. Add deployment target holdings at their suggested_amount weight.
3. Re-evaluate overweight/underweight status per allocation node using the revised weights.
4. Alignment score delta = (resolved overweight nodes × +4) + (newly underweight nodes × −2) + (deployment to underweight node × +3).

**Caveat:** This is an approximation. Actual alignment improvement requires a full PAR re-run. The CRA estimate is for planning guidance only — clearly labeled as such in the UI.

---

## 3.7 Minimum Viability Gates

A `RotationProposal` is marked `OPERATOR_REVIEW_REQUIRED` if any of the following are true:
- Any source has `policy_type = CORE_ANCHOR` (requires explicit operator confirmation)
- Estimated total_capital_pool exceeds 10% of portfolio_mv in a single rotation
- Any deployment target would exceed `WARN_POSITION_PCT` after allocation
- Tax bucket E position is present in sources (approaching LT threshold — explicit review)
- Any source has `tax_bucket = D` (significant long-term gain)

Otherwise: `DRAFT` (ready for operator review) or `READY` (no flags raised).

---

## 3.8 Framework Boundaries

The CRA framework explicitly does **not**:
- Determine lot selection (which specific shares to sell)
- Specify limit vs. market order types
- Account for intraday price movement
- Replace the operator's judgment on sizing, timing, or tax lot optimization
- Modify any PAR run scores or outputs
