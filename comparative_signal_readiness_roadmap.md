# Comparative Signal Readiness Roadmap
**Phase 7.7B — Deliverable Q7**
**Generated:** 2026-06-01

---

## 1. Purpose

Define the specific archive depth, observation count, and price history milestones that must be met before each comparative signal effectiveness study can be conducted with credibility. This roadmap answers the question: **When can we legitimately re-run Phase 7.7A?**

---

## 2. Phase 8.x Study Schedule

| Study | Phase | Target Date | Description |
|-------|-------|-------------|-------------|
| 30-Day Pilot | Phase 8.1 | 2026-07-15 | First 30-day return pairs for Zacks and Danelfin |
| 90-Day Pilot | Phase 8.2 | 2026-09-01 | First credible multi-horizon comparison |
| 6-Month Comparative Authority | Phase 8.3 | 2026-12-01 | Primary re-run of Phase 7.7A |
| 12-Month Full-Cycle Comparative | Phase 8.4 | 2027-06-01 | Complete market-cycle validation |

---

## 3. Milestone Definitions

### Milestone 1 — Phase 8.1: 30-Day Pilot (Target: 2026-07-15)

**Purpose:** Establish whether Zacks and Danelfin 30-day returns are now computable. Not a full effectiveness study — a feasibility check.

**Minimum archive depth requirements:**

| Provider | Minimum Captures | Minimum Observations | Minimum Symbols | Min Archive Span |
|----------|-----------------|---------------------|-----------------|-----------------|
| Zacks | 2 full-universe | 5,000 | 2,000 | 6 weeks |
| Danelfin | 2 full-universe | 1,500 | 600 | 6 weeks |
| ESS | Existing archive | 32,805 (confirmed) | — | Confirmed |

**Price history requirement:**
- Price data must be available through at least 30 calendar days after the first post-governance capture date (2026-06-01)
- **Required price data end date:** ≥ 2026-07-01
- This is the **single blocking dependency** for Phase 8.1

**Return pair minimum per bucket for meaningful statistics:**

| Metric | Minimum n per bucket |
|--------|---------------------|
| Average return | 50 |
| Median return | 50 |
| Win rate | 100 (for ±5% confidence) |
| Spearman ρ | 5 buckets with n ≥ 30 each |

At 2 Zacks captures (~2,568 obs each), expected 30-day pairs per bucket: ~200–500. **Sufficient for pilot analysis.**

**Study scope:**
- Compute 30-day returns for all Zacks and Danelfin observations from 2026-06-01 captures
- Compare bucket-level averages, medians, win rates against ESS bucket-level results from Phase 7.6G
- Do NOT use this to change composite weights — pilot only

**Go/no-go criteria:**
- [ ] Price data extends to ≥ 2026-07-01
- [ ] At least 1 Zacks full-universe capture since 2026-06-01
- [ ] At least 1 Danelfin full-universe capture since 2026-06-01
- [ ] Both masters pass all quality gates

---

### Milestone 2 — Phase 8.2: 90-Day Pilot (Target: 2026-09-01)

**Purpose:** First multi-horizon effectiveness comparison. Tests whether ESS, Zacks, and Danelfin agree on short (30d) vs. medium (90d) time horizons.

**Minimum archive depth requirements:**

| Provider | Minimum Captures | Minimum Observations | Minimum Symbols | Min Archive Span |
|----------|-----------------|---------------------|-----------------|-----------------|
| Zacks | 8 full-universe | 20,000 | 2,400 | 3 months |
| Danelfin | 8 full-universe | 5,800 | 700 | 3 months |
| ESS | Existing + ongoing | 40,000+ | 2,800+ | 14+ months |

**Price history requirement:**
- Price data must extend ≥ 90 calendar days beyond the first post-governance capture
- **Required price data end date:** ≥ 2026-09-01

**Minimum n per bucket for 90d study:**

