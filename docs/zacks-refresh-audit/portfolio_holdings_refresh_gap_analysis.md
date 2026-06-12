# Portfolio Holdings Refresh Gap Analysis
**Audit Date**: 2026-06-12  
**Source PAR**: PAR-20260611-E43FC3BB  
**Scope**: ZACKS-REFRESH-UNIVERSE-01

---

## 1. Executive Summary

Of **78 currently held portfolio positions**, **24 equity holdings are excluded from the Zacks smart refresh list** and are receiving stale Zacks data. These 24 holdings all share the same structural condition: they are in `base_equity_universe.csv`, their `starmine_ess_text` is non-bullish (NEUTRAL / BEARISH / VERY_BEARISH / NO_ESS), and they already exist in the `latest_zacks.csv` cache.

Under current logic, once a symbol is cached and turns non-bullish, it is **never refreshed again**.

---

## 2. Holdings Inventory

### 2a. Total Holdings Breakdown

| Category | Count | Notes |
|----------|-------|-------|
| Total portfolio positions | 78 | From PAR-20260611-E43FC3BB |
| Non-equity (ETFs / funds / crypto / cash) | 20 | Zacks not applicable — see §3 |
| Equity holdings in universe | 58 | Subject to smart refresh logic |
| ↳ In smart refresh list (BULLISH/VERY_BULLISH) | 34 | Getting daily Zacks updates |
| ↳ Excluded from smart refresh — **GAP** | **24** | Stale Zacks data risk |

### 2b. The 24 Excluded Equity Holdings

| Symbol | ESS Category | Staleness Risk | Notes |
|--------|-------------|----------------|-------|
| TSLA | VERY_BEARISH | **CRITICAL** | Held bearish position; Zacks stale |
| CMCO | BEARISH | **HIGH** | Potential reduction candidate |
| DVN | BEARISH | **HIGH** | Potential reduction candidate |
| KGC | BEARISH | **HIGH** | Potential reduction candidate |
| PRIM | BEARISH | **HIGH** | Potential reduction candidate |
| ALNT | NEUTRAL | MEDIUM | Held neutral position |
| AMG | NEUTRAL | MEDIUM | Held neutral position |
| AMZN | NEUTRAL | MEDIUM | Held neutral position |
| ANIP | NEUTRAL | MEDIUM | Held neutral position |
| AZZ | NEUTRAL | MEDIUM | Held neutral position |
| FIS | NEUTRAL | MEDIUM | Held neutral position |
| GFF | NEUTRAL | MEDIUM | Held neutral position |
| HCI | NEUTRAL | MEDIUM | Held neutral position |
| IVZ | NEUTRAL | MEDIUM | Held neutral position |
| NVS | NEUTRAL | MEDIUM | Held neutral position |
| UTHR | NEUTRAL | MEDIUM | Held neutral position |
| XYZ | NEUTRAL | MEDIUM | Held neutral position |
| YELP | NEUTRAL | MEDIUM | Held neutral position |
| AEIS | NO_ESS | MEDIUM | No ESS signal; Zacks is only data source |
| BSVN | NO_ESS | MEDIUM | No ESS signal; Zacks is only data source |
| CBOE | NO_ESS | MEDIUM | No ESS signal; Zacks is only data source |
| MTZ | NO_ESS | MEDIUM | No ESS signal; Zacks is only data source |
| SIMO | NO_ESS | MEDIUM | No ESS signal; Zacks is only data source |
| STNG | NO_ESS | MEDIUM | No ESS signal; Zacks is only data source |

---

## 3. Non-Equity Holdings (No Zacks Gap — By Design)

The following 20 holdings are **not in `base_equity_universe.csv`** and are correctly excluded from Zacks refresh. These are non-equity instruments for which Zacks ratings do not apply:

| Symbol | Type | In Zacks Cache |
|--------|------|----------------|
| BND | Bond ETF (Vanguard) | No |
| BNDX | Intl Bond ETF (Vanguard) | No |
| DODFX | Mutual fund (Dodge & Cox) | Yes (stale) |
| FBTC | Crypto ETF (Fidelity Bitcoin) | Yes (stale) |
| FCPGX | Mutual fund (Fidelity) | Yes (stale) |
| FETH | Crypto ETF (Fidelity Ethereum) | Yes (stale) |
| FMCSX | Mutual fund (Fidelity Mid-Cap) | Yes (stale) |
| FSOL | Crypto ETF (Fidelity Solana) | Yes (stale) |
| FXAIX | Mutual fund (Fidelity S&P 500) | Yes (stale) |
| M26CNT069 | Internal identifier / cash | No |
| MCB | Not in universe | Yes (stale) |
| SBS | ADR — not in universe | Yes (stale) |
| SMR | Not in universe | Yes (stale) |
| SPAXX | Money market fund | No |
| TTNDY | ADR — not in universe | Yes (stale) |
| VB | Broad equity ETF (Vanguard) | Yes (stale) |
| VO | Broad equity ETF (Vanguard) | Yes (stale) |
| VOO | S&P 500 ETF (Vanguard) | Yes (stale) |
| VWO | EM ETF (Vanguard) | No |
| XRP | Cryptocurrency | Yes (stale) |

**Note**: Several non-equity symbols appear in `latest_zacks.csv` with stale data. This is a separate cleanup issue but does not affect portfolio coverage decisions.

---

## 4. The Asymmetric Staleness Risk

The staleness risk is **directionally asymmetric** in the worst possible way:

1. A holding starts as BULLISH → gets daily Zacks refresh → composite score is current
2. ESS degrades: BULLISH → NEUTRAL → BEARISH → VERY_BEARISH
3. As ESS declines below BULLISH, the smart refresh immediately drops the symbol
4. The holding now runs on **stale Zacks data indefinitely**
5. The composite score continues to use the cached (potentially outdated) Zacks rating
6. **Reduction decisions are made on degraded signal quality**

This is the highest-risk path: the positions most in need of up-to-date Zacks data (deteriorating holdings under reduction review) are the ones that get cut off from refresh.

---

## 5. NO_ESS Holdings Are the Highest-Integrity Risk

For the 6 NO_ESS equity holdings (AEIS, BSVN, CBOE, MTZ, SIMO, STNG), Zacks is effectively the **only available signal source** for conviction scoring. When these symbols are cached and excluded from smart refresh, the composite score is being computed from data of unknown age. There is no ESS fallback to flag degradation.

---

## 6. Quantified Staleness Window

The age of cached Zacks data for excluded holdings depends on when the symbol last qualified for refresh (last time it was BULLISH or uncached). There is currently no staleness tracking in `latest_zacks.csv` beyond the `fetch_date` column. Holdings that turned bearish weeks ago may have Zacks data that is 30–90+ days stale with no alert mechanism.

---

## 7. Recommended Remediation

See `governance_recommendation.md` for the full fix design.  
Short form: Add `forced_symbols` parameter to `build_smart_refresh_list()`. Pass current portfolio holdings into the forced set from `refresh_signals.py`. This ensures all held positions receive a daily Zacks refresh regardless of ESS category. Net impact: +24 symbols added to daily refresh. Runtime impact is negligible (see `runtime_impact_assessment.md`).
