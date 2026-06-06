# Dislocation Taxonomy
## ISSUE-04A Design Phase — June 5, 2026

---

## 1. Starting Point: What the System Currently Does

The UI has a `_fmpDislocationType()` function in `app.js` that classifies each
holding as "HIGH CONVICTION", "POTENTIAL", or "NONE" based on a simple two-rule
heuristic:

```javascript
// HIGH CONVICTION: intact thesis + ≥87.5% beat rate + bearish/neutral signal
// POTENTIAL: intact thesis + ≥75% beat rate + Danelfin < 3.0
// NONE: everything else
```

This is a display-only heuristic with no backend definition, no scoring
methodology, no governance, and no approval. It is the starting state ISSUE-04A
is designed to replace.

---

## 2. Proposed SIH Definition of Dislocation

**Dislocation:** A condition where one or more independent evidence streams
indicate that a security's current market signal (price action, AI rating, or
consensus momentum) has diverged from its underlying fundamental or historical
investment case.

Key constraints on this definition:

1. Dislocation is always **security-level** — not portfolio-level or macro-level
2. Dislocation must be **evidenced** — at least two independent signals must
   agree that divergence exists
3. Dislocation is **directional** — it implies that the fundamentals support a
   higher conviction than the market currently reflects (not the reverse)
4. Dislocation is **not a forecast** — it identifies divergence; it does not
   predict reversal timing or magnitude
5. Dislocation is **informational** — it does not trigger automated action

---

## 3. Candidate Dislocation Classes — Evaluation

### Class A: Price vs. Fundamentals

Definition: A security exhibits strong or improving fundamental metrics while
its market signal (ESS, Danelfin, Zacks) reflects weakness or neutrality.

Sub-classes:

**A1 — Beat Rate / Revenue Divergence**
- Revenue growth ≥ sector mean AND beat rate ≥ 75%
- ESS BEARISH/NEUTRAL or Danelfin ≤ 3.0
- Rationale: Analyst consensus has not caught up to improving business reality

**A2 — Margin Expansion / Price Weakness**
- Improving ROIC or FCF yield (trending positive)
- ESS weak or declining
- Rationale: Market punishing near-term noise while fundamentals improve

**A3 — Earnings Beats / Multiple Compression**
- Beat rate ≥ 75%
- ABR HOLD or declining
- Rationale: Analysts downgrading despite consistent execution

**Verdict: CORE CLASS — Include A1 and A3. A2 requires trending data not yet
available (FMP gives point-in-time, not trend). Defer A2.**

---

### Class B: Signal Agreement vs. Market Price

Definition: Multiple consensus sources agree bullish while price action or AI
signals show weakness.

Sub-classes:

**B1 — Consensus Convergence / Signal Divergence**
- ESS BULLISH or VERY_BULLISH
- ABR ≤ 2.0 (BUY or better)
- Zacks ≥ 4.0 (normalized)
- Price near 52-week lows OR Danelfin ≤ 3.0

**B2 — Analyst Agreement / AI Disagreement**
- ABR ≤ 2.0 from ≥ 15 analysts (strong coverage)
- Danelfin ≤ 2.0 (AI model bearish)
- ESS BULLISH or better

**Verdict: VALID CLASS — Include B1 and B2. This class directly validates
whether analyst consensus and AI-based signals are diverging, which is
exactly the kind of intelligence CII is designed to surface. The analyst
count requirement in B2 prevents thin-coverage false positives.**

---

### Class C: Analyst Target Gap

Definition: A significant upside to consensus price target exists alongside
strong analyst coverage and consensus quality.

Sub-classes:

**C1 — High Coverage Upside**
- upside_pct ≥ 20%
- analyst_count ≥ 15
- ABR ≤ 2.5 (BUY or MODERATE BUY)

**C2 — Target Conviction**
- upside_pct ≥ 30%
- analyst_count ≥ 10
- ABR ≤ 2.0

