# Recommendation Change Assessment

Repository: security-intelligence-hub  
PAR: PAR-20260529-7482D734  
Date: 2026-06-08

## Context

This assessment evaluates the current PAR output and identifies any material changes relative to what prior incorrect portfolio analyses may have shown. All conclusions below are based exclusively on PAR-20260529-7482D734, derived from the May-29-2026 Fidelity export.

## Q4 — Current Recommendation Set (6 True Actions)

### Allocation Actions

| Priority | Type | Node | Drift | Severity | Mandate |
|---|---|---|---|---|---|
| 1 | REDUCE | EQUITIES.INTERNATIONAL | +6.08pp | MODERATE | STANDARD_OVERWEIGHT |
| 2 | REDUCE | EQUITIES.INTERNATIONAL.LARGE | +4.25pp | MODERATE | STANDARD_OVERWEIGHT |
| 3 | REDUCE | EQUITIES.US.MEGA.ULTRA_MEGA | +4.45pp | MODERATE | STANDARD_OVERWEIGHT |
| 4 | INCREASE | EQUITIES.US.LARGE | -6.17pp | MODERATE | INTENTIONAL_UNDERWEIGHT |
| 5 | INCREASE | EQUITIES.US.MEGA.EXTENDED_MEGA | -4.15pp | MODERATE | INTENTIONAL_UNDERWEIGHT |
| 6 | REPLAY | EQUITIES.US.LARGE | — | MODERATE | — |

### Deployment Queue (Top 10)

| Rank | Symbol | Score | Tier | Policy |
|---|---|---|---|---|
| 1 | VRT | 98.530 | CORE_CONVICTION_LEADER | None |
| 2 | ARW | 97.110 | HIGH_CONVICTION_ANCHOR | None |
| 3 | ATLC | 94.810 | HIGH_CONVICTION_ANCHOR | None |
| 4 | LRCX | 94.730 | HIGH_CONVICTION_ANCHOR | None |
| 5 | DELL | 94.580 | HIGH_CONVICTION_ANCHOR | None |
| 6 | CAH | 93.090 | HIGH_CONVICTION_ANCHOR | None |
| 7 | PCB | 92.740 | HIGH_CONVICTION_ANCHOR | None |
| 8 | AVT | 92.600 | HIGH_CONVICTION_ANCHOR | None |
| 9 | SANM | 92.450 | HIGH_CONVICTION_ANCHOR | None |
| 10 | CRS | 91.370 | HIGH_CONVICTION_ANCHOR | None |

### Policy-Suppressed

- TSLA: DO_NOT_SELL — blocked from deployment queue (BLOCKED_BY_POLICY / MONITOR_ONLY)

## Q4 — International Reduction Holdings Detail

Node: EQUITIES.INTERNATIONAL.LARGE (drift +4.25pp)

| Symbol | Market Value | Portfolio % | Notes |
|---|---|---|---|
| SBS | $18,100.14 | 3.83% | Largest contributor |
| DODFX | $15,318.42 | 3.24% | SELL_LAST policy active |
| VXUS | $3,938.01 | 0.83% | — |
| VEA | $3,589.25 | 0.76% | — |
| FIGFX | $1,232.94 | 0.26% | — |
| NVS | $911.57 | 0.19% | — |
| TTNDY | $517.93 | 0.11% | — |

## Q5 — Policy Interaction Analysis

### TSLA — DO_NOT_SELL

Current impact:
- Deployment queue: BLOCKED_BY_POLICY / MONITOR_ONLY (confirmed in policy_suppressed list)
- Allocation Reduction: If TSLA appears in any reduction candidate list, execution should be BLOCKED_BY_POLICY
- Funding Sources: TSLA should not appear as an executable funding source — policy prevents liquidation
- CRA: If CRA generates a capital-source entry for TSLA, blocked_by_policy=True should apply
- PAP: TSLA excluded from executable sell queue

Gap identified: Funding Sources and Allocation Reduction surfaces have not yet been normalized to apply BLOCKED_BY_POLICY execution state (PRA-IMPL-02 scope — not yet implemented).

### DODFX — SELL_LAST

Current impact:
- DODFX appears in EQUITIES.INTERNATIONAL.LARGE reduction candidates (2nd largest at $15,318.42 / 3.24%)
- DODFX also appears in EQUITIES.INTERNATIONAL reduction candidates
- With SELL_LAST active, DODFX should be ranked at the tail of the international reduction candidate list
- Current SIH behavior: SELL_LAST is applied in the deployment queue tail-ranking, but explicit DEFERRED_BY_POLICY state propagation to Allocation Reduction and Funding Sources is pending PRA-IMPL-02

Gap identified: DODFX currently appears in reduction candidate lists without explicit deferred ordering — the recommendation text does not yet reference the SELL_LAST constraint. This is the policy normalization gap identified in PRA-IMPL-02.

### Impact If Policies Were Fully Applied (Post PRA-IMPL-02)

| Symbol | Surface | Current | Post PRA-IMPL-02 |
|---|---|---|---|
| TSLA | Funding Sources | Not explicitly blocked in surface text | BLOCKED_BY_POLICY badge + excluded from executable funding sources |
| TSLA | Allocation Reduction | Not explicitly blocked | BLOCKED_BY_POLICY / MONITOR_ONLY |
| DODFX | Allocation Reduction | Listed as candidate | DEFERRED_BY_POLICY / REDUCE_SELL_LAST; tail-ranked |
| DODFX | Funding Sources | Listed as candidate | DEFERRED_BY_POLICY; last-resort liquidation only |

## Conviction Anchors

High Conviction Retain signals currently in recommendation stream:
- DELL (STRATEGIC_RETAIN_SIGNAL / OBSERVATION)
- MSFT (STRATEGIC_RETAIN_SIGNAL / OBSERVATION)
- MU (STRATEGIC_RETAIN_NARRATIVE / NARRATIVE)
- VRT (STRATEGIC_RETAIN_NARRATIVE / NARRATIVE)
- CVE (STRATEGIC_RETAIN_NARRATIVE / NARRATIVE)

Post PRA-IMPL-04: These 5 items would move to the Conviction Anchors section and be removed from the Actions count, reducing reported recommendation workload from 33 cards to 6 true actions.

## Material Changes Versus Prior Analysis

All prior analyses using the wrong portfolio must be considered unreliable for:
- Portfolio MV (correct: $472,219.90)
- Cash balance (correct: $42,619.59)
- Deployable cash (correct: $9,564.20)
- Node drift percentages (all percentages recalculated from May-29 positions)
- Deployment queue ranking (based on current ESS data from June-8 intake)

The most material issue: any prior analysis showing $54K as deployable was based on a portfolio not matching the May-29 Fidelity export, or used a real-time balance not reflected in the uploaded CSV.
