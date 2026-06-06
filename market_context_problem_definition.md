# Market Context Problem Definition

Project: Security Intelligence Hub (SIH)  
Assessment: Market Context Intelligence (MCI)  
Date: 2026-06-06

## 1) Core Problem

SIH currently explains security outcomes primarily through security-level and portfolio-internal evidence:
- Analyst signal quality (ESS, analyst consensus, targets)
- Replay support
- CW-DAS and STI logic
- Fundamental validation (thesis integrity, consistency, modifier)
- Dislocation diagnostics

Gap:
SIH has limited explicit representation of external market-state shocks that can dominate short-horizon price behavior even when company fundamentals are stable.

Consequence:
SIH can correctly detect weak or conflicting security-level evidence, but cannot consistently distinguish:
- company-specific deterioration versus
- market-wide or sector-wide transient stress/liquidity events.

## 2) Why This Matters

Without a bounded market-context layer, operators face two opposite failure modes:
1. Overreact to transient market stress by treating it as thesis failure.
2. Underreact to true thesis deterioration by over-attributing moves to macro noise.

A governance-safe MCI should reduce attribution error, not create a narrative engine.

## 3) Boundary Conditions

MCI must respect existing SIH principles already used in PMI and Dislocation governance:
- interpretation first, automation second
- deterministic evidence over story-based inference
- no circular scoring feedback without validated outcome evidence
- operator authority preserved

## 4) Problem Decomposition

### A. Detectable Market-State Questions
- Is current market regime broadly risk-on or risk-off?
- Is volatility regime materially elevated?
- Is sector-relative stress broad-based or idiosyncratic?
- Is there a known scheduled macro event window (FOMC/CPI/NFP) likely affecting dispersion?
- Is liquidity unusually constrained (proxy via breadth/vol/credit/treasury-rate shock indicators)?

### B. Non-Detectable (or weakly-detectable) Causal Claims
- A specific stock moved because of one named headline event.
- A specific IPO caused a specific ticker decline.
- Geopolitical event X caused security Y move absent robust event-study evidence.

MCI should avoid these causal statements by design.

## 5) Required Output Type

MCI outputs should be framed as context state, not explanation certainty:
- regime labels
- stress flags
- confidence bands
- event-window markers
- evidence trails

Not:
- single-cause narratives
- autonomous action directives

## 6) Success Criteria for MCI (Assessment-Level)

MCI is useful if it can, deterministically and reproducibly:
1. classify broad market stress context for each run date,
2. identify sector-level versus security-level divergence likelihood,
3. improve operator interpretation quality without changing score/rank behavior in v1,
4. produce auditable evidence logs and no narrative hallucination.

## 7) Governance Note on Naming

GitHub issue number 13 is already a closed historical issue in this repository.  
Recommendation: treat this as a new issue concept (for example ISSUE-18: Market Context Intelligence Assessment/Design) while preserving this document set as the design basis.
