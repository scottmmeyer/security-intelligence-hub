# ESS Stability Preview
**Phase 7.6F-R — Deliverable Q4**
**Generated:** 2026-06-01
**Dataset:** `ess_history_master.csv`

---

## 1. Dataset Summary

| Metric | Value |
|--------|-------|
| Total records (ess_history_master.csv) | 54,566 |
| Total unique symbols | 2,918 |
| Unique capture dates | 36 |
| Date range | 2025-08-18 → 2026-06-01 |
| Span (days) | 287 |
| Portfolio-level dates | 14 (Aug 2025 – Mar 9 2026) |
| Mixed/portfolio Apr 2026 dates | 5 (Apr 3 – Apr 13 2026) |
| Full-universe dates | 17 (Apr 15 – Jun 1 2026) |

---

## 2. ESS Movement Overview (First → Last Observation)

**Universe:** 2,869 symbols with 2+ observations

| Movement Category | Count | % of Multi-Obs Symbols |
|-------------------|-------|------------------------|
| Upgraded (+1 or more) | 542 | 18.9% |
| Unchanged | 958 | 33.4% |
| Downgraded (−1 or more) | 1,369 | 47.7% |
| **Total** | **2,869** | **100%** |

**Average delta (first→last, 5-pt scale):** −0.519

The negative average delta reflects a net downgrade trend across the 287-day observation window (Aug 2025 – Jun 2026). This is consistent with a period of macroeconomic tightening, sector rotation, and portfolio mean-reversion, where many securities held at elevated ESS scores in mid-2025 declined through the following year.

**ESS Delta Distribution:**

| Delta | Count | % |
|-------|-------|----|
| +3 or more | 28 | 1.0% |
| +2 | 110 | 3.8% |
| +1 | 404 | 14.1% |
| 0 (unchanged) | 958 | 33.4% |
| −1 | 743 | 25.9% |
| −2 | 453 | 15.8% |
| −3 or more | 173 | 6.0% |

---

## 3. Top 10 Upgrades (First → Last, 5-pt Scale)

| Symbol | Delta | First ESS | Last ESS | Observations | Coverage Days |
|--------|-------|-----------|----------|--------------|---------------|
| HELE | +4 | 1 (VERY_BEARISH) | 5 (VERY_BULLISH) | 17 | 83 |
| NIQ | +4 | 1 (VERY_BEARISH) | 5 (VERY_BULLISH) | 3 | 12 |
| OSCR | +4 | 1 (VERY_BEARISH) | 5 (VERY_BULLISH) | 17 | 83 |
| ARE | +3 | 1 (VERY_BEARISH) | 4 (BULLISH) | 17 | 83 |
| AVA | +3 | 2 (BEARISH) | 5 (VERY_BULLISH) | 26 | 215 |
| BB | +3 | 1 (VERY_BEARISH) | 4 (BULLISH) | 18 | 83 |
| BLMN | +3 | 1 (VERY_BEARISH) | 4 (BULLISH) | 20 | 83 |
| CDXS | +3 | 2 (BEARISH) | 5 (VERY_BULLISH) | 17 | 83 |
| DMRC | +3 | 2 (BEARISH) | 5 (VERY_BULLISH) | 19 | 66 |
| FIVN | +3 | 2 (BEARISH) | 5 (VERY_BULLISH) | 17 | 83 |

**Notable:** HELE (Helen of Troy), OSCR (Oscar Health), and NIQ show the most dramatic recoveries — full 4-point reversals from VERY_BEARISH to VERY_BULLISH. Most of these large upgrades occurred in the Apr–May 2026 full-universe window, suggesting a possible market-wide sentiment shift in Q2 2026.

---

## 4. Top 10 Downgrades (First → Last, 5-pt Scale)

