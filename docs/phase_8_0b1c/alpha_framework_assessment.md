# Alpha Framework Assessment — Phase 8.0B.1C

## CII Expected Alpha Sources — Relative Importance

Based on the top-25 analysis and CII architecture:

| Layer | Alpha Source | Estimated Relative Contribution | Rationale |
|-------|-------------|--------------------------------|-----------|
| 1 | Analyst Consensus (ESS + Zacks + Danelfin) | **50%** | Primary filter — all 25 candidates are replay-backed consensus bullish. This is the gate that matters most. |
| 3 | Historical Validation (Replay) | **25%** | Hard eligibility gate — non-replay candidates don't enter the queue regardless of fundamentals or consensus. Acts as an empirical quality control. |
| 4 | Portfolio Discipline (CW-DAS, position sizing) | **15%** | Ensures capital flows efficiently to the right candidates without runaway concentration. Alpha preservation more than alpha generation. |
| 2 | Fundamental Validation | **10%** | Currently display-only. High potential to contribute via error-detection (catching DETERIORATING theses before they cost the portfolio). |

### Key observation
Replay (Layer 3) contributes more to the current alpha framework than Fundamentals (Layer 2) — even though the CII framework lists them in a different order. The reason: Replay is a binary hard gate (20 points in CW-DAS) while Fundamentals are currently display-only. If fundamentals are integrated via Model B, their contribution would rise to ~15–20%.

---

## Would Integrating Fundamentals Improve Alpha Generation or Decision Confidence?

**Answer: Both — but more importantly, it improves error reduction.**

### Alpha Generation Case
Integrating beat rate and thesis integrity does not directly generate alpha. The consensus layer already captures analyst views. What fundamentals add is **error reduction** — preventing capital deployment into securities where the thesis is breaking down before the consensus catches up.

The PSX example is illustrative: VERY_BULLISH ESS at #4 despite DETERIORATING fundamentals. Without fundamental integration, the system would direct capital toward PSX. With Model B, PSX drops to ~#11 and the capital flows instead to LRCX (#3), which has 100% beat rate, +23.7% revenue growth, and 42.8% ROIC.

**Alpha comes from directing capital away from the PSX type and toward the LRCX type.**

### Decision Confidence Case
For securities like AEIS (#24, NEUTRAL ESS but 100% beat rate and +21.4% revenue), a fundamental modifier provides the operator with a quantitative signal that the business quality is better than the ESS reads. This doesn't change the ranking dramatically but improves operator confidence.

---

## Sectors Where Beat Rate May Be Misleading

| Sector | Issue | Implication |
|--------|-------|-------------|
| Solar / Clean Energy | Analysts systematically overestimate; beat rate < 50% is common | Don't penalize FSLR-type cases for low beat rate |
| Biotech pre-revenue | Beat rate N/A or sparse | Cover via `INSUFFICIENT_DATA` handling |
| Commodity producers | Revenue beat rate varies with commodity price, not management quality | Beat rate more valid for earnings than revenue |
| Regional banks | Beat rates are compressed (narrow spread) | Beat rate less informative than ROIC |

**Recommendation:** Apply beat_rate modifier only where coverage = FULL AND the company has ≥6 quarters of history. Cap the penalty in sectors where beat rate is systematically low (identified via sector flag).

---

## Conclusion

Integrating fundamentals via Model B would:
1. Raise the Layer 2 contribution from ~0% (current) to ~15%
2. Reduce the error rate from DETERIORATING-thesis deployments
3. Increase capital efficiency by promoting high-conviction INTACT+CONSISTENT candidates
4. Strengthen CII's "validates consensus against fundamentals" philosophy statement

**The expected outcome is improved alpha via reduced error, not new alpha source generation.** This is appropriate given CII's philosophy — we are not claiming fundamentals independently predict returns, but that they validate consensus signals.
