# PRA-IMPL-02 Funding Decision Trace

## Scope

This document traces actual recommendation funding behavior from PAP and CRA sources using
live runtime execution against PAR-CONCENTRATED_ALPHA-3FAFBBBF (2026-06-14 data).

All evidence is from code inspection and executed Python trace, not from design docs.

---

## PAP Funding Source Identification — Live Trace

PAR run: `data/portfolio_ingestion/analysis_runs/PAR-CONCENTRATED_ALPHA-3FAFBBBF`

`identify_funding_sources(...)` executed with real holdings/overlays/alignment.

### Result: 4 Sources Identified

| Rank | Type | Symbol(s) | Available % | Score | Policy Alignment |
|---|---|---|---|---|---|
| 1 | EXCESS_CASH | SPAXX | 7.03% | **107.03** | Uses excess liquidity before forcing equity reductions |
| 2 | TRIM_CANDIDATE | TSLA | 3.1% | 93.1 | Rotates out of weaker-signal names into higher-conviction |
| 3 | OVERWEIGHT_REDUCTION | SBS, DODFX, CVE | 6.83% | 92.83 | Repairs allocation drift while funding underweight nodes |
| 4 | OVERWEIGHT_REDUCTION | SBS, DODFX, VXUS | 4.25% | 90.25 | Repairs allocation drift while funding underweight nodes |

**Summary emitted:**
> 4 funding source(s) identified. Primary: Excess Cash (SPAXX, ~7.0% available). Score 107.0. Alternatives considered: Trim Candidate, Overweight Reduction.

---

## PAP Recommendation Rationale — Before and After PRA-IMPL-02

### Pre-PRA (persisted in PAR run, generated before this implementation)

```
Funding source: Excess Cash (SPAXX, ~7.0% available).
```

Why/Alternatives/Policy clauses: **NOT PRESENT**

### Post-PRA (what the engine produces NOW with new code)

```
Funding source: Excess Cash (SPAXX, ~7.0% available). Why this source: Cash/sweep
allocation (9.0%) exceeds the operational reserve floor (2%). Approximately 7.0% is
deployable without affecting liquidity. Alternatives considered: Trim Candidate,
Overweight Reduction. Policy alignment: Uses excess liquidity before forcing equity
reductions, preserving optionality.
```

Why/Alternatives/Policy clauses: **ALL PRESENT**

---

## CRA Reduction Scoring — Sampled Candidates

Representative synthetic sample exercising all category types against real portfolio context:

| Rank | Symbol | Category | Priority | Score | Key Drivers |
|---|---|---|---|---|---|
| 1 | MSFT | SIGNAL_DETERIORATION | URGENT | **130.0** | Base 90 + priority 20 + ESS VERY_BEARISH +12 + signal BEARISH +8 |
| 2 | AAPL | SIGNAL_DETERIORATION | HIGH | 117.0 | Base 90 + priority 12 + ESS BEARISH +7 + signal BEARISH +8 |
| 3 | AMZN | STRATEGIC_EXIT | HIGH | 96.0 | Base 84 + priority 12 |
| 4 | NVDA | OVERWEIGHT_REDUCTION | HIGH | **80.0** | Base 76 + priority 12 + drift 14pp (capped +18) **–22 conviction penalty** (CORE_CONVICTION_LEADER in queue) |
| 5 | META | LOW_CONVICTION_REDUCTION | MODERATE | 61.0 | Base 55 + priority 6 |

**Critical observation:** NVDA was penalized –22 because it appears in the deployment queue as CORE_CONVICTION_LEADER. This is a genuine behavioral change versus pre-PRA which had no penalty logic.

---

## CRA Deployment Annotations — VRT and ARW

After `annotate_deployments_with_funding_plan(...)`:

**Target: VRT (rank 1)**
- `funding_source_symbol`: MSFT
- `funding_source_category`: SIGNAL_DETERIORATION
- `funding_source_score`: 130.0
- `funding_source_reason`: "Weak signal posture and deterioration evidence justify reducing this holding first. Preferred over alternatives due to higher policy-aware reduction score (130.0)."
- `funding_source_alternatives`: ["AAPL (SIGNAL DETERIORATION, score 117.0)", "AMZN (STRATEGIC EXIT, score 96.0)", "NVDA (OVERWEIGHT REDUCTION, score 80.0)"]
- `funding_policy_alignment_reason`: "Aligned with concentrated-alpha philosophy: rotate from weaker or over-allocated exposures into higher-conviction opportunities with explicit policy constraints."

**Target: ARW (rank 2)**
- Same primary source (MSFT at 130.0) — shared source pool, no per-target depletion modeled
- Same alternatives

---

## Recommendation Traces (5 Sampled)

### REC-1: INCREASE_UNDERWEIGHT EQUITIES.US.LARGE (type: INCREASE_UNDERWEIGHT)
- Recommended: build EQUITIES.US.LARGE allocation (–7.3pp drift)
- Funding source selected: EXCESS_CASH (SPAXX, 7.0%)
- Why selected: cash above reserve floor (9% total – 2% floor = 7% deployable); EXCESS_CASH scores 107.03
- Alternatives: TRIM_CANDIDATE (TSLA, 93.1), OVERWEIGHT_REDUCTION (SBS, 92.83)
- Why EXCESS_CASH won: highest base score (100 vs 86 vs 80) + available % bonus
- Scoring components: base(100) + min(20, available_pct=7.03) = 107.03

### REC-2: INCREASE_UNDERWEIGHT EQUITIES.US.MEGA.EXTENDED_MEGA
- Same funding path: EXCESS_CASH primary
- Same 3 alternatives listed

### REC-3: REDUCE_OVERWEIGHT EQUITIES.INTERNATIONAL.LARGE (+4.2pp drift)
- No funding context embedded (reduce recommendations don't carry funding source)

### REC-4: REDUCE_OVERWEIGHT EQUITIES.US.MEGA.HYPER_MEGA (+3.7pp drift)
- No funding context embedded

### REC-5 (Synthetic CRA deployment — VRT/ARW):
- Primary: MSFT (score 130.0)
- Alternatives: AAPL, AMZN, NVDA
- Conviction penalty on NVDA confirmed active

---

## Scoring Component Breakdown

**EXCESS_CASH score formula:**
- `base = 100.0`
- `+ min(20, available_pct=7.03) = +7.03`
- `total = 107.03`

**TRIM_CANDIDATE score formula:**
- `base = 86.0`
- `+ min(20, available_pct=3.1) = +3.1`
- `+ bearish_bonus: TSLA has BEARISH ESS → +4.0`
- `total = 93.1`

**OVERWEIGHT_REDUCTION formula:**
- `base = 80.0 + fixed_bonus_6.0 = 86.0`
- `+ min(20, available_pct) — capped`
- `total ≈ 90–93`