| Metric | Minimum n per bucket |
|--------|---------------------|
| Average return | 100 |
| Win rate | 200 |
| Spearman ρ | 5 buckets with n ≥ 100 each |

At 8 Zacks captures, expected 90-day pairs per bucket: ~500–1,200. Marginally sufficient.

**Study scope:**
- 30-day and 90-day return effectiveness comparison across all three signals
- Persistence comparison using 8+ dates (credible but short)
- Monotonicity assessment with first meaningful Zacks/Danelfin data
- Preliminary verdict on whether ESS dominance is genuine or archive-driven

**Go/no-go criteria:**
- [ ] Price data extends to ≥ 2026-09-01
- [ ] ≥ 8 Zacks full-universe captures since 2026-06-01 with ≤ 1 gap > 14 days
- [ ] ≥ 8 Danelfin full-universe captures since 2026-06-01 with ≤ 1 gap > 14 days
- [ ] At least one market correction or volatility event in the observation window

---

### Milestone 3 — Phase 8.3: 6-Month Comparative Authority Study (Target: 2026-12-01)

**Purpose:** Primary re-run of Phase 7.7A. This is the first study that can produce a credible answer to the Phase 7.7A question: "Is ESS genuinely stronger, or just better-covered?"

**This is the minimum archive required to change composite weights.**

**Minimum archive depth requirements:**

| Provider | Minimum Captures | Minimum Observations | Minimum Symbols | Min Archive Span |
|----------|-----------------|---------------------|-----------------|-----------------|
| Zacks | 26 full-universe | 66,000 | 2,400 | 6 months |
| Danelfin | 26 full-universe | 18,800 | 700 | 6 months |
| ESS | Existing + ongoing | 60,000+ | 2,800+ | 18+ months |

**Price history requirement:**
- Price data must extend ≥ 30 calendar days beyond the study date (for 30d returns from November captures)
- **Required price data end date:** ≥ 2027-01-01

**Study scope:**
- Full Phase 7.7A re-run with sufficient data for all 7 questions
- 30-day, 60-day, and 90-day return effectiveness comparison
- Monotonicity with Spearman ρ on all three signals
- Persistence with ≥ 25 dates per signal (credible sample)
- Volatility ordering comparison
- Revised `signal_authority_scorecard.csv`
- New `comparative_signal_authority_recommendation.md` with updated verdict

**Eligible verdicts at Phase 8.3:**
- A. ESS_CONFIRMED_DOMINANT — ESS significantly outperforms on all metrics
- B. ESS_MARGINALLY_DOMINANT — ESS leads on some metrics, Zacks comparable on others
- C. SIGNALS_COMPARABLE — No material difference; weights justified by coverage breadth only
- D. ZACKS_COMPETITIVE — Zacks matches or exceeds ESS on return effectiveness
- E. INSUFFICIENT_COMPARATIVE_EVIDENCE — only if data gaps prevent analysis (should not recur)

**Weight change authority:** Phase 8.3 is the earliest point at which composite weight changes are evidence-justified. Any weight adjustments require verdict B, C, or D — not E.

**Go/no-go criteria:**
- [ ] Price data extends to ≥ 2027-01-01
- [ ] ≥ 26 Zacks full-universe captures with ≤ 2 gaps > 14 days
- [ ] ≥ 26 Danelfin full-universe captures with ≤ 2 gaps > 14 days
- [ ] At least one earnings season fully captured (Q2 2026 or Q3 2026)
- [ ] At least one market correction event (≥10% drawdown on S&P 500) in window, OR explicit acknowledgment of single-regime limitation

---

### Milestone 4 — Phase 8.4: 12-Month Full-Cycle Comparative (Target: 2027-06-01)

**Purpose:** Full market-cycle validation. By 2027-06-01, all three signals will have been observed through multiple market regimes. This is the study required to make permanent, durable weight decisions.

**Minimum archive depth requirements:**

