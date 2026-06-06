# Dislocation Scoring Framework
## ISSUE-04A Design Phase — June 5, 2026

---

## 1. Design Constraints

Before evaluating models, the constraints that any acceptable model must satisfy:

1. **Explainability first.** Every dislocation classification must produce a
   human-readable evidence list. "HIGH CONVICTION DISLOCATION: intact thesis +
   87.5% beat rate + ESS BEARISH" is acceptable. An opaque composite score is
   not.

2. **No new data sources.** All inputs must already exist in the system.

3. **No false positives from thin coverage.** Dislocation signals from names
   with analyst_count < 5 or ESS unavailable must be suppressed or downgraded.

4. **Backward compatible.** The scoring logic must be expressible as a stateless
   function over existing fields, callable at API payload time without rerunning
   the full analysis pipeline.

5. **Not a ranking system.** Dislocation is a binary-with-severity classification,
   not a ranked score. Operators should not be sorting positions by "dislocation
   score" — they should be filtering the watchlist by tier (HIGH / MODERATE / WATCH).

---

## 2. Model A — Fundamental-Signal Divergence (FSD)

**Philosophy:** Dislocation is defined exclusively by the gap between FMP
fundamental quality and AI/consensus signal quality. No analyst target data.
No replay data.

**Inputs:**

| Input | Role |
|-------|------|
| thesis_integrity | Primary gate: must be INTACT |
| fundamental_consistency | Secondary gate: CONSISTENT → strengthens |
| beat_rate_8q | Evidence: ≥ 75% required |
| ess_score_text | Divergence signal: BEARISH/NEUTRAL = divergence |
| danelfin_score | Divergence signal: ≤ 3.0 = divergence |
| revenue_growth | Confirming signal: positive = confirms |

**Classification rules:**

```
HIGH CONVICTION DISLOCATION:
  thesis = INTACT
  AND beat_rate ≥ 0.875
  AND (ess = BEARISH or VERY_BEARISH)
  AND (danelfin < 2.0 OR ess = VERY_BEARISH)

MODERATE DISLOCATION:
  thesis = INTACT
  AND beat_rate ≥ 0.75
  AND (ess = BEARISH or NEUTRAL)
  AND danelfin < 3.0

WATCH:
  thesis = INTACT
  AND beat_rate ≥ 0.625
  AND (ess = NEUTRAL or danelfin < 3.0)

NONE:
  All other cases
```

**Strengths:**
- Entirely FMP + ESS-grounded — the most defensible data combination
- Simple rules, fully explainable
- Beat rate directly validates analyst expectations (CII Layer 1 coherence)
- No reliance on price targets or analyst coverage gaps

**Weaknesses:**
- Misses replay-based divergence (Class D1)
- Misses analyst consensus vs. AI divergence (Class B2)
- Beat rate alone can misfire for cyclical sectors where "beats" are structurally
  correlated

**Verdict:** Strong foundation model. Correct for the most common case but
incomplete.

---

## 3. Model B — Consensus-AI Divergence (CAD)

**Philosophy:** Dislocation is defined as the gap between human analyst consensus
(ABR, analyst count) and AI/model signals (ESS, Danelfin).

**Inputs:**

| Input | Role |
|-------|------|
| abr | Primary signal: ≤ 2.0 = bullish consensus |
| analyst_count | Gate: ≥ 10 required |
| ess_score_text | Divergence signal |
| danelfin_score | Divergence signal |
| upside_pct | Confirming signal |

**Classification rules:**

```
HIGH CONVICTION DISLOCATION:
  abr ≤ 1.75 (STRONG BUY)
  AND analyst_count ≥ 20
  AND (ess = BEARISH or danelfin < 2.0)

MODERATE DISLOCATION:
  abr ≤ 2.0 (BUY)
  AND analyst_count ≥ 10
  AND (ess = BEARISH or NEUTRAL)
  AND danelfin < 3.0

WATCH:
  abr ≤ 2.5 AND analyst_count ≥ 5
  AND danelfin < 2.5
  AND upside_pct ≥ 20%
```

**Strengths:**
- Captures analyst-vs-AI divergence which is genuinely interesting
- Analyst count gate prevents thin-coverage false positives
- Directly surfaces the "why do analysts say BUY but the AI says SELL" question

**Weaknesses:**
- ABR coverage is only 65.4% — many portfolio symbols lack this signal
- ABR has systematic upward bias (analysts maintain coverage relationships)
- Upside % in WATCH tier is dangerous — could create anchoring to stale targets
- Model fires only on stocks with sufficient analyst coverage, missing uncovered
  dislocations

**Verdict:** Valid secondary model but should not be primary. Coverage gaps
and bias make ABR unreliable as a primary dislocation driver.

---