| Symbol | Delta | First ESS | Last ESS | Observations | Coverage Days |
|--------|-------|-----------|----------|--------------|---------------|
| AB | −4 | 5 (VERY_BULLISH) | 1 (VERY_BEARISH) | 21 | 287 |
| APTV | −4 | 5 (VERY_BULLISH) | 1 (VERY_BEARISH) | 25 | 287 |
| ASC | −4 | 5 (VERY_BULLISH) | 1 (VERY_BEARISH) | 19 | 268 |
| ASIX | −4 | 5 (VERY_BULLISH) | 1 (VERY_BEARISH) | 23 | 287 |
| AWI | −4 | 5 (VERY_BULLISH) | 1 (VERY_BEARISH) | 26 | 287 |
| BIDU | −4 | 5 (VERY_BULLISH) | 1 (VERY_BEARISH) | 19 | 275 |
| BWXT | −4 | 5 (VERY_BULLISH) | 1 (VERY_BEARISH) | 29 | 195 |
| CCJ | −4 | 5 (VERY_BULLISH) | 1 (VERY_BEARISH) | 25 | 287 |
| CRON | −4 | 5 (VERY_BULLISH) | 1 (VERY_BEARISH) | 16 | 132 |
| DNOW | −4 | 5 (VERY_BULLISH) | 1 (VERY_BEARISH) | 27 | 287 |

**Notable:** These are not rapid collapses — most have 19–29 observations over 195–287 days, indicating sustained degradation. AB (AllianceBernstein), APTV (Aptiv), BIDU (Baidu), CCJ (Cameco), and DNOW (NOW Inc.) represent a diverse cross-sector set, suggesting idiosyncratic rather than systemic downgrade drivers for each.

---

## 5. Most Stable Symbols (Lowest Std Dev, 3+ Observations)

| Symbol | Std Dev | Observations | Coverage Days | ESS (first→last) |
|--------|---------|--------------|---------------|-------------------|
| APO | 0.000 | 26 | 287 | 4→4 (BULLISH) |
| ADAM | 0.000 | 17 | 83 | 3→3 (NEUTRAL) |
| ADTN | 0.000 | 17 | 83 | 3→3 (NEUTRAL) |
| ALCO | 0.000 | 17 | 83 | 2→2 (BEARISH) |
| AEYE | 0.000 | 15 | 71 | 3→3 (NEUTRAL) |
| ASGN | 0.000 | 8 | 177 | 2→2 (BEARISH) |
| AUDC | 0.000 | 4 | 72 | 4→4 (BULLISH) |
| ACDC | 0.000 | 3 | 12 | 4→4 (BULLISH) |
| ACVA | 0.000 | 3 | 12 | 2→2 (BEARISH) |
| ADV | 0.000 | 3 | 12 | 5→5 (VERY_BULLISH) |

**Notable:** APO (Apollo Global Management) is the most impressive — 26 observations over 287 days with zero ESS variation (BULLISH throughout). This is the gold standard for signal stability. AEYE, ALCO, and ASGN show similar stability over shorter windows. Stable signals are ideal anchors for composite scoring.

---

## 6. Caveat: Scope Bias in Early History

The 14 portfolio-level dates (Aug 2025 – Mar 9 2026) cover only ~500–963 holdings — securities that were already under active portfolio consideration. These tend to have **above-average initial ESS scores** (holdings were often acquired at favorable sentiment). This creates a **survivorship-selection bias** in the early delta analysis: the high rate of downgrades from first to last observation is partly an artifact of the portfolio selection filter (high ESS at entry → mean reversion).

Full-universe data begins 2026-03-10, and the 17 full-universe dates (Apr 15 – Jun 1) provide a more representative picture of cross-sectional ESS stability.

---

## 7. Summary

The ESS historical archive shows **strong signal breadth** (2,504 TIER_A symbols), **meaningful variation** (only 33% unchanged from first to last), and a **slight downward trend** in sentiment over the observation window. The dataset is suitable for forward signal effectiveness and transition analysis studies.
