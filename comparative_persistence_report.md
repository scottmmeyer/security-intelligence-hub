# Comparative Persistence Report
**Phase 7.7A — Deliverable Q5**
**Generated:** 2026-06-01

---

## 1. Purpose

Measure signal persistence for ESS, Zacks, and Danelfin: the probability that a security's rating bucket remains unchanged from one observation to the next. High persistence indicates a stable signal that does not generate excessive portfolio churn. Low persistence may indicate noise or over-reactivity to short-term market movements.

---

## 2. Methodology

For each signal, identify all symbols with observations on at least two consecutive dates. For each symbol-date pair, record whether the 5pt bucket is the same on the next observation date. Persistence = count(unchanged) / count(total transitions).

**Important constraint:** Zacks and Danelfin have only 5 observation dates over a 15-day window (2026-05-14 to 2026-05-29). ESS has 36 observation dates over ~10.5 months (2025-08-18 to 2026-06-01). These measurement bases are not directly comparable. Persistence numbers must be interpreted in context of archive depth.

---

## 3. ESS Persistence — High Confidence

### 3.1 Summary

| Metric | Value |
|--------|-------|
| Total transitions | 51,648 |
| Observation dates | 36 |
| Archive span | ~10.5 months |
| Average persistence | **79.0%** |
| Confidence | **HIGH** |

### 3.2 Persistence by Bucket

| Bucket | Label | Persist Count | Total Transitions | Persistence Rate |
|--------|-------|---------------|-------------------|-----------------|
| 1 | VERY_BEARISH | 3,236 | 3,987 | **81.2%** |
| 2 | BEARISH | 7,490 | 9,346 | **80.1%** |
| 3 | NEUTRAL | 12,380 | 15,284 | **81.0%** |
| 4 | BULLISH | 11,444 | 14,865 | **77.0%** |
| 5 | VERY_BULLISH | 6,273 | 8,166 | **76.8%** |

### 3.3 Interpretation

ESS persistence of 79.0% means that in 4 of 5 weekly observations, a security's sentiment bucket does not change. The extremes (bucket 1 and 5) are slightly more persistent than the middle (bucket 4 and 5 show slightly lower persistence — consistent with the natural tendency for bullish positions to revert toward neutral over time).

**Duration analysis (from Phase 7.6G):** Median time in each bucket:
- VERY_BEARISH: 18 trading days
- BEARISH: 18 trading days
- NEUTRAL: 18 trading days
- BULLISH: 20 trading days
- VERY_BULLISH: 24 trading days

This indicates a typical rating lasts 3–5 weeks before migrating. Sufficient for weekly or bi-weekly portfolio rebalancing cycles.

**Confidence basis:** 51,648 transitions from a 10.5-month, 36-date archive spanning multiple market regimes (bull, correction, recovery). The sample is large enough to distinguish structural persistence from short-term artifact.

---

## 4. Zacks Persistence — Low Confidence

### 4.1 Summary

| Metric | Value |
|--------|-------|
| Total transitions | 740 |
| Observation dates | 5 |
| Archive span | 15 days |
| Average persistence | **90.1%** |
| Confidence | **LOW** |

### 4.2 Persistence by Bucket

| Bucket | 5pt | Persist Count | Total Transitions | Persistence Rate |
|--------|-----|---------------|-------------------|-----------------|
| 1 (Rank 5 — Strong Sell) | 1 | 6 | 8 | 75.0% |
| 2 (Rank 4 — Sell) | 2 | 49 | 54 | 90.7% |
| 3 (Rank 3 — Hold) | 3 | 374 | 399 | 93.7% |
| 4 (Rank 2 — Buy) | 4 | 137 | 165 | 83.0% |
| 5 (Rank 1 — Strong Buy) | 5 | 101 | 114 | 88.6% |

**Note on bucket 1:** Only 8 transitions observed. The 75.0% rate is not statistically meaningful.

### 4.3 The 15-Day Artifact Problem

Zacks persistence appears to be **90.1%** — higher than ESS's 79.0%. This should not be interpreted as evidence that Zacks is more stable than ESS. Three compounding factors inflate the number:

1. **Analyst revision cycle:** Zacks ranks are updated based on earnings revisions, price targets, and broker recommendations. The typical revision cycle is 4–8 weeks, not 3 days. Capturing 5 dates over 15 days means most ratings were last revised before the observation window began — they appear "persistent" simply because the analyst hasn't changed their view yet.