| Provider | Minimum Captures | Minimum Observations | Minimum Symbols | Min Archive Span |
|----------|-----------------|---------------------|-----------------|-----------------|
| Zacks | 52 full-universe | 133,000 | 2,400 | 12 months |
| Danelfin | 52 full-universe | 37,600 | 700 | 12 months |
| ESS | Existing + ongoing | 85,000+ | 2,800+ | 24+ months |

**Price history requirement:**
- **Required price data end date:** ≥ 2027-07-01

**Study scope:**
- Full Phase 7.7A re-run with multi-regime data
- Regime-stratified analysis: bull/bear/neutral sub-periods analyzed separately
- Signal correlation matrix: do Zacks and Danelfin add independent information relative to ESS?
- UCF weight optimization study: if signals show different strengths in different regimes, should UCF weights be regime-adaptive?
- Final composite weight recommendation with confidence intervals

---

## 4. Price History Dependency Tracking

| Study | Price Data Required Through | Current Price Data End | Gap (as of 2026-06-01) |
|-------|---------------------------|----------------------|------------------------|
| Phase 8.1 | 2026-07-01 | 2026-05-26 | **36 days** |
| Phase 8.2 | 2026-09-01 | 2026-05-26 | **98 days** |
| Phase 8.3 | 2027-01-01 | 2026-05-26 | **220 days** |
| Phase 8.4 | 2027-07-01 | 2026-05-26 | **401 days** |

**Action required:** Price history must be extended. This is a separate work item from signal archive governance but is a blocking dependency for all Phase 8.x studies.

---

## 5. ESS Archive Continuation

ESS archive must also continue to grow. The Phase 8.3 and 8.4 comparisons require ESS to cover the same study window as Zacks and Danelfin.

- ESS captures should continue at the current cadence (~weekly full-universe from Fidelity)
- ESS archive must extend to at least 2026-12-01 for Phase 8.3
- ESS archive must extend to at least 2027-06-01 for Phase 8.4

---

## 6. Readiness Scorecard Template

For each Phase 8.x study, evaluate before proceeding:

| Check | Required | Current (2026-06-01) | Status |
|-------|----------|---------------------|--------|
| Zacks captures | ≥ 26 (Phase 8.3) | 1 full | NOT READY |
| Danelfin captures | ≥ 26 (Phase 8.3) | 0 full (1 large) | NOT READY |
| Zacks observations | ≥ 66,000 (Phase 8.3) | 3,373 | NOT READY |
| Danelfin observations | ≥ 18,800 (Phase 8.3) | 2,266 | NOT READY |
| Price data end date | ≥ 2027-01-01 (Phase 8.3) | 2026-05-26 | NOT READY |
| ESS captures (ongoing) | Continued | 36 dates | READY |
| Quality gates implemented | Yes | Defined (not yet coded) | PARTIAL |

**Current status (2026-06-01): NOT READY for any Phase 8.x comparative study.**

This is expected. Archive governance begins today. Re-evaluate readiness at Phase 8.1 target date (2026-07-15).

---

## 7. Roadmap Summary

```
2026-06-01  ← Archive governance established (Phase 7.7B)
             Start systematic Zacks + Danelfin capture

2026-07-15  ← Phase 8.1: 30-Day Pilot
             First 30d return pairs for Zacks + Danelfin
             Feasibility check only; no weight changes

2026-09-01  ← Phase 8.2: 90-Day Pilot
             Multi-horizon comparison begins
             Preliminary ESS vs. Zacks vs. Danelfin assessment

2026-12-01  ← Phase 8.3: 6-Month Comparative Authority Study
             PRIMARY RE-RUN OF PHASE 7.7A
             Earliest date to change composite weights
             Verdict: A, B, C, D, or E

2027-06-01  ← Phase 8.4: 12-Month Full-Cycle Comparative
             Multi-regime validation
             Durable weight decisions
             UCF weight optimization study eligible
```
