# Danelfin Lineage Audit Report
**Phase:** 7.5M — Signal Provenance, Lineage & Freshness Audit  
**Date:** 2026-05-31  
**Status:** COMPLETE

---

## Summary

The `danelfin_score` displayed in SIH represents the **Danelfin Overall AI Score**, normalized from a raw 1–10 integer to a 1–5 float by dividing by 2. It is **not** the Fundamental, Technical, Sentiment, or Low Risk sub-scores.

---

## What Danelfin Score Means

Danelfin's stock page at `danelfin.com/stock/{TICKER}` displays five AI scores as `aria-label="N out of 10"` elements in order:

| Index | Score Type | Used by SIH? |
|-------|-----------|--------------|
| [0] | **Overall AI Score** | ✅ YES — this is `danelfin_raw` |
| [1] | Fundamental Score | No |
| [2] | Technical Score | No |
| [3] | Sentiment Score | No |
| [4] | Low Risk Score | No |

**Danelfin's definition:** The Overall AI Score reflects the probability that a stock will **outperform the market (beat the S&P 500) over the next 3 months**, based on Danelfin's machine learning model trained on 900+ features.

Scale: 1–10 (10 = highest probability of outperforming, 1 = lowest).

**SIH does NOT use sub-scores.** Only the Overall AI Score (index [0]) is captured.

---

## Transformation

```
danelfin_score = danelfin_raw / 2.0
```

This maps the 1–10 raw integer to the SIH 1–5 ascending scale:

| Raw (1–10) | Score (1–5) | Interpretation |
|-----------|------------|----------------|
| 10 | 5.0 | Highest conviction (Strong Buy equivalent) |
| 8 | 4.0 | Strong signal |
| 7 | 3.5 | Mild positive signal |
| 6 | 3.0 | Neutral |
| 5 | 2.5 | Mild negative signal |
| 2 | 1.0 | Lowest conviction |

---

## Complete Lineage for VRT

| Step | Location | Field | Value |
|------|----------|-------|-------|
| 1. Scrape | `danelfin.com/stock/VRT` | aria-label[0] | `7 out of 10` |
| 2. Store raw | `data/signals/danelfin/latest_danelfin.csv` | `danelfin_raw` | `7` |
| 3. Normalize | `fetch_danelfin_scores.py` line 99 | `danelfin_raw / 2.0` | `3.5000` |
| 4. Store normalized | `data/signals/danelfin/latest_danelfin.csv` | `danelfin_score` | `3.5000` |
| 5. Universe build | `analytical_universe_manager.py` line 567–569 | loaded from latest_danelfin | `3.5` |
| 6. Universe CSV | `data/current/analytical_universe.csv` | `danelfin_score` | `3.5` |
| 7. Overlay | `SecurityIntelligenceOverlay.danelfin_score` | pass-through | `"3.5"` |
| 8. API | `security_overlays[].danelfin_score` | `"3.5"` | `"3.5"` |
| 9. UI display | UCF dashboard / overlay table | `danelfin_score` | **3.5** |

---

## Top 20 Deployment Candidates — Danelfin Values

| Rank | Symbol | Raw (1–10) | Score (1–5) | Meaning |
|------|--------|-----------|------------|---------|
| 1 | VRT | 7 | 3.5 | Mild positive |
| 2 | ARW | 8 | 4.0 | Strong signal |
| 3 | SNX | 6 | 3.0 | Neutral |
| 4 | ATLC | 6 | 3.0 | Neutral |
| 5 | PSX | 5 | 2.5 | Mild negative |
| 6 | CBOE | 4 | 2.0 | Negative |
| 7 | AVT | 7 | 3.5 | Mild positive |
| 8 | LRCX | 6 | 3.0 | Neutral |
| 9 | CAH | 6 | 3.0 | Neutral |
| 10 | DELL | 5 | 2.5 | Mild negative |
| 11 | SANM | 8 | 4.0 | Strong signal |
| 12 | PCB | 8 | 4.0 | Strong signal |
| 13 | CIEN | 8 | 4.0 | Strong signal |
| 14 | NUE | 5 | 2.5 | Mild negative |
| 15 | GFF | 5 | 2.5 | Mild negative |
| 16 | ALNT | 9 | 4.5 | Very strong signal |
| 17 | MTZ | 9 | 4.5 | Very strong signal |
| 18 | CRS | 8 | 4.0 | Strong signal |
| 19 | CMCO | 7 | 3.5 | Mild positive |
| 20 | ANGO | 5 | 2.5 | Mild negative |

---

## Composite Score Contribution

Danelfin carries **10% weight** in the production composite (v1):

```
composite = (ESS×0.55 + Zacks×0.25 + Yahoo×0.10 + Danelfin×0.10) / total_available_weight
```

When Danelfin is missing (score = 0.0 or empty), it is excluded from both the numerator and denominator (renormalization over available signals only).

---

## Coverage Notes

Danelfin coverage is **partial** — not all portfolio holdings have a Danelfin score. Symbols with no score in `latest_danelfin.csv` contribute 0 weight to the composite. The `analytical_universe_manager.py` falls back to any previously stored value in the base universe when a fresh fetch is unavailable.

---

## Freshness

| Field | Latest sourced_date | Age (2026-05-31) | Status |
|-------|--------------------|----|--------|
| `danelfin_score` in `latest_danelfin.csv` | 2026-05-29 | 2 days | **FRESH** |
| `danelfin_score` in `analytical_universe.csv` | Rebuilt 2026-05-31 | 0 days | **FRESH** |
