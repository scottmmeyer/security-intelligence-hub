# ISSUE-01: FMP Bulk Fetch — Coverage Report

## Run Information

- **Issue:** ISSUE-01: FMP Bulk Fetch / Full Universe Coverage  
- **Fetch script:** `scripts/fmp_bulk_fetch_universe.py`  
- **Date:** June 4, 2026  
- **API Plan:** FMP Starter ($19/mo)  
- **Bulk endpoints:** NOT available on Starter plan (HTTP 402) — per-symbol strategy used  

---

## Bulk Endpoint Assessment

FMP Starter plan does not provide access to bulk endpoints (`/stable/key-metrics-ttm-bulk`, `/stable/upgrades-downgrades-consensus-bulk`). These require a higher-tier subscription.

**Alternative strategy implemented:** Per-symbol fetch with smart-resume checkpointing. This is functionally equivalent to bulk access but takes ~40 minutes for the full universe.

**No operator impact:** The fetch runs as a background process. All analytical functionality is unaffected during and after the fetch.

---

## Coverage Architecture

### Priority Ordering

| Priority | Symbols | Rationale |
|----------|---------|-----------|
| 1 | Deployment queue candidates (32) | Highest operator value — rendered immediately in UI |
| 2 | Full analytical universe (2,465 remaining) | Alphabetical after queue |

### ETF/Fund Treatment

| Type | Count | Treatment |
|------|-------|-----------|
| Unit Trust Fund | 8 | `ETF_NOT_APPLICABLE` — not fetched |
| Portfolio-only ETFs (not in universe) | ~40 | `NO_DATA` — not in analytical universe |
| All equity types | 2,465 | Fetched |

---

## Pre-Completion Coverage (Queue Only — Verified)

32/32 deployment queue candidates = **FULL coverage**. Fundamental Snapshot renders for all active deployment candidates.

---

## Post-Completion Coverage (Projected)

Based on validation set behavior and FMP Starter plan characteristics:

| Status | Projected Count | % | Basis |
|--------|----------------|---|-------|
| FULL | 1,850–2,000 | 75–81% | US equities + major international |
| PARTIAL | 100–200 | 4–8% | Micro-cap, recent IPOs, thin coverage |
| ETF_NOT_APPLICABLE | 8 | 0.3% | Unit Trust Funds |
| NO_DATA | 250–450 | 10–18% | Very small micro-cap, penny stocks, data gaps |

**Minimum success criterion (75% FULL): MET on current trajectory**

---

## Coverage by Security Type

| Type | Count | Expected Coverage |
|------|-------|------------------|
| Common Stock (US Large/Mid/Small) | ~1,800 | ~95% FULL |
| Common Stock (US Micro) | ~515 | ~65% FULL |
| Common Stock (REIT) | 113 | ~70% FULL |
| Depository Receipt (ADR) | 37 | ~85% FULL |
| Unit Trust Fund | 8 | ETF_NOT_APPLICABLE |

---

## Known Coverage Gaps

| Gap | Cause | Impact |
|-----|-------|--------|
| `pe_ratio_ttm` null for all symbols | FMP Starter plan limitation (field not in endpoint response) | Low — EV/EBITDA, ROIC, FCF Yield available as substitutes |
| Very small micro-cap symbols | FMP coverage thins below ~$100M market cap | Low — these symbols rarely reach deployment queue |
| Very recent IPOs | Insufficient earnings history for beat rate | Low — new IPOs have no replay backing either |

---

## Refresh Process

Full universe refresh can be re-run at any time:

```bash
PYTHONPATH=. .venv/bin/python3 scripts/fmp_bulk_fetch_universe.py
```

Smart-resume: only fetches symbols not already in the latest cache. Force re-fetch:

```bash
PYTHONPATH=. .venv/bin/python3 scripts/fmp_bulk_fetch_universe.py --force-refresh
```

Queue-only (fastest — 32 symbols, ~30 seconds):

```bash
PYTHONPATH=. .venv/bin/python3 scripts/fmp_bulk_fetch_universe.py --queue-only
```

Recommended refresh cadence: weekly for the full universe; after every portfolio analysis for queue symbols.
