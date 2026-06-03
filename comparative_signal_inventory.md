# Comparative Signal Inventory
**Phase 7.7A — Deliverable Q1**
**Generated:** 2026-06-01

---

## 1. Purpose

Document and compare all available historical signal data for ESS, Zacks, and Danelfin prior to comparative effectiveness analysis.

---

## 2. Signal Summary Table

| Dimension | ESS | Zacks | Danelfin |
|-----------|-----|-------|----------|
| **Archive source** | `data/history/ess_archive/` + `ess_history_master.csv` | `data/signals/zacks/` | `data/signals/danelfin/` |
| **Earliest observation** | 2025-08-18 | 2026-05-14 | 2026-05-14 |
| **Latest observation** | 2026-06-01 | 2026-05-29 | 2026-05-29 |
| **Archive span** | ~10.5 months | 15 days | 15 days |
| **Total observations** | 54,566 | 3,373 | 2,266 |
| **Unique symbols** | 2,918 | 2,601 | 954 |
| **Observation dates** | 36 | 5 | 5 |
| **Freshness (as of 2026-06-01)** | 0 days | 3 days | 3 days |
| **Provider** | LSEG StarMine via Fidelity | Zacks Investment Research | Danelfin AI |
| **Raw scale** | Text (VBearish–VBullish) or 1–10 numeric | Rank 1–5 (1=best) | Score 1–10 (continuous) |
| **Normalized 5pt scale** | 1=VBearish, 5=VBullish | 1=StrongSell, 5=StrongBuy | 1–5 rounded |
| **Price-history-matched (30d returns)** | 32,805 observation pairs | 0 (price data ends 2026-05-26) | 0 (same constraint) |
| **Price-history-matched (7d returns)** | N/A (computed at 30d) | 0 | 683 pairs |
| **Price-history-matched (3d returns)** | N/A | 2,267 pairs | 738 pairs |

---

## 3. Per-Signal Detail

### 3.1 ESS (Equity Summary Score from LSEG StarMine)

**Archive:** `ess_history_master.csv` — built in Phase 7.6F-R from 50 authentic ESS archive files

| Date | Observation Count |
|------|-------------------|
| 2025-08-18 | 256 (portfolio-level) |
| ... (26 portfolio-level dates) | 200–400 each |
| 2026-03-10 | 2,831 (first full-universe capture) |
| ... (9 full-universe dates) | 2,500–2,900 each |
| 2026-06-01 | 2,831 (latest) |

**Scale:** Two source formats, both normalized to 5pt:
- Portfolio files (Aug 2025–Feb 2026): numeric 1–10 → 5pt via equal-quintile mapping
- Full-universe files (Mar 2026–Jun 2026): text categories (VERY_BEARISH / BEARISH / NEUTRAL / BULLISH / VERY_BULLISH) → 5pt direct

**Coverage:** 2,918 unique symbols. 2,504 are TIER_A (10+ observations). Full breadth of investable US equity universe.

**Forward return matching:** 32,805 30-day pairs, 10,435 60-day pairs, 7,031 90-day pairs (from Phase 7.6G).

---

### 3.2 Zacks (Zacks Investment Research Rank)

**Archive:** Five individual date files under `data/signals/zacks/`

| Date | Rows | Notes |
|------|------|-------|
| 2026-05-14 | 1 | Single test entry (MU only) |
| 2026-05-20 | 1 | Single test entry (MU only) |
| 2026-05-21 | 78 | Partial capture |
| 2026-05-26 | 2,568 | First full-scale capture |
| 2026-05-29 | 725 | Partial capture |

**Schema:** `symbol, zacks_rank, zacks_score, abr, price_target, eps_growth, sourced_date`

**Scale:** Zacks Rank 1–5 where 1=Strong Buy, 5=Strong Sell. Inverted for 5pt normalization: Rank 1 → 5pt=5, Rank 5 → 5pt=1.

**Rank distribution (2026-05-26, n=2,568 including 105 blank ranks):**

| Zacks Rank | Count | 5pt Equivalent |
|------------|-------|----------------|
| 1 (Strong Buy) | 203 | 5 |
| 2 (Buy) | 397 | 4 |
| 3 (Hold) | 1,460 | 3 |
| 4 (Sell) | 299 | 2 |
| 5 (Strong Sell) | 104 | 1 |
| Blank/NA | 105 | N/A |

**Forward return matching:** Price data ends 2026-05-26. With Zacks data starting 2026-05-14, maximum available return window is ~12 days. Only 3-day returns are achievable with full-universe Zacks (2,267 of 2,568 symbols on 2026-05-26). Zero 7d+ returns possible.

**Coverage overlap with ESS:** 2,513 symbols (86.1% of ESS universe). 693 symbols appear in multiple Zacks dates (transition-eligible).

---

