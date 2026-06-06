# Dislocation Metrics Framework
## ISSUE-12 Assessment — June 5, 2026

---

## 1. Q2 — What Performance Windows Matter?

### Candidate Windows

| Window | Rationale |
|--------|-----------|
| 30 days | Short-term: captures quick reversion; tests whether signal divergence resolves rapidly |
| 60 days | Medium-term: earnings cycle (~2 months); tests whether analyst upgrades follow fundamentals |
| 90 days | **Primary window** — one calendar quarter; full earnings cycle; standard factor research horizon |
| 180 days | Extended: two quarters; tests persistence of dislocation resolution |
| 365 days | Full-year: maximum conviction test; higher noise but validates long-term information content |

### Recommendation

**Primary measurement window: 90 days**

Rationale:
1. Class A1 (Beat Divergence): the thesis is that analyst models will catch up
   to fundamental execution within one earnings cycle. 90 days captures one
   full quarter, which is when the next earnings report typically confirms
   or refutes the fundamental case.
2. Class D1 (Replay-Signal Lag): replay evidence reflects 6–12 month historical
   periods. 90 days is the minimum window to distinguish signal recovery from noise.
3. Class B2 (Analyst-AI Divergence): analyst consensus is a slower-moving signal.
   90 days allows at least one earnings-driven revision cycle.
4. 90 days is the standard first-pass window in academic factor research and is
   computationally tractable with yfinance historical price data.

**Secondary windows: 30 days and 180 days**

30-day outcomes identify whether any tier is generating quick-reversion alpha
(useful for WATCH tier calibration). 180-day outcomes test persistence.

365-day outcomes are deferred until at least 18 months of detection history
exists (otherwise the first cohort is not yet resolved when the analysis runs).

---

## 2. Q4 — Required Metrics

### Core Metrics (Required)

| Metric | Definition | Purpose |
|--------|-----------|---------|
| **Absolute Return** | (P_t+90 - P_t0) / P_t0 | Baseline performance without benchmark adjustment |
| **Excess Return** | Absolute Return - SPY Return (same window) | Primary alpha measurement |
| **Hit Rate** | % of detections with Excess Return > 0 | Directional accuracy |
| **Median Excess Return** | Median of all excess returns | Robust central tendency; less sensitive to outliers |
| **Mean Excess Return** | Mean of all excess returns | Standard mean; useful with confidence intervals |

### Supporting Metrics (Recommended)

| Metric | Definition | Purpose |
|--------|-----------|---------|
| **Maximum Drawdown** | Max peak-to-trough during holding period | Downside risk per detection |
| **Win/Loss Ratio** | Mean(winners) / abs(Mean(losers)) | Quality of directional accuracy |
| **Cohort Size** | # of detections per tier/class | Statistical significance baseline |
| **Detection Persistence** | Avg consecutive dates with non-NONE tier | How long signals last |
| **Resolution Rate** | % of detections that return to NONE within 90 days | Signal lifecycle |

### Advanced Metrics (Deferred — require ≥ 3 cohorts)

| Metric | When to add |
|--------|------------|
| Sharpe-like ratio (excess return / std dev) | After 5+ cohorts |
| Information Coefficient (IC) | After 10+ detections per class |
| Percentile rank vs. benchmark distribution | After 2 quarters |

---

## 3. Q5 — Class-Level Evaluation

**All classes must be evaluated independently.** The signal mechanisms differ:

| Class | What it tests |
|-------|--------------|
| A1 — Fundamental Beat Divergence | Does strong earnings execution eventually lift market signals? |
| D1 — Replay-Signal Lag | Does historical replay outperformance predict future signal recovery? |
| B2 — Analyst-AI Divergence | Does analyst consensus outperform AI/model signals when they disagree? |
| MULTI_CLASS | Do multi-signal detections produce higher excess returns than single-class? |

### Class-Level Reporting

Report at minimum:
- Cohort size per class
- Hit rate per class (90-day)
- Median excess return per class (90-day)

**MULTI_CLASS as separate category:** YES. MULTI_CLASS detections fire when 2+
independent evidence streams agree. If MULTI_CLASS excess returns are materially
higher than single-class, this would justify:
1. Keeping MULTI_CLASS as the highest-priority watchlist signal
2. Potentially introducing a B3 co-occurrence class in future

If MULTI_CLASS does NOT outperform single-class, it suggests the additional
evidence streams are correlated (not independent) and the multi-class framework
is adding noise rather than signal.

---

## 4. Q6 — Tier-Level Evaluation

**Tiers must also be evaluated independently.** The tier design assumes:
- HIGH_CONVICTION detections outperform MODERATE
- MODERATE detections outperform WATCH
- WATCH detections are marginal but directionally useful

### Tier Hypothesis Matrix

| Tier | Hypothesis | Minimum expected excess return (90d) |
|------|-----------|--------------------------------------|
| HIGH_CONVICTION | Strongest predictive value | +5% vs SPY |
| MODERATE | Moderate predictive value | +2% vs SPY |
| WATCH | Directional accuracy only | Hit rate > 55% |

If the tier ordering is NOT preserved (e.g., MODERATE outperforms HIGH_CONVICTION),
the tier thresholds require recalibration.

### Outcome if Tiers Are Not Predictive

If 90-day outcomes show no tier ordering:
- Do not add HIGH_CONVICTION detections to any scoring system
- Do not use tier as a weighting factor for deployment decisions
- Recalibrate thresholds before adding new dislocation classes

---

## 5. Statistical Significance Requirements

With ~20 non-NONE detections per run and ~monthly run cadence, expect:

| Cohort size | Expected at 90 days | Min for significance |
|------------|---------------------|---------------------|
| Single date detection | 20–30 names | Too small alone |
| Rolling 3-month cohort | 50–100 names | Approaching significance |
| Rolling 6-month cohort | 100–200 names | Statistically interpretable |

**The first meaningful statistical conclusion is achievable ~90 days from the
first tracked detection (September 2026), using a rolling 3-month cohort.**

Do not draw conclusions from fewer than 30 detections per class.
Do not calibrate thresholds from fewer than 2 full cohorts (6 months of data).

---

## 6. Tracking Cadence

| Activity | Frequency |
|---------|-----------|
| Append new detections to tracking CSV | Every PAR run (automatic) |
| Compute 30-day outcomes | Monthly |
| Compute 90-day outcomes | Quarterly (first computation: September 2026) |
| Review tier/class performance | Semi-annually |
| Calibration decision | No earlier than December 2026 |
