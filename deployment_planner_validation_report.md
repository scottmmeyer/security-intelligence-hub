# Deployment Planner Validation Report
**Phase 7.5D — Capital Deployment Planner**
**Reference Run:** PAR-20260531-F794D952
**Report Date:** 2025-06-01
**Status:** ✅ CERTIFIED

---

## 1. Overview

Phase 7.5D introduces the Capital Deployment Planner (`src/portfolio/deployment_planner.py`), a read-only guidance layer that answers:

> "I have $X deployable — where should it go and how much to each position?"

The planner consumes the CW-DAS ranked deployment queue (Phase 7.5B) and produces a `DeploymentPlan` artifact with per-holding `AllocationRecommendation` records organized into three operator-navigable tiers. No trade generation. No execution authority. No order files.

---

## 2. Allocation Algorithm

### 2.1 Eligibility Filter

A holding is eligible for allocation if:
- `redundancy_pen == 0` (not flagged as OW-node)
- `headroom_pct > 0` (has room below `WARN_POSITION_PCT = 6%`)

**PAR-20260531-F794D952 result:** 32 of 43 queue items eligible; 11 excluded (OW/blocked).

### 2.2 Rank-Weighted Proportional Formula

```
weight_i = deployment_score_i × conviction_mult_i / √rank_i

conviction_mult:
  CORE_CONVICTION_LEADER (CCL) = 3.0
  HIGH_CONVICTION_ANCHOR (HCA) = 1.0

raw_alloc_i = (weight_i / Σ weights) × deployable_cash
```

The √rank decay concentrates capital toward top-ranked positions. The 3× CCL multiplier ensures CORE_CONVICTION_LEADER holdings receive priority treatment consistent with the fund's conviction intensity.

### 2.3 Per-Position Cap

Each position is capped at `max(0, (WARN_POSITION_PCT − current_pct) / 100 × total_mv)`. The planner targets the warn threshold (6%) for safety — exceeding it requires deliberate operator override. Overflow from capped positions is redistributed proportionally among still-uncapped eligible candidates.

### 2.4 Tier Assignment

| Tier | Criteria |
|------|----------|
| TIER_1 (Highest) | `narrative_tier == CORE_CONVICTION_LEADER` |
| TIER_2 (Secondary) | HCA candidates with `rank ≤ floor(N × 0.35)` |
| TIER_3 (Optional) | All remaining eligible candidates |

---

## 3. Validation Results — PAR-20260531-F794D952

### 3.1 Fund Context

| Metric | Value |
|--------|-------|
| Total Portfolio Market Value | $472,219.90 |
| Cash MV | $42,619.59 (9.03%) |
| Floor Reserve | $9,444.40 (2.00%) |
| Deployable Cash | $33,175.19 (7.03%) |
| Eligible Candidates | 32 of 43 |

### 3.2 Allocation Summary

| Tier | Candidates | Allocated | % of Plan |
|------|-----------|-----------|-----------|
| TIER_1 — CCL | 2 | $13,199.78 | 39.8% |
| TIER_2 — HCA Top | 13 | $11,673.05 | 35.2% |
| TIER_3 — Optional | 17 | $8,302.36 | 25.0% |
| **TOTAL** | **32** | **$33,175.19** | **100%** |

Total allocated = deployable cash (no residual). All eligible cash deployed.

### 3.3 Top 10 Recommendations

| Rank | Symbol | Tier | Current $ | Current % | +Add | Projected $ | Projected % | Status |
|------|--------|------|-----------|-----------|------|-------------|-------------|--------|
| #1 | AEIS | TIER_1 | $11,435 | 2.42% | **$7,733** | $19,168 | 4.06% | DEPLOYABLE |
| #2 | VRT | TIER_1 | $17,009 | 3.60% | **$5,467** | $22,476 | 4.76% | DEPLOYABLE |
| #3 | ARW | TIER_2 | $4,330 | 0.92% | $1,466 | $5,796 | 1.23% | DEPLOYABLE |
| #4 | SNX | TIER_2 | $4,083 | 0.86% | $1,261 | $5,344 | 1.13% | DEPLOYABLE |
| #5 | ATLC | TIER_2 | $4,200 | 0.89% | $1,128 | $5,328 | 1.13% | DEPLOYABLE |
| #6 | PSX | TIER_2 | $3,534 | 0.75% | $1,028 | $4,562 | 0.97% | DEPLOYABLE |
| #7 | CAH | TIER_2 | $4,987 | 1.06% | $937 | $5,924 | 1.25% | DEPLOYABLE |
| #8 | AVT | TIER_2 | $4,371 | 0.93% | $875 | $5,246 | 1.11% | DEPLOYABLE |
| #9 | LRCX | TIER_2 | $4,482 | 0.95% | $825 | $5,307 | 1.13% | DEPLOYABLE |
| #10 | DELL | TIER_2 | $6,237 | 1.32% | $778 | $7,015 | 1.49% | DEPLOYABLE |

### 3.4 Portfolio Impact

