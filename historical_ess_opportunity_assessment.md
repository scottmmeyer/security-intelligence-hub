# Historical ESS Opportunity Assessment
**Phase 7.6D.2 — Replay Historical Signal Integrity Audit**
**Date:** 2026-06-01

---

## Q7: If Historical ESS Archives Are Found, What Is the Upgrade Opportunity?

---

## What Was Found

**Portfolio Manager** (`/Users/scottmmeyer/Projects/portfolio_manager`) contains authentic historical ESS archives:

| Earliest Capture | File | Rows |
|---|---|---|
| 2025-08-18 | EquitySummaryScores-18Aug2025.csv | ~784 |
| 2025-08-24 | EquitySummaryScores-24Aug2025.csv | ~784 |
| 2025-08-25 | EquitySummaryScores-25Aug2025.csv | ~784 |
| 2025-10-19 | EquitySummaryScores-19Oct2025.csv | ~784 |
| 2025-10-29 | EquitySummaryScores-29Oct2025.csv | ~784 |
| 2025-11-18 | EquitySummaryScores-18NOV2025.csv | ~784 |
| 2025-12-11 | EquitySummaryScores_backup_20251211_171503.csv | ~784 |
| 2026-01-08 | EquitySummaryScores-08JAN2026.csv | ~784 |
| 2026-02 through 2026-03 | Multiple files | ~784 each |
| 2026-04 through 2026-06-01 | Dense coverage in processed_inputs/ | ~784 each |

**SANM as a spot check:** SANM appears in the earliest PM archive (Aug 2025) with ESS = 8.9/10 (approximately BULLISH/VERY_BULLISH on Fidelity's 1–10 scale). In the current SIH signal (May 2026): ESS = 4.277778 / 5 (BULLISH). The signal direction is consistent, which is evidence of ESS stability for this particular holding.

---

## Coverage Quality Assessment

### What PM ESS Archives Provide

| Dimension | PM Archive Quality |
|---|---|
| Date coverage | 2025-08-18 through 2026-06-01 (authentic daily near 2026) |
| Symbol coverage | ~784 symbols (portfolio holdings and watchlist — not full universe) |
| Universe coverage ratio | ~31% of SIH's 2,502-row analytical universe |
| Scale format | 1–10 LSEG StarMine scale (needs conversion to SIH 1–5 or text) |
| Zacks column | Present (Zacks Investment Research rating inline) |
| Other providers | Jefferson Research, McLean Capital Management columns present |

### What PM ESS Archives Do NOT Provide

1. **May 2025 ESS data.** The earliest PM archive is Aug 18, 2025 — 96 days after the replay start date of May 14, 2025.

2. **Full analytical universe coverage.** PM covers ~784 holdings (portfolio + watchlist). SIH's replay construction requires ~2,502 full-universe rows. PM data would cover approximately 31% of the needed universe.

3. **A complete substitute ESS source.** Even if PM data were ingested into SIH, the remaining ~69% of the universe (securities not in PM's portfolio view) would still use whatever ESS source SIH provides at that time.

---

## Replay Improvement Opportunity

### Scenario 1: Inject PM Aug 2025 ESS into Historical Replay (Portfolio Holdings Only)

**What would change:** For the ~784 PM-covered symbols appearing in the analytical universe at snapshot_date=2025-05-14, substitute the Aug 2025 ESS scores (most current available) for the current 2026 ESS scores. Reconstruct the composite_score for those symbols.

**Benefit:** Reduces look-ahead from 12 months to ~3 months for covered symbols.

**Limitation:** 96-day gap remains for covered symbols. ~69% of universe still uses 2026 signals. Mixed provenance could create a different class of bias (inconsistent signal dates across the universe).

**Verdict: NOT RECOMMENDED as a retroactive fix.** Mixed-vintage signals across the universe would be harder to reason about than the current uniform (but forward-dated) state.

### Scenario 2: Construct a New Replay Starting Aug 2025

**What would change:** Run a fresh HISTORICAL_VALIDATION replay with snapshot_date=2025-08-18 (or the nearest PM ESS date) and end_date=2026-08-18. PM ESS would provide authentic signals for portfolio-covered securities. Non-covered securities would still use 2026 ESS (because SIH's signal history starts 2026-05-13).

**Benefit:** PM ESS as partial ground truth for portfolio holdings.

**Limitation:** Still only 31% authentic. Non-portfolio symbols use forward signals. The replay still wouldn't be fully authentic.

**Verdict: MARGINAL IMPROVEMENT.** Worth considering as a partial validation but not a replacement for the current 365-day replay evidence.

### Scenario 3: Construct a New Replay Starting May 2026

**What would change:** A replay with snapshot_date=2026-05-13 would have fully authentic ESS, partially authentic Zacks (sparse), partially authentic Danelfin. End date would be approximately 2027-05-13 — one year from now.

**Benefit:** First fully authentic HISTORICAL_VALIDATION replay.

**Limitation:** Returns are not yet available (the period hasn't elapsed). This would be a prospective replay, not a validating historical one.

**Verdict: THIS IS THE CORRECT LONG-TERM APPROACH.** Begin capturing authentic signals now. In May 2027, run the first fully authentic 365-day HISTORICAL_VALIDATION replay. The current daily/weekly signal captures (ESS, Zacks, Danelfin from May 2026 onward) are the foundation for this.

---

## Does Historical ESS Change the Depth Assessment?

**Phase 7.6D** established that replay depth (6-day vs 365-day) matters. The question here is whether finding historical ESS changes the depth meaningfulness.

**Finding:** The 365-day replays ARE deeper evidence of basket performance. The concern is about signal authenticity at the start date, not basket performance measurement. Even with CLASS D signal provenance:
- The stocks selected for the baskets DID exist at 2025-05-14
- The prices used to measure performance ARE authentic
- The baskets DID outperform their benchmarks

What's uncertain is whether a basket selected with authentic 2025 signals would have shown the same outperformance. But the depth (365-day return evidence) remains more informative than 6-day evidence regardless of start-date signal provenance.

**Implication:** Depth-aware scoring (Phase 7.6D recommendation) retains value even after this finding. A 365-day basket member selected by CLASS D signals still has more performance evidence than a 6-day CURRENT_RECOMMENDATION member. The uncertainty is about HOW MUCH to trust the 365-day evidence — it should perhaps be weighted at 0.85× of a fully authentic 365-day replay rather than 1.0×.

---

## Summary: ESS Opportunity Assessment

| Opportunity | Feasibility | Impact |
|---|---|---|
| Inject PM Aug 2025 ESS retroactively | PARTIAL (31% coverage) | Low — mixed-vintage signals create new problems |
| New Aug 2025-start replay | PARTIAL | Marginal — only 31% authentic |
| New May 2026-start replay (prospective) | HIGH | High — first authentic 365-day replay available May 2027 |
| Validate SANM specifically with PM Aug 2025 ESS | YES — SANM in PM archive | Confirms stable BULLISH signal; reduces routing-artifact concern |
| Continuous signal capture (starting now) | ALREADY HAPPENING | High long-term value |

**Recommended action:** Prioritize continuous signal capture (ESS, Zacks, Danelfin) and mark May 2026 as the authentic signal baseline. Plan for the first authentic 365-day HISTORICAL_VALIDATION replay to be run in May 2027. Treat existing 365-day replays as CLASS D evidence with appropriate confidence discount.
