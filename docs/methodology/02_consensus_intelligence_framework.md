# 02 — Consensus Intelligence Framework

## Overview

The Security Intelligence Hub implements a four-layer investment intelligence framework. Each layer serves a distinct purpose and contributes different evidence to deployment decisions.

```
┌─────────────────────────────────────────────────────────┐
│           CONSENSUS INTELLIGENCE FRAMEWORK              │
│                                                         │
│  Layer 1 │ ANALYST CONSENSUS                            │
│  Layer 2 │ FUNDAMENTAL VALIDATION                       │
│  Layer 3 │ HISTORICAL VALIDATION (Replay)               │
│  Layer 4 │ PORTFOLIO DISCIPLINE                         │
│                                                         │
│  Deployment Decision = All 4 layers aligned             │
└─────────────────────────────────────────────────────────┘
```

---

## Layer 1 — Analyst Consensus

**Purpose:** Capture what the professional investment community currently believes about a security.

**Core insight:** Professional analysts, collectively, have better information access, more research hours, and deeper sector expertise than most individual investors. Their aggregate consensus represents the distilled view of hundreds of man-years of investment analysis.

**Sources:**
| Source | What It Measures | Weight in Composite |
|--------|-----------------|---------------------|
| ESS (Equity Summary Score) | Aggregated multi-firm analyst consensus | 55% |
| Zacks Rank | Earnings estimate revision momentum | 20% |
| Danelfin AI Score | Machine-learning model across 900+ indicators | 25% |

**Scale:** 0.0–5.0 composite score, where 5.0 represents maximum analyst conviction.

**Output:** `composite_score` → `ess_score_text` (VERY_BULLISH through VERY_BEARISH) → signal direction BULLISH / NEUTRAL / BEARISH

**Critical constraint:** SIH does not follow consensus blindly. Layer 1 is the starting point, not the ending point.

---

## Layer 2 — Fundamental Validation

**Purpose:** Validate whether the business fundamentals support the analyst consensus. Separate the fundamentally sound from the narratively driven.

**Core insight:** Analyst ratings can persist after the underlying business begins to deteriorate. The ESS may still read BULLISH while revenue is declining for the third consecutive quarter. Fundamental validation detects this gap before it costs the portfolio.

**Sources (FMP — Phase 8.0B.1B):**
| Metric | What It Validates |
|--------|-----------------|
| Revenue Growth | Is the business growing? Is growth accelerating? |
| EPS Growth | Is earnings quality improving? |
| Earnings Surprise Rate | Does the company regularly beat analyst expectations? |
| ROIC | Is the business deploying capital well? |
| FCF Yield | Is the business generating real cash? |
| Analyst Grade Revisions | Is consensus trending up or down? |

**Classifications produced:**
- `Thesis Integrity:` INTACT / QUESTIONABLE / DETERIORATING / INSUFFICIENT_DATA
- `Fundamental Consistency:` CONSISTENT / MIXED / CONTRADICTORY / DATA_ANOMALY

**Key outputs:**
- INTACT + CONSISTENT: Fundamentals confirm the consensus. High confidence in deployment.
- INTACT + CONTRADICTORY: Fundamentals strong, signals weak — potential dislocation.
- DETERIORATING + CONSISTENT (bearish): Both say sell.
- DETERIORATING + CONTRADICTORY (bullish): Warning — possible value trap.

---

## Layer 3 — Historical Validation (Replay)

**Purpose:** Determine whether similar signal configurations have historically succeeded. Require empirical evidence before deploying capital.

**Core insight:** A signal that has never worked historically deserves skepticism, regardless of how strong the current consensus reads. Replay requires that the thesis type has produced positive results in historical backtests.

**Source:** SIH Replay System — portfolio simulation against historical signal states.

**Mechanism:** Each holding is evaluated against historical replay runs. `replay_supported = True` means the current signal configuration has appeared in historical winning portfolios.

**Gate function:** Replay is an eligibility gate, not a scoring modifier. A security must have `replay_supported = True` to enter the deployment queue. No replay → no deployment candidacy.

**Why this matters:** This requirement prevents "narrative-only" positions — ideas that sound compelling but have no empirical support. Every deployment queue candidate has been validated by history.

---

## Layer 4 — Portfolio Discipline

**Purpose:** Ensure that capital is deployed intelligently within the portfolio. Right size, right concentration, right allocation target alignment.

**Core insight:** Even perfect security selection is destroyed by poor portfolio construction. Concentration risk, overweight allocation nodes, and runaway position sizes eliminate alpha. Discipline is as important as conviction.

**Mechanisms:**

### CW-DAS (Conviction-Weighted Deployment Attractiveness Score)
Scores each candidate on 7 components:
- Signal quality (composite → 30 pts)
- Replay backing (20 pts)
- Conviction tier (CCL=35, HCA=28)
- Sizing headroom vs. 6% WARN threshold (8 pts)
- Momentum convergence (10 pts)
- Redundancy penalty (−15 for OW allocation nodes)
- Concentration penalty (−20 for oversized positions)

### Allocation Target Alignment
Portfolio is measured against a 40-node allocation target hierarchy (EQUITIES.US.LARGE, etc.). Overweight nodes receive redundancy penalties. Underweight nodes benefit from zero penalties on candidate scoring.

### Capital Rotation Advisor (CRA)
When rebalancing is needed, the CRA identifies optimal capital sources (positions to reduce) and deployment targets (positions to grow), respecting all policy constraints, strategic exit designations, and concentration limits.

### Concentration Controls
- WARN threshold: 6% per position
- MAX threshold: 8% per position
- No single deployment action can breach these limits

---

## The Framework in Practice

**Example: DELL #1 Deployment Candidate (June 2026)**

| Layer | Evidence | Verdict |
|-------|----------|---------|
| Layer 1 | Composite 4.72 / VERY_BULLISH ESS / Danelfin 2.5 | Strong consensus |
| Layer 2 | +18.8% revenue growth, 85.7% beat rate, 18.5% ROIC, INTACT + CONSISTENT | Fundamentals confirm |
| Layer 3 | replay_supported = True | Historical backing confirmed |
| Layer 4 | 1.5% current weight (5.27% sizing headroom), CCL tier, no OW penalties | Optimal deployment candidate |

**Result:** CW-DAS 99.33 / Rank #1 — all four layers aligned.

---

**Example: TSLA — Present in Holdings, Not in Deployment Queue (June 2026)**

| Layer | Evidence | Verdict |
|-------|----------|---------|
| Layer 1 | VERY_BEARISH ESS | Consensus negative |
| Layer 2 | −2.9% revenue, 57.1% beat rate, 3.2% ROIC, DETERIORATING + DATA_ANOMALY | Fundamentals deteriorating |
| Layer 3 | replay_supported = False (VERY_BEARISH signal fails eligibility) | No historical backing |
| Layer 4 | DO_NOT_SELL policy active | Held, not grown |

**Result:** TSLA is retained per policy but blocked from deployment queue. All four layers aligned against addition.

---

## Framework Governance

- Layer 1 changes require `ess_methodology.md` update
- Layer 2 changes require `fmp_integration_philosophy.md` update
- Layer 3 changes require replay system certification
- Layer 4 changes require CW-DAS formula trace update

No layer may be bypassed without documented governance approval.