| Metric | Before | After |
|--------|--------|-------|
| Cash MV | $42,619 | $9,444 |
| Cash % | 9.03% | 2.00% |
| Positions ≥ 6% (warn) | 2 | 2 |
| Unallocated Cash | — | $0 |

Cash reaches the floor reserve level ($9,444 = 2.00%), which is correct — the planner deploys all available cash while respecting `MIN_CASH_PCT = 2.0%`.

---

## 4. Acceptance Criteria Checklist

| # | Criterion | Result | Notes |
|---|-----------|--------|-------|
| AC-1 | `total_allocated ≤ deployable_cash` | ✅ PASS | $33,175.19 = $33,175.19 |
| AC-2 | No position exceeds `MAX_POSITION_PCT = 8%` after deployment | ✅ PASS | Max projected: VRT 4.76% |
| AC-3 | No position projected above `WARN_POSITION_PCT = 6%` | ✅ PASS | All capped at warn threshold |
| AC-4 | Projected weights reconcile: `current_mv + suggested_add ≈ projected_mv` | ✅ PASS | Δ < $0.01 per position |
| AC-5 | AEIS (rank 1, CCL) assigned TIER_1 | ✅ PASS | AEIS → TIER_1 |
| AC-6 | VRT (rank 2, CCL) assigned TIER_1 | ✅ PASS | VRT → TIER_1 |
| AC-7 | CCL candidates receive higher allocation than HCA peers | ✅ PASS | AEIS $7,733 > all TIER_2 |
| AC-8 | OW-node-blocked candidates excluded from recommendations | ✅ PASS | 11 blocked candidates absent |
| AC-9 | `unallocated + total_allocated ≈ deployable_cash` | ✅ PASS | $0 + $33,175 = $33,175 |
| AC-10 | Tier summaries sum to `total_allocated` | ✅ PASS | $13,200 + $11,673 + $8,302 = $33,175 |
| AC-11 | Zero cash → empty plan (no crash) | ✅ PASS | Unit test passes |
| AC-12 | Empty queue → empty plan (no crash) | ✅ PASS | Unit test passes |
| AC-13 | All-blocked queue → empty plan (no crash) | ✅ PASS | Unit test passes |
| AC-14 | Cash override respected | ✅ PASS | Unit test passes |
| AC-15 | All recommendations have non-empty `allocation_rationale` | ✅ PASS | 32 rationales present |
| AC-16 | All `constraint_status` values are valid CONSTRAINT_STATUSES | ✅ PASS | All 32 = "DEPLOYABLE" |

**All 16 acceptance criteria: PASS**

---

## 5. Test Coverage

**Total new tests: 26**

| Test Class | Tests | Focus |
|------------|-------|-------|
| TestEdgeCases | 4 | zero cash, empty queue, all-blocked, cash override |
| TestAllocationInvariants | 6 | total ≤ cash, no MAX breach, reconciliation, unallocated, tier sums, advisory |
| TestTierAssignment | 3 | CCL → TIER_1, HCA → not TIER_1, OW excluded |
| TestCCLPriority | 2 | CCL gets more than HCA, rank decay |
| TestReferenceRun | 11 | AEIS/VRT TIER_1, allocation bounds, projected weights, impact, tier pct, version |

**Full test suite: 692 tests passing (666 pre-7.5D + 26 new). Zero regressions.**

---

## 6. Architecture & Governance Notes

| Concern | Decision |
|---------|---------|
| Read-only? | Yes — planner only reads `deployment_queue.json`; writes nothing to portfolio state |
| Scoring changes? | None — CW-DAS ranks consumed exactly as produced by Phase 7.5B |
| New scoring model? | No — weighting formula uses existing `deployment_score` and `narrative_tier`; no new signal inputs |
| Trade generation? | Explicitly prohibited — output is advisory allocation guidance only |
| UI placement? | "Generate Deployment Plan" button added to existing Capital Deployment Queue panel; plan renders in companion `#deploymentPlanContainer` below the queue |
| Backend route? | `POST /api/portfolio/deployment-plan` (on-demand compute for pre-7.5D runs) |
| Persistence? | `deployment_plan.json` written alongside `deployment_queue.json` during `run_analysis()` |
| Pre-7.5D runs? | `load_analysis_run()` loads `deployment_plan.json` if present; on-demand API for older runs |

---

## 7. Artifacts Produced

| Artifact | Location | Phase |
|----------|----------|-------|
| `src/portfolio/deployment_planner.py` | Source | 7.5D engine |
| `tests/test_7_5d_deployment_planner.py` | Tests | 26 tests |
| `data/…/PAR-20260531-F794D952/deployment_plan.json` | Run data | Reference validation run |
| `deployment_planner_validation_report.md` | Root | This document |

---

## 8. Certification

```
PHASE 7.5D — CAPITAL DEPLOYMENT PLANNER
VALIDATION STATUS: ✅ CERTIFIED

  All 16 acceptance criteria: PASS
  Test suite: 692 tests, 0 failures
  No MAX_POSITION_PCT breaches in reference run
  No scoring model changes (read-only synthesis)
  No trade generation, no execution authority
  UI: companion view added to Capital Deployment Queue

SIGNED: automated validation — PAR-20260531-F794D952
```
