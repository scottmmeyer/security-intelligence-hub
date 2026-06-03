# Signal Capture Cadence Plan
**Phase 7.7B — Deliverable Q4**
**Generated:** 2026-06-01

---

## 1. Purpose

Define the required capture cadence for Zacks and Danelfin archives to enable evidence-based comparative signal authority studies in Phase 8.x. All projections assume capture starting 2026-06-01.

---

## 2. Minimum vs. Preferred Cadence

| Tier | Frequency | Captures/Month | Captures/6 Months |
|------|-----------|----------------|-------------------|
| **Minimum** | Weekly (Monday or Tuesday) | 4–5 | ~26 |
| **Preferred** | Twice-weekly (Monday + Thursday) | 8–9 | ~52 |
| **Enhanced** | Three times weekly | 12–13 | ~78 |

**Recommendation:** Operate at **Preferred** cadence (twice-weekly). The marginal cost of a second weekly capture is low, and doubled capture frequency provides:
- Better persistence measurement (more transition pairs)
- Earlier detection of provider data gaps
- Faster identification of anomalies (out-of-range scores, coverage drops)

---

## 3. Expected Archive Growth Projections

### 3.1 Minimum Cadence (Weekly)

Assuming full-universe Zacks (~2,600 symbols) and full Danelfin (~760 symbols) per capture:

| Milestone | Captures | Zacks Observations | Danelfin Observations | Calendar Date |
|-----------|----------|--------------------|-----------------------|---------------|
| Baseline (today) | 1 full | 2,568 | 782 | 2026-06-01 |
| 30-day pilot | ~5 | ~15,000 | ~4,600 | 2026-07-01 |
| 60-day window | ~9 | ~26,000 | ~8,000 | 2026-08-01 |
| 90-day pilot | ~14 | ~41,000 | ~12,500 | 2026-09-01 |
| 6-month comparative | ~26 | ~70,000 | ~21,500 | 2026-12-01 |
| 12-month comparative | ~52 | ~137,000 | ~43,000 | 2027-06-01 |

### 3.2 Preferred Cadence (Twice-Weekly)

| Milestone | Captures | Zacks Observations | Danelfin Observations | Calendar Date |
|-----------|----------|--------------------|-----------------------|---------------|
| Baseline (today) | 1 full | 2,568 | 782 | 2026-06-01 |
| 30-day pilot | ~9 | ~25,000 | ~7,600 | 2026-07-01 |
| 60-day window | ~18 | ~49,000 | ~14,900 | 2026-08-01 |
| 90-day pilot | ~26 | ~71,000 | ~21,600 | 2026-09-01 |
| 6-month comparative | ~52 | ~137,000 | ~41,600 | 2026-12-01 |
| 12-month comparative | ~104 | ~270,000 | ~82,000 | 2027-06-01 |

---

## 4. Forward Return Study Readiness by Cadence

### 4.1 First Available 30-Day Return Pairs

- **Earliest possible:** First capture on or before 2026-07-01 will have at least one 30-day window if price data extends to 2026-08-01+
- **Requirement:** Price history data must be extended past 2026-05-26 (current end date). The price data gap is a **separate critical action item.**
- **Projected:** 30-day effectiveness study becomes viable when price data catches up to captures from 30+ days ago. Assuming price data update by 2026-07-15: first 30-day pairs from captures starting 2026-06-01 will be available ~2026-07-15.

### 4.2 Effectiveness Study Readiness Dates

| Study Type | Minimum Archive Required | Minimum Cadence | Earliest Available |
|------------|--------------------------|-----------------|-------------------|
| 30-day return pilot (Zacks) | 1 full capture + 30d price gap | Weekly | **2026-07-01** |
| 30-day return pilot (Danelfin) | 1 full capture + 30d price gap | Weekly | **2026-07-01** |
| 90-day return comparison | 3 captures separated by 30d each | Weekly | **2026-09-01** |
| Persistence study (1 month) | ~4 captures | Weekly | **2026-07-01** |
| Persistence study (credible) | ~25 captures | Weekly | **2026-12-01** |
| 6-month comparative authority | 26+ captures, all 3 signals | Weekly | **2026-12-01** |
| 12-month full-cycle comparative | 52+ captures, multi-regime | Weekly | **2027-06-01** |

---

## 5. Critical Dependency: Price Data Extension

**Current price data ends: 2026-05-26**

All forward-return effectiveness studies depend on price history extending past the capture dates. Without price data beyond 2026-05-26:
- Captures from 2026-06-01 onward have **zero forward return pairs**
- The same archive depth problem from Phase 7.7A will repeat

**Required action (separate from signal capture):** Implement ongoing weekly price history ingestion for the investable universe. Target: price data current within 7 days at all times.

**If price data is not extended, the 30-day return study target date of 2026-07-01 is not achievable**, and all downstream study dates slide by the same number of days that price data lags.

---

## 6. Capture Scheduling

### 6.1 Recommended Weekly Capture Day

| Provider | Recommended Day | Rationale |
|----------|----------------|-----------|
| Zacks | **Tuesday** | Zacks updates are primarily driven by broker revisions published Monday–Tuesday. Capturing Tuesday maximizes freshness. |
| Danelfin | **Tuesday** | Align with Zacks for operational simplicity. |
| Both (preferred 2nd capture) | **Friday** | Captures the week's close-of-market information. |

### 6.2 Holiday and Gap Handling

- If the scheduled capture day falls on a US market holiday, capture on the next trading day
- If a capture is missed, do NOT attempt to backfill with a delayed capture on a different date — the file date must match the actual capture date
- Log all missed captures in the quality gates report

### 6.3 Minimum Consecutive Coverage

For the 6-month study (Phase 8.x) to be credible, at minimum:
- **No gap > 14 calendar days** between consecutive captures
- At least 20 of 26 expected monthly captures must be present (77% capture rate minimum)
- At least 1 capture per calendar month from June 2026 through November 2026

---

## 7. Archive Size Projections

At preferred cadence (twice-weekly, 2,568 Zacks + 760 Danelfin per capture):

| Horizon | Zacks File Count | Zacks Total Size (est.) | Danelfin File Count | Danelfin Total Size (est.) |
|---------|-----------------|------------------------|--------------------|-----------------------------|
| 30 days | ~9 | ~630 KB | ~9 | ~180 KB |
| 6 months | ~52 | ~3.6 MB | ~52 | ~1.0 MB |
| 12 months | ~104 | ~7.3 MB | ~104 | ~2.0 MB |

Archive sizes are manageable. No compression or partitioning is needed in the 12-month horizon.

---

## 8. Cadence Summary

| Item | Decision |
|------|----------|
| **Minimum cadence** | Weekly |
| **Recommended cadence** | Twice-weekly (Monday/Tuesday + Friday) |
| **Capture day** | Tuesday + Friday |
| **Gap tolerance** | ≤ 14 calendar days |
| **First 30d study date** | 2026-07-01 (requires price data update) |
| **First credible comparative study** | 2026-12-01 (6-month archive) |
| **Full-cycle study** | 2027-06-01 (12-month archive) |
| **Blocking dependency** | Price history extension past 2026-05-26 |