## 4. Model C — Multi-Factor Composite (MFC)

**Philosophy:** Dislocation is driven by the convergence of evidence from
fundamentals, analyst consensus, AI signals, and historical replay support.
Multiple streams required for HIGH tier; fewer for lower tiers.

**Inputs:** Full signal inventory (Models A + B + replay)

**Evidence stream scoring:**

```
Stream 1 — Fundamental (FMP):
  INTACT thesis + beat_rate ≥ 0.875 + CONSISTENT → +2 points
  INTACT thesis + beat_rate ≥ 0.75 + CONSISTENT  → +1 point
  INTACT thesis + beat_rate ≥ 0.75 + MIXED        → +0.5 points
  Any other combination                             → 0 points

Stream 2 — Signal Divergence (ESS + Danelfin):
  ESS BEARISH or VERY_BEARISH                      → +1 point
  ESS NEUTRAL                                       → +0.5 points
  Danelfin < 2.0                                    → +1 point
  Danelfin 2.0–3.0                                 → +0.5 points
  (max 2 points from this stream)

Stream 3 — Analyst Consensus (ABR):
  abr ≤ 1.75 AND analyst_count ≥ 20               → +1 point
  abr ≤ 2.0 AND analyst_count ≥ 10                → +0.5 points
  (only contributes when ABR available)

Stream 4 — Replay Evidence (D1):
  replay_supported = True AND replay_percentile ≥ 65  → +1 point
  replay_supported = True AND replay_percentile ≥ 80  → +1.5 points
  (only contributes when replay available)

Total score range: 0 – 6.5 points

Tier assignment:
  ≥ 3.5 points → HIGH CONVICTION DISLOCATION
  ≥ 2.0 points → MODERATE DISLOCATION
  ≥ 1.0 point  → WATCH
  < 1.0 points → NONE
```

**Strengths:**
- Most comprehensive — captures all validated classes
- Handles missing data gracefully (streams contribute when available)
- Distinguishes between evidence quality (both replay + fundamentals → stronger)
- Points system is legible: easy to explain why a name scored 3.5 vs 2.0

**Weaknesses:**
- More complex to implement and test
- Point values need empirical calibration against historical cases
- Risk that operators focus on the point total rather than the evidence narrative
- Requires more field availability validation before deployment

**Verdict:** Correct long-term architecture. Better suited for 04C
(implementation) after the taxonomy is validated in 04B (pilot).

---

## 5. Recommendation: Phased Adoption

**Phase 04B (pilot):** Implement Model A (Fundamental-Signal Divergence)
as the initial dislocation classifier. It is the most defensible, requires
no new data, and is the easiest to validate against known cases (e.g., PSX with
DETERIORATING thesis should NOT fire; LRCX with INTACT thesis + 100% beat +
VERY_BULLISH ESS is NOT dislocated — correct, since signals agree with fundamentals).

**Phase 04C (extension):** Add Class D1 (Replay-Signal Lag) and Class B2
(Analyst-AI Divergence, gated by analyst_count ≥ 10) as additional streams.
The combined output is a simplified version of Model C with 3 streams.

**Phase 04D (full model):** Implement full Model C with calibrated thresholds
after observing 6–12 months of 04B/04C results.

---

## 6. Explainability Requirement

**Every dislocation classification must produce:**

1. Tier: HIGH CONVICTION / MODERATE / WATCH / NONE
2. Class: which taxonomy class(es) triggered
3. Evidence list: 2–4 human-readable facts

Example:

```
Tier: HIGH CONVICTION DISLOCATION
Class: A1 (Fundamental Beat Divergence)
Evidence:
  - Beat rate 87.5% (7 of 8 quarters)
  - Thesis: INTACT (revenue +18.2%, ROIC 28.4%)
  - ESS: BEARISH — signal has not reflected fundamental execution
  - Danelfin: 1.8 — AI model also diverging
```

No compressed scores. No opaque summaries. Full evidence narrative every time.

---

## 7. Thresholds Summary

| Parameter | HIGH CONVICTION | MODERATE | WATCH |
|-----------|----------------|----------|-------|
| beat_rate | ≥ 87.5% | ≥ 75% | ≥ 62.5% |
| ESS (divergence) | BEARISH/VERY_BEARISH | BEARISH or NEUTRAL | NEUTRAL |
| Danelfin (divergence) | ≤ 2.0 | ≤ 3.0 | ≤ 3.5 |
| Thesis | INTACT required | INTACT required | INTACT preferred |
| Replay percentile | ≥ 65 (Class D1 only) | ≥ 65 | ≥ 50 |
| Analyst count (Class B2) | ≥ 20 | ≥ 10 | ≥ 5 |
| ABR (Class B2) | ≤ 1.75 | ≤ 2.0 | ≤ 2.5 |
