# RC-02 Mapping Fix Report

**Date:** 2026-06-09  
**Status:** IMPLEMENTED  
**File changed:** `src/portfolio/enrichment.py` — `_ETF_OVERRIDES` table

---

## Phase 2 — Correct Classification Determination

### BSVN — Bank7 Corp

| Field | Value | Source |
|---|---|---|
| Company | Bank7 Corp | company_profile |
| Domicile | Oklahoma City, OK, United States | company_profile |
| Sector | Financial Services / Banks - Regional | security_metadata |
| Market Cap | ~$300M (micro-cap threshold) | market price × shares |
| Quote Type | EQUITY | security_metadata |
| **asset_class** | **EQUITIES** | SIH taxonomy |
| **geography** | **US** | country=United States |
| **market_cap_bucket** | **MICRO** | <$500M US micro-cap |
| **sector** | **FINANCIAL SERVICES** | security_metadata |
| **industry** | **Banks - Regional** | security_metadata |

SIH precedent: US MICRO uses `benchmark_id=BM_US_MICRO_RUMIC`, `investable_vehicle_id=VEH_US_MICRO_IWC` (consistent with IWC ETF). Override uses `_ETF_OVERRIDES` pattern (not scored/replayed — classification only).

### STNG — Scorpio Tankers Inc.

| Field | Value | Source |
|---|---|---|
| Company | Scorpio Tankers Inc. | company_profile |
| Domicile | Monaco | company_profile |
| Exchange | NYSE | listed US exchange |
| Sector | Energy / Oil & Gas Midstream | security_metadata |
| Market Cap | ~$1.3B | market price estimate |
| Quote Type | EQUITY | security_metadata |
| **asset_class** | **EQUITIES** | SIH taxonomy |
| **geography** | **INTERNATIONAL** | Monaco domicile → not US |
| **market_cap_bucket** | **SMALL** | $1-2B international small cap |
| **sector** | **ENERGY** | security_metadata |
| **industry** | **Oil & Gas Midstream** | security_metadata |

SIH precedent: Monaco-domiciled stocks treated as INTERNATIONAL (no existing Monaco entries in universe; country NOT in adr_domicile_policy.yaml but defaults to INTERNATIONAL). Comparable: ACGL (Bermuda, MID), ABEV (Brazil, MID). STNG at ~$1.3B maps to SMALL (just below MID threshold for INTERNATIONAL tier).

### SIMO — Silicon Motion Technology (ADR)

| Field | Value | Source |
|---|---|---|
| Company | Silicon Motion Technology Corporation | company_profile |
| Domicile | Hong Kong | company_profile |
| Description | ADR REP 4 ORD | Fidelity description |
| Sector | Technology / Semiconductors | security_metadata |
| Market Cap | ~$1.4B | market price estimate |
| Quote Type | EQUITY (ADR) | security_metadata |
| **asset_class** | **EQUITIES** | SIH taxonomy |
| **geography** | **INTERNATIONAL** | Hong Kong domicile |
| **market_cap_bucket** | **SMALL** | $1-2B international small cap |
| **sector** | **TECHNOLOGY** | security_metadata |
| **industry** | **Semiconductors** | security_metadata |

SIH precedent: ADRs from non-US domiciles → INTERNATIONAL. Hong Kong is in `adr_domicile_policy.yaml` as DEVELOPED_INTERNATIONAL (not explicitly listed but defaults to INTERNATIONAL via fallback). Comparable: ADCT (Switzerland MICRO), ACGL (Bermuda MID). At ~$1.4B → SMALL tier.

---

## Phase 3 — Implementation

### Change: `src/portfolio/enrichment.py` — `_ETF_OVERRIDES`

Added 3 entries in a new comment block "Individual equity overrides — RC-02 classification gap fix":

```python
# ── Individual equity overrides — RC-02 classification gap fix ───────────
# These symbols are absent from analytical_universe.csv but present in the
# portfolio.  Without an override they fall through to asset_class=UNKNOWN,
# causing L1 allocation sum < 100% (RC-02 FAIL).
# Source: company_profile data + security_metadata (sector/industry/country).
# Classification follows SIH taxonomy conventions.
"BSVN":  dict(asset_class="EQUITIES", geography="US",            market_cap_bucket="MICRO",  mega_subtier="N/A", sector="FINANCIAL SERVICES", industry="Banks - Regional"),   # Bank7 Corp, Oklahoma City, US; ~$300M market cap
"STNG":  dict(asset_class="EQUITIES", geography="INTERNATIONAL", market_cap_bucket="SMALL",  mega_subtier="N/A", sector="ENERGY",            industry="Oil & Gas Midstream"), # Scorpio Tankers Inc., Monaco-domiciled, NYSE-listed; ~$1.3B market cap
"SIMO":  dict(asset_class="EQUITIES", geography="INTERNATIONAL", market_cap_bucket="SMALL",  mega_subtier="N/A", sector="TECHNOLOGY",        industry="Semiconductors"),      # Silicon Motion Technology ADR, Hong Kong; ~$1.4B market cap
```

### Why _ETF_OVERRIDES (not analytical_universe.csv)?

The `_ETF_OVERRIDES` table is the established SIH mechanism for manually classifying symbols that are outside the scoring universe. Previous examples: DODFX, FIGFX, FMCSX, FCPGX (mutual funds), TTNDY (ADR). The analytical universe is source-controlled by the scoring pipeline — adding holdings-only symbols there would pollute the scoring dataset.

### Governance

- **No scoring changes.** The `_ETF_OVERRIDES` entries only set classification fields (asset_class, geography, market_cap_bucket, sector, industry). ESS/composite score generation is entirely separate.
- **No recommendation changes.** Holdings are already appearing in recs via their signal data; classification doesn't add or remove signal influence.
- **No CW-DAS / deployment queue changes.** Deployment queue uses signal-based scoring, not asset_class.
- **Pure allocation intelligence.** Only affects: allocation map, L1 sum (reconciliation), alignment scoring contribution.
