# Analyst Target Data Inventory
## CII-005 Phase Assessment — June 5, 2026

---

## 1. Overview

This document catalogs every analyst target and count field already collected,
stored, modeled, or referenced in the Security Intelligence Hub codebase as of
June 5, 2026 (post-ISSUE-05).

---

## 2. Fields Already In The System

### 2.1 `price_target` (Consensus Mean)

| Attribute | Value |
|-----------|-------|
| **Source** | Yahoo Finance (`yfinance`) — `ticker.info["targetMeanPrice"]` |
| **API field** | `targetMeanPrice` |
| **Storage** | `data/signals/yahoo/latest_yahoo_supplemental.csv` — column `price_target` |
| **Coverage** | 2,515 / 2,570 symbols (97.9%) in June 5, 2026 snapshot |
| **Model** | `AnalystConsensus.price_target: Optional[float]` — `src/portfolio/models.py:612` |
| **Current UI usage** | Displayed in `_consensusPanelHtml()` — recommendation card expansion, `app.js:1565`. Also present in `dq-sig-card` ABR row in deployment queue signal profile. |
| **Scoring usage** | **None.** Governance comment in `fetch_yahoo_supplemental.py`: "supplemental columns and do NOT affect the composite score formula." |

### 2.2 `upside_pct`

| Attribute | Value |
|-----------|-------|
| **Source** | Computed at fetch time: `(price_target / current_price − 1.0) × 100` |
| **Formula** | `upside_pct = (targetMeanPrice / regularMarketPrice − 1) × 100` |
| **Storage** | `data/signals/yahoo/latest_yahoo_supplemental.csv` — column `upside_pct` |
| **Coverage** | 2,515 / 2,570 symbols (97.9%) — requires both `price_target` and `current_price` |
| **Model** | `AnalystConsensus.upside_pct: Optional[float]` |
| **Current UI usage** | Displayed in `_consensusPanelHtml()`. Color-coded green/red. Also used in `_signalAgreementPanelHtml()` divergence flag: ABR ≤ 2.5 but upside < −10% triggers a warning badge. |
| **Scoring usage** | **None.** |

### 2.3 `current_price`

| Attribute | Value |
|-----------|-------|
| **Source** | Yahoo Finance — `ticker.info["regularMarketPrice"]` (fallback: `previousClose`) |
| **Storage** | `data/signals/yahoo/latest_yahoo_supplemental.csv` — column `current_price` |
| **Coverage** | 2,567 / 2,570 symbols (99.9%) |
| **Current UI usage** | Displayed alongside `price_target` in `_consensusPanelHtml()`. Not used in DQ signal grid. |
| **Scoring usage** | **None.** |

### 2.4 `abr` (Average Broker Recommendation)

| Attribute | Value |
|-----------|-------|
| **Source** | Yahoo Finance — `ticker.info["recommendationMean"]` |
| **Scale** | 1.0 = Strong Buy → 5.0 = Sell |
| **Storage** | `data/signals/yahoo/latest_yahoo_supplemental.csv` — column `abr` |
| **Coverage** | 1,681 / 2,570 symbols (65.4%) — lower than price_target; many small/micro caps lack analyst coverage |
| **Model** | `AnalystConsensus.abr: Optional[float]` — mapped to `consensus_label` via `abr_to_label()` |
| **Current UI usage** | Consensus label + ABR numeric in recommendation panel. In DQ signal grid: "Yahoo ABR" card with label. Conflict badge computed (`CONSENSUS_ALIGNED` / `CONSENSUS_DIVERGENCE`). |
| **Scoring usage** | **None.** |

### 2.5 `analyst_count` — KNOWN GAP

| Attribute | Value |
|-----------|-------|
| **Source** | Yahoo Finance — `ticker.info["numberOfAnalystOpinions"]` |
| **Status** | **MISSING — never fetched.** `fetch_yahoo_supplemental.py` does not request this field. |
| **Model** | `AnalystConsensus.analyst_count: Optional[int]` — defined, always `None` |
| **Storage** | Not written to CSV. Column absent from `latest_yahoo_supplemental.csv`. |
| **Comment in code** | `src/portfolio/models.py:612`: "not available in current Yahoo data feed" |
| **GitHub issue** | ISSUE-08 — documented in `docs/phase_cii003/github_issue_priority_review.md`. The fix is: add `result["analyst_count"] = int(info.get("numberOfAnalystOpinions") or 0) or None` to `fetch_yahoo_supplemental.py`. Estimated XS, ~30 min. |
| **Scoring usage** | N/A (null) |

### 2.6 Fields Available in yfinance But NOT Fetched

Confirmed by live `yf.Ticker('DELL').info` query (June 5, 2026):

| yfinance field | Value (DELL) | Notes |
|---|---|---|
| `targetMeanPrice` | $483.83 | ✅ Already fetched as `price_target` |
| `targetMedianPrice` | $500.00 | ❌ Not fetched, not stored |
| `targetHighPrice` | $700.00 | ❌ Not fetched, not stored |
| `targetLowPrice` | $213.00 | ❌ Not fetched, not stored |
| `numberOfAnalystOpinions` | 23 | ❌ Not fetched — ISSUE-08 |
| `averageAnalystRating` | "1.8 - Buy" | ❌ Not fetched (redundant with `abr`) |

---

## 3. Data Flow Summary

```
yfinance (Yahoo Finance API)
  └── fetch_yahoo_supplemental.py
        └── data/signals/yahoo/latest_yahoo_supplemental.csv
              └── load_analyst_consensus()
                    └── AnalystConsensus model
                          └── runner._build_consensus_payload()
                                └── analyst_consensus_by_symbol (API response)
                                      └── _consensusPanelHtml() [recommendation cards]
                                      └── _signalAgreementPanelHtml() [conflict detection]
                                      └── dq-sig-card ABR row [deployment queue signal profile]
```

---

## 4. Fields NOT In The System At All

| Field | Assessment |
|-------|------------|
| Target high / low / median | Not fetched. Not in CSV. Not in model. Available via yfinance. |
| Analyst count | In model (always null). Not fetched. ISSUE-08 fix defined. |
| Raw analyst text ("1.8 - Buy") | Not fetched. Redundant with computed `abr` + `consensus_label`. |
| FMP analyst data | FMP Starter plan does not include analyst target endpoints (HTTP 402). |

---

## 5. Coverage Assessment for Portfolio Holdings

Current portfolio has ~59 symbols. Yahoo supplemental covers 2,570 symbols at 97.9% for price_target and 65.4% for ABR. Portfolio-level coverage for the 59-symbol holding set is expected to be near 100% for price_target and ~85–90% for ABR (large-cap holdings are all covered; some niche/small-cap names may lack analyst coverage).

---

## 6. Data Freshness

| Field | Source freshness | Fetch cadence |
|---|---|---|
| `price_target` | Yahoo reflects latest published consensus | Re-fetched daily via refresh pipeline |
| `abr` | Yahoo reflects latest broker recommendation mean | Re-fetched daily |
| `current_price` | Yahoo `regularMarketPrice` | Re-fetched daily — may lag live market |
| `analyst_count` | Yahoo `numberOfAnalystOpinions` | Not yet fetched |

**Key staleness risk:** Yahoo's consensus price target is an aggregated average and can lag by days after new analyst updates. This is well-understood and already flagged in `yahoo_lineage_report.md`. The fetch date in `sourced_date` represents when SIH last pulled from Yahoo, not when the analyst last updated their target.