**Verdict: PARTIAL — Include with caution. Analyst price targets are upward-
biased and lag market events. Upside % alone is not evidence of dislocation.
However, large upside from broad, high-quality coverage alongside a weak AI
signal is informative. Class C should require co-occurrence with another class
signal (not standalone). Flag as ANALYST TARGET DIVERGENCE sub-class within
Class B.**

---

### Class D: Replay Divergence

Definition: A replay-supported security (with historical replay evidence) is
currently receiving below-median AI signals despite that evidence.

Sub-classes:

**D1 — Replay-Supported / Signal Lag**
- replay_supported = True
- replay_percentile ≥ 65th
- ESS NEUTRAL or lower, OR Danelfin ≤ 2.5

**D2 — High Replay / Low Current Conviction**
- replay_percentile ≥ 80th
- composite_score ≤ 3.5

**Verdict: CORE CLASS — Include D1. This is the most replay-grounded class and
aligns most directly with SIH's historical evidence foundation. A security
with strong historical replay and current signal weakness is exactly the kind
of dislocation SIH should highlight. D2 is a subset of D1 and can be captured
by the same logic.**

---

### Class E: Portfolio Dislocation

Definition: An existing holding that appears to be experiencing dislocation
relative to its portfolio context — improving conviction signals but reduced
weight or target weight gap.

Sub-classes:

**E1 — Signal Improving / Weight Declining**
- opportunity_flag = ACCUMULATE (or was ACCUMULATE recently)
- current_weight_pct < target_weight_pct (below mandate target)
- ESS BULLISH

**E2 — High Conviction / Under-Deployed**
- narrative_tier = CCL or HCA
- current_weight_pct significantly below threshold
- no overweight constraint in allocation node

**Verdict: VALID but DIFFERENT — This class describes portfolio dislocation,
not security dislocation. It overlaps heavily with the existing CW-DAS
deployment queue (which already ranks under-deployed high-conviction names).
Class E should NOT be a standalone dislocation type — it is better surfaced
via the deployment queue with its headroom_pct field. Exclude from the
Dislocation Watchlist definition. Retain as a CW-DAS concern.**

---

## 4. Final Taxonomy — Approved Classes

| Class | Name | Core Signal |
|-------|------|------------|
| A1 | Fundamental Beat Divergence | Beat rate + revenue growth vs. signal weakness |
| A3 | Analyst Beat / Consensus Lag | Earnings beats with deteriorating analyst consensus |
| B1 | Consensus-Signal Split | Multi-source bullish vs. AI weakness |
| B2 | Analyst-AI Divergence | ABR/analyst-driven bullish vs. Danelfin/ESS bearish |
| C (co-occurrence) | Target Gap Signal | High upside + strong coverage only when paired with another class |
| D1 | Replay-Signal Lag | Replay evidence vs. current signal weakness |

### Excluded Classes

| Class | Reason for Exclusion |
|-------|---------------------|
| A2 (Margin trend) | Requires trending FMP data not yet available |
| E (Portfolio dislocation) | Captured by CW-DAS deployment queue and headroom_pct |
| Raw price action | SIH does not source live price feeds beyond Yahoo supplemental |

---

## 5. Severity Tiers

| Tier | Name | Criteria |
|------|------|---------|
| 1 | HIGH CONVICTION DISLOCATION | 2+ classes trigger simultaneously |
| 2 | MODERATE DISLOCATION | 1 class triggers with ≥ 2 confirming signals |
| 3 | WATCH | 1 class triggers with limited confirmation |
| 0 | NONE | No dislocation class triggered |

---

## 6. What Dislocation Is NOT

1. A price target (not "the stock will go up")
2. A buy signal (not a trade instruction)
3. A reversal prediction (no timing claim)
4. A criticism of the CW-DAS ranking (a #12-ranked name can still be a HIGH
   CONVICTION DISLOCATION — rank is about deployment priority, not
   fundamental quality)
5. A replacement for STI classification or replay support — those remain the
   primary signals for deployment decisions
