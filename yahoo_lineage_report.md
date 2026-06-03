# Yahoo Lineage Audit Report
**Phase:** 7.5M — Signal Provenance, Lineage & Freshness Audit  
**Date:** 2026-05-31  
**Status:** COMPLETE

---

## Summary

Three Yahoo Finance signals are tracked in SIH: **ABR** (Analyst Buy Rating), **Price Target**, and **Upside**. The ABR is used raw (1–5 descending, lower=bullish) in the consensus matrix display; it is inverted for experimental composite v2 but does NOT contribute to the production composite score (v1). The price target and upside are display-only with a known stale-target risk documented in the DELL case below.

---

## Signal Definitions

### ABR (Analyst Buy Rating)
**Source:** Yahoo Finance consensus recommendations page  
**Scale:** 1.0 (Strong Buy) → 5.0 (Strong Sell) — **lower is bullish**  
**Meaning:** Weighted mean of analyst recommendations (1=Strong Buy, 2=Buy, 3=Hold, 4=Sell, 5=Strong Sell)

Yahoo ABR is displayed as-is (raw value). The SIH system inverts it for scoring purposes only:

```
normalize_yahoo_abr(abr) = 6.0 − abr  → ascending scale 1–5 (5=most bullish)
```

### Price Target
**Source:** Yahoo Finance consensus analyst price target (median/mean of targets)  
**Meaning:** Average analyst 12-month forward price target in USD  
**Display:** Raw USD value

### Upside
**Source:** Computed at fetch time by `fetch_yahoo_supplemental.py`  
**Formula:** `upside_pct = (price_target / current_price − 1.0) × 100`  
**Meaning:** Implied upside/downside percent from current price to analyst consensus target  
**Note:** This is **point-in-time** — the upside % reflects prices at the exact moment of scrape, not a rolling calculation.

---

## Complete Lineage Path

```
Yahoo Finance web page
  → src/scoring/fetch_yahoo_supplemental.py (scrapes consensus page)
    → data/signals/yahoo/latest_yahoo_supplemental.csv
      fields: symbol, price_target, abr, eps_growth_5yr, current_price, upside_pct, sourced_date
        → src/portfolio/analyst_consensus.load_analyst_consensus()
          → analyst_consensus_by_symbol dict (keyed by UPPERCASE symbol)
            → API response: analyst_consensus_by_symbol[symbol].{consensus_label, abr}
              → UI: UCF dashboard / portfolio_alignment fidelity panel
```

### ABR in Composite Score (v1 — Production)

**Yahoo ABR does NOT contribute to the production composite_score (v1).**

In `analytical_universe_manager._score_from_inputs()`, the `yahoo_score` parameter defaults to empty for most holdings. The `yahoo_abr_normalized` (inverted ABR) is stored as a separate column in `analytical_universe.csv` as an **experimental** field — it only contributes to `composite_v2_yahoo`, which is not the production score used in deployment or UCF ranking.

Verification for VRT:
- `yahoo_abr_normalized` in `analytical_universe.csv` = `""` (empty)
- `yahoo_score` = `""` (empty)
- **Production composite does NOT include Yahoo ABR for VRT**

### ABR in Consensus Matrix (display only)

The Yahoo ABR IS used for the 3-signal consensus matrix (Section 4 of UCF dashboard and fidelity panel):

```
_consensus_label_to_direction(consensus_label):
    STRONG_BUY / BUY → BULLISH
    HOLD / NO_CONSENSUS → NEUTRAL  
    SELL / STRONG_SELL → BEARISH
```

This is **display only** — no impact on scoring, ranking, or deployment.

---

## DELL Stale Target Case

| Field | Value | Observation |
|-------|-------|-------------|
| `price_target` | $220.26 | Analyst consensus target |
| `current_price` (at scrape) | $426.35 | DELL price on 2026-05-29 |
| `upside_pct` | −48.3% | Computed at scrape time |
| `abr` | 2.00 (Buy) | Analyst consensus = Buy |
| `sourced_date` | 2026-05-29 | 2 days ago |

**Anomaly:** The ABR of 2.00 (consensus Buy) is inconsistent with a price target of $220.26 against a $426.35 current price — an analyst consensus of "Buy" typically implies upside, not a −48% downside.

**Root Cause:** This is a **stale analyst price target**, not a stale data fetch. The scraped Yahoo page reflects analyst targets that have not been updated since the price appreciated significantly. The data was scraped correctly on 2026-05-29, but the underlying analyst estimates on Yahoo Finance reflect an older price regime.

**Classification:** MISLABEL risk — the display of "upside: −48.3%" next to an ABR of 2.0 (Buy) will confuse operators. The target is technically correct as-scraped, but the combination signals a data quality issue at the Yahoo source.

**Governance:** SIH displays the target and upside with the sourced_date. Operators should interpret upside with caution when ABR and upside_pct are contradictory (Buy + negative upside = stale target).

---

## Freshness

| Field | Latest sourced_date | Age (2026-05-31) | Status |
|-------|--------------------|----|--------|
| `abr` | 2026-05-29 | 2 days | **FRESH** |
| `price_target` | 2026-05-29 | 2 days | **FRESH (fetch is fresh; target may be stale at source)** |
| `upside_pct` | 2026-05-29 | 2 days | **FRESH (computed at fetch; subject to price drift)** |

---

## Top 20 Deployment Candidates — Yahoo Values

| Symbol | ABR (raw) | Price Target | Upside % | ABR Direction |
|--------|-----------|-------------|----------|---------------|
| VRT | 1.50 | $376.80 | +18.5% | BULLISH |
| ARW | (no ABR) | $214.50 | −2.1% | — |
| SNX | 1.55 | $241.36 | −5.7% | BULLISH |
| ATLC | (no ABR) | $104.00 | +23.8% | — |
| PSX | 2.15 | $190.58 | +7.9% | BULLISH |
| CBOE | 3.12 | $330.43 | −3.9% | NEUTRAL |
| AVT | (no ABR) | $89.00 | +0.6% | — |
| LRCX | 1.53 | $313.69 | −3.2% | BULLISH |
| CAH | 1.47 | $245.27 | +22.8% | BULLISH |
| DELL | 2.00 | $220.26 | **−48.3%** ⚠️ | BULLISH (stale target) |
| SANM | (no ABR) | $212.25 | −20.2% | — |
| PCB | (no ABR) | $26.00 | +5.5% | — |
| CIEN | 2.05 | $457.91 | −18.6% | BULLISH |
| NUE | 1.76 | $244.14 | −2.0% | BULLISH |
| GFF | (no ABR) | $118.29 | +35.4% | — |
| ALNT | 1.60 | $73.80 | −1.7% | BULLISH |
| MTZ | 1.25 | $473.05 | +23.4% | BULLISH |
| CRS | 1.33 | $459.44 | −1.2% | BULLISH |
| CMCO | (no ABR) | $26.50 | +65.3% | — |
| ANGO | (no ABR) | $18.00 | +54.1% | — |

⚠️ DELL: ABR=2.00 (Buy) but upside=−48.3% — stale analyst target.