2. **Short window = no mean reversion:** In a 10.5-month ESS archive, stocks naturally cycle through multiple regime changes, earnings announcements, and sector rotations — all of which produce genuine transitions. In 15 days, none of these have time to materialize.

3. **Small transition pool:** 740 transitions from 693 symbols × 5 dates. The symbols eligible for transitions are those covered in multiple Zacks snapshots — already a selected subsample. Missing snapshots (e.g., 2026-05-21 only has 78 rows) further bias toward symbols where the vendor maintained a consistent rating.

**The Zacks 90.1% persistence number is an artifact of archive depth, not structural signal stability.**

---

## 5. Danelfin Persistence — Low Confidence

### 5.1 Summary

| Metric | Value |
|--------|-------|
| Total transitions | 1,310 |
| Observation dates | 5 |
| Archive span | 15 days |
| Average persistence | **88.9%** |
| Confidence | **LOW** |

### 5.2 Persistence by Bucket

| Bucket | Persist Count | Total Transitions | Persistence Rate |
|--------|---------------|-------------------|-----------------|
| 1 (weakest) | 8 | 12 | 66.7% |
| 2 | 534 | 578 | 92.4% |
| 3 | 218 | 290 | 75.2% |
| 4 | 389 | 412 | 94.4% |
| 5 (strongest) | 15 | 18 | 83.3% |

**Note:** Buckets 1 and 5 have 12 and 18 transitions respectively. The rates are not statistically reliable.

### 5.3 Interpretation

Danelfin's 88.9% persistence faces the same 15-day artifact problem as Zacks. Additionally:

- Danelfin uses a continuous 1–10 scale; 5pt bucketization rounds half-point scores into shared bins. Minor score changes (e.g., from 2.0 to 2.5) stay in the same bucket and register as "persistent" even though the underlying signal changed.
- The 5pt rounding naturally suppresses apparent transitions, artificially inflating persistence.

Danelfin's granular half-point scale means the signal actually updates more frequently than its bucket persistence implies — but we cannot measure this with current data.

**The Danelfin 88.9% persistence number is an artifact of both archive depth and bucket rounding, not structural signal stability.**

---

## 6. Comparative Summary

| Signal | Avg Persistence | Total Transitions | Archive Span | Confidence |
|--------|----------------|-------------------|--------------|------------|
| ESS | 79.0% | 51,648 | 10.5 months (36 dates) | **HIGH** |
| Zacks | 90.1% | 740 | 15 days (5 dates) | **LOW** |
| Danelfin | 88.9% | 1,310 | 15 days (5 dates) | **LOW** |

**Do not interpret the Zacks/Danelfin numbers as evidence they are "more persistent" than ESS.** The numerically higher values are a direct consequence of a 15-day observation window that prevents any meaningful rating changes from appearing.

The only interpretable comparison:
- ESS persistence (79.0%) is based on a genuine multi-regime sample. This is a real, measured persistence rate.
- Zacks/Danelfin persistence are observations of a 15-day snapshot. They carry no information about long-run stability.

---

## 7. ESS Persistence vs. Required Portfolio Turnover

A 79% weekly persistence rate implies approximately 21% of positions see a bucket change each week. For a 100-security portfolio with weekly rebalancing, this means ~21 rating changes per week, of which only a fraction would cross a decision threshold (e.g., exit <2, enter >4). Observed net churn in production deployment is consistent with this figure.

**ESS persistence is operationally sufficient for weekly and bi-weekly rebalancing cycles.** No persistence-driven constraint changes are indicated.

---

## 8. Verdict

**Q5: Is signal persistence comparable across ESS, Zacks, and Danelfin?**

**ANSWER: NO — E. INSUFFICIENT_COMPARATIVE_EVIDENCE**

ESS persistence (79.0%) is based on a reliable, multi-regime, high-n sample. Zacks (90.1%) and Danelfin (88.9%) persistence measurements are 15-day artifacts that cannot be meaningfully compared to ESS.

**Required for proper persistence comparison:** 6+ months of Zacks and Danelfin archive at weekly capture frequency (target: 200+ transitions per bucket per signal). Earliest viable comparison: Phase 8.x, 2026-12-01.
