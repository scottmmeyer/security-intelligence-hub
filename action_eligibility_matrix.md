# Action Eligibility Matrix

**Date:** 2026-06-09  
**Legend:** ✓ = Can appear | ✗ = Cannot appear | ✓* = Conditional | (B) = Blocked/policy state shown, not executed

---

## Matrix

| Action Type | Top 10 | PAP (Recs Panel) | CRA | Deployment Queue | DQ Blocked List | Security Overlay |
|---|---|---|---|---|---|---|
| BUY | ✓ (only type) | ✗ | ✗ | ✓ (only type) | ✗ | ✗ |
| ACCUMULATE | ✓ (shown as BUY) | ✓ (INCREASE_UNDERWEIGHT) | ✗ | ✓ | ✗ | ✓ |
| HOLD | ✗ | ✓ (STRATEGIC_RETAIN_SIGNAL) | ✗ | ✗ | ✗ | ✓ |
| WATCH | ✗ | ✓ (observation lane) | ✗ | ✗ | ✗ | ✓ |
| TRIM | ✗ | ✓ (STRATEGIC_TRIM_CANDIDATE) | ✓ (SIGNAL_DETERIORATION) | ✗ | ✗ | ✓ |
| SELL | ✗ | ✓* (if explicitly generated) | ✓ (STRATEGIC_EXIT) | ✗ | ✗ | ✓* |
| REDUCE_OVERWEIGHT | ✗ | ✓ (REDUCE_OVERWEIGHT rec) | ✓ (OVERWEIGHT_REDUCTION) | ✗ | ✗ | ✗ |
| INCREASE_UNDERWEIGHT | ✗ | ✓ (INCREASE_UNDERWEIGHT rec) | ✗ | ✗ | ✗ | ✗ |
| ROTATE (sell→buy pair) | ✗ | ✗ | ✓ (RotationProposal) | ✗ | ✗ | ✗ |
| FUNDING_SOURCE | ✗ | ✗ | ✓ (capital source pool) | ✗ | ✗ | ✗ |
| BLOCKED_ACTION | ✗ | ✓ (blocked lane) | (B) (shown as blocked) | ✗ | ✓ | (B) |
| DEFERRED_ACTION | ✗ | ✓ (blocked lane) | (B) | ✗ | ✓ | (B) |
| REDUCE_CANDIDATE | ✗ | ✓* (via REDUCE_OVERWEIGHT) | ✓ | ✗ | ✗ | ✓ |
| LOW_CONVICTION | ✗ | ✓* | ✓ (LOW_CONVICTION_REDUCTION) | ✗ | ✗ | ✗ |
| TAX_AWARE_EXIT | ✗ | ✗ | ✓ (TAX_AWARE_EXIT) | ✗ | ✗ | ✗ |

---

## Key Observations

### 1. Top 10 / Deployment Queue are Buy-Only Surfaces

The DQ eligibility gate (`_is_eligible()`) requires `signal_direction == BULLISH`. This is an **architectural commitment** that all DQ entries are buy-side candidates. No sell or trim action can enter the DQ, and by extension, cannot enter the Top 10.

### 2. PAP Is the Only Multi-Direction Surface

The Portfolio Action Pipeline (PAP) contains both buy actions (INCREASE_UNDERWEIGHT) and sell actions (REDUCE_OVERWEIGHT, STRATEGIC_TRIM_CANDIDATE). However, all current sell-context PAP recs are either BLOCKED_BY_POLICY or DEFERRED_BY_POLICY.

### 3. CRA Is the Only Dedicated Sell/Reduction Surface

The CRA capital pool exclusively contains reduction actions: SIGNAL_DETERIORATION, STRATEGIC_EXIT, OVERWEIGHT_REDUCTION, TAX_AWARE_EXIT, LOW_CONVICTION_REDUCTION. It has no buy-side entries.

### 4. No Unified Ranking Exists Across Buy and Sell Actions

There is no system component that ranks BUY actions against SELL/TRIM actions on a single priority scale. CW-DAS is used for buys; RPS is used for reductions. They are computed independently and never compared.

---

## Scoring System Comparison

| Scoring System | Used For | Range | Inputs |
|---|---|---|---|
| CW-DAS (deployment_score) | Buy prioritization (DQ) | 0–100+ | signal, replay, conviction tier, sizing headroom, momentum, fundamental |
| RPS (reduction_priority_score) | Sell/trim prioritization (REDUCE_OVERWEIGHT drilldown) | 0–100 | signal, score, replay absence, allocation pressure |
| Priority (1/2/3) | PAP rec ordering | 1–3 | urgency of recommendation type |
| Capital source priority | CRA source pool ordering | URGENT/HIGH/MODERATE/LOW/DEFER | ESS, overweight severity, strategic exit |

No cross-system mapping or normalization exists.