### 3.3 Danelfin (Danelfin AI Score)

**Archive:** Five individual date files under `data/signals/danelfin/`

| Date | Rows | Notes |
|------|------|-------|
| 2026-05-14 | 1 | Single test entry (MU only) |
| 2026-05-20 | 782 | First meaningful capture |
| 2026-05-21 | 33 | Partial capture |
| 2026-05-26 | 725 | Partial capture |
| 2026-05-29 | 725 | Partial capture |

**Schema:** `symbol, danelfin_raw, danelfin_score, sourced_date`

**Scale:** `danelfin_score` is on a 1–5 continuous scale (granular: 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0). Higher = more bullish. Rounded to nearest integer for 5pt normalization.

**Score distribution (2026-05-20, n=782):**

| Score | Count | 5pt Bucket |
|-------|-------|------------|
| 1.0 | 9 | 1 |
| 1.5 | 61 | 2 |
| 2.0 | 131 | 2 |
| 2.5 | 167 | 3 |
| 3.0 | 177 | 3 |
| 3.5 | 118 | 4 |
| 4.0 | 85 | 4 |
| 4.5 | 26 | 5 |
| 5.0 | 8 | 5 |

Distribution is roughly bell-shaped, concentrated at 2.0–3.5. Only 8 observations in the top bucket (5.0) — too few for meaningful returns analysis.

**Forward return matching:** From 2026-05-20: 683 7-day pairs, 738 3-day pairs. Zero 14d+ returns possible.

**Coverage overlap with ESS:** 938 symbols (32.2% of ESS universe). Only 725 symbols appear in multiple dates (transition-eligible).

---

## 4. Coverage Overlap Matrix

| | ESS (2,918) | Zacks (2,601) | Danelfin (954) |
|---|---|---|---|
| **ESS** | — | 2,513 (86.1%) | 938 (32.2%) |
| **Zacks** | 2,513 (96.6%) | — | 898 (94.1%) |
| **Danelfin** | 938 (98.3%) | 898 (94.1%) | — |
| **All Three** | **882** | **882** | **882** |

Common universe (all three signals present): **882 symbols**

---

## 5. Price Data Coverage

Price history available in `data/history/prices/symbol=<TICKER>/prices.csv`:
- 2,567 symbols with price files
- Date range: 2025-05-13 → 2026-05-26

Coverage of each signal's symbols:
- ESS symbols with prices: 2,487 of 2,918 (85.2%)
- Zacks symbols with prices: 2,298 of 2,601 (88.3%)
- Danelfin symbols with prices: 883 of 954 (92.6%)

---

## 6. Forward Return Horizon Feasibility

| Signal | Best Observation Date | Max Forward Window | Reason |
|--------|----------------------|-------------------|--------|
| ESS | 2025-08-18 (earliest) | 30d, 60d, 90d | 10+ months before price data ends |
| Zacks | 2026-05-26 (best full date) | **3 days** | Price data ends 2026-05-26 |
| Danelfin | 2026-05-20 (best full date) | **7 days** | Price data ends 2026-05-26 |

**Critical limitation:** A like-for-like 30-day forward return comparison between ESS, Zacks, and Danelfin is **impossible** with current archives. Zacks and Danelfin data were not captured until May 2026, and price history ends May 26, 2026.

---

## 7. Archive Quality Summary

| Criterion | ESS | Zacks | Danelfin |
|-----------|-----|-------|----------|
| Archive depth | ★★★★★ (10+ months) | ★ (15 days) | ★ (15 days) |
| Symbol breadth | ★★★★★ (2,918) | ★★★★ (2,601) | ★★ (954) |
| Observation frequency | ★★★★ (~weekly) | ★ (5 snapshots) | ★ (5 snapshots) |
| Forward return testability | ★★★★★ (30d viable) | ★ (3d only) | ★★ (7d only) |
| Persistence testability | ★★★★★ (51,648 transitions) | ★★ (740 transitions) | ★★ (1,310 transitions) |
| Overall research readiness | **HIGH** | **VERY LOW** | **LOW** |

---

## 8. Data Collection Gap

To enable a proper Phase 7.7A comparison, the following capture milestones would be required:

| Milestone | When Available | Action Required |
|-----------|----------------|-----------------|
| Zacks 30-day forward returns | ~2026-07-01 | Continue capturing Zacks weekly |
| Danelfin 30-day forward returns | ~2026-07-01 | Continue capturing Danelfin weekly |
| Comparable 6-month archive (Zacks) | ~2026-12-01 | Systematic weekly capture |
| Full-cycle comparison | ~2027-06-01 | After bull/bear/neutral regimes present |

**Recommendation:** Begin systematic weekly signal capture for Zacks and Danelfin starting immediately. Re-run Phase 7.7A no earlier than 2026-12-01 when 6+ months of archive depth is available for both signals.
