# Fund Vehicle Intelligence (FVI) Problem Definition

Project: Security Intelligence Hub (SIH)  
Assessment: ISSUE-19 FVI Architecture and Governance  
Date: 2026-06-06

## Q1) Core Problem

SIH currently makes strong decisions about sleeve sizing and portfolio construction, but has limited intelligence about mutual fund vehicle quality. This creates a decision asymmetry:

- Sleeve decision: "International allocation is overweight; reduce exposure."
- Vehicle decision: "DODFX may be an excellent implementation vehicle within International exposure."

When those two decisions are not separated, SIH can recommend reducing a fund due to sleeve pressure without knowing whether the fund itself is superior, average, or weak versus peers.

## Problem Statement

FVI should solve the missing layer between allocation policy and implementation quality by answering:
1. Is this mutual fund a high-quality vehicle within its mandate?
2. Is it outperforming relevant peers on risk-adjusted, cost-aware, and persistence-aware bases?
3. Should SIH retain this vehicle while reducing sleeve size elsewhere?
4. Should SIH consider replacement, and only when evidence exceeds economic switching friction?

## A/B Decision Separation

### A) Sleeve Allocation Decision (Portfolio Construction)

Purpose:
- Determine target exposure by sleeve (for example International, US Large, Fixed Income).

Primary drivers:
- Portfolio-level risk budget
- Strategic allocation policy
- Concentration constraints
- Macro or governance constraints

Output:
- Increase, hold, or reduce sleeve exposure.

### B) Vehicle Quality Decision (Implementation Choice)

Purpose:
- Determine whether a specific fund is a good vehicle for delivering the sleeve mandate.

Primary drivers:
- Peer-relative risk-adjusted outcomes
- Cost efficiency and fee drag
- Manager/process stability
- Downside behavior and persistence
- Switching economics (loads, taxes, transaction friction)

Output:
- Retain, watchlist, or replace vehicle.

## Required Governance Conclusion

These two decision types should be evaluated separately, then recomposed through explicit policy rules.

Recommended composition rule:
1. Decide sleeve direction first.
2. Evaluate vehicle quality independently.
3. Allow "reduce sleeve, retain vehicle" as a valid combined outcome.
4. Prohibit automatic "overweight sleeve -> replace fund" logic.

## Why FVI Matters

Without FVI, SIH risks:
- false replacement recommendations,
- loss of high-quality managers due to allocation-only pressure,
- avoidable switching friction and tax drag,
- explainability gaps in CRA and Allocation Reduction outputs.

With FVI, SIH gains:
- cleaner separation of construction vs implementation,
- auditable replacement criteria,
- higher confidence in reduction and funding-source decisions,
- improved operator trust.

## Non-Goals (Assessment Boundary)

FVI does not, at assessment stage:
- alter CW-DAS methodology,
- alter ranking math,
- force replacement recommendations,
- assume active or passive superiority.

Assessment output is governance and architecture only.
