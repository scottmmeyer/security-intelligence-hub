# Phase 8.0B.1A.1 — Coverage Analysis

**Date:** 2026-06-04  

---

## HTTP Status Summary (all 10 symbols × 4 datasets = 40 calls)

| Symbol | Type | key_metrics | grades | earnings | income_growth |
|--------|------|------------|--------|----------|--------------|
| VRT | US equity | ✅ 200 | ✅ 200 | ✅ 200 | ✅ 200 |
| DELL | US equity | ✅ 200 | ✅ 200 | ✅ 200 | ✅ 200 |
| ARW | US equity | ✅ 200 | ✅ 200 | ✅ 200 | ✅ 200 |
| AVGO | US equity | ✅ 200 | ✅ 200 | ✅ 200 | ✅ 200 |
| PSX | US equity | ✅ 200 | ✅ 200 | ✅ 200 | ✅ 200 |
| TSM | International ADR | ✅ 200 | ✅ 200 | ✅ 200 | ✅ 200 |
| ASML | International ADR | ✅ 200 | ✅ 200 | ✅ 200 | ✅ 200 |
| CVE | Canadian (NYSE-listed) | ✅ 200 | ✅ 200 | ✅ 200 | ✅ 200 |
| TSLA | US (policy example) | ✅ 200 | ✅ 200 | ✅ 200 | ✅ 200 |
| VXUS | ETF | ✅ 200 (empty) | ✅ 200 (empty) | ✅ 200 (empty) | ✅ 200 (empty) |

**Coverage rate: 100% for equities (9/9). ETFs: HTTP 200 but empty arrays.**

---

## Data Completeness by Symbol

| Symbol | km fields | gc fields | earnings quarters | income quarters |
|--------|-----------|-----------|------------------|-----------------|
| VRT | 2/9 target | 5/5 | 8 (7 past) | 4 |
| DELL | 2/9 target | 5/5 | 8 | 4 |
| ARW | 2/9 target | 5/5 | 8 | 4 |
| AVGO | 2/9 target | 5/5 | 8 | 4 |
| PSX | 2/9 target | 5/5 | 8 | 4 |
| TSM | 2/9 target | 5/5 | 8 | 4 |
| ASML | 2/9 target | 5/5 | 8 | 4 |
| CVE | 2/9 target | 5/5 | 8 | 4 |
| TSLA | 2/9 target | 5/5 | 8 | 4 |
| VXUS | 0/9 | 0/5 | 0 | 0 |

**Note on 2/9 key_metrics:** Only `earningsYieldTTM` and `freeCashFlowYieldTTM` match the originally assumed field names. The other 7 fields are present under different names — once the fetcher field map is corrected, coverage is **7/9** (peRatioTTM and revenuePerShareTTM absent on Starter).

---

## International Symbol Coverage

| Symbol | Exchange | Country | Coverage |
|--------|---------|---------|---------|
| TSM | NYSE (ADR) | Taiwan | ✅ Full data |
| ASML | NASDAQ | Netherlands | ✅ Full data |
| CVE | NYSE | Canada | ✅ Full data |

**Result:** All international ADRs and cross-listed companies with US exchange presence return full fundamental data. FMP's Starter plan covers the SIH international universe that trades on US exchanges.

---

## ETF Coverage

| Symbol | Type | Data |
|--------|------|------|
| VXUS | Vanguard Total Intl ETF | HTTP 200, empty array |

**Result:** ETFs return HTTP 200 but empty arrays across all 4 datasets. This is expected — ETFs have no earnings surprises, income statements, or analyst grades. The fetcher's fail-open behavior (empty = stub row with null fields) handles this correctly.

---

## SIH Universe Coverage Estimate

Based on this sample (100% US equity + ADR coverage), extrapolating to the 689-symbol universe:

| Category | Count (est.) | Expected Coverage |
|----------|------------|-----------------|
| US equities | ~580 | ✅ Full coverage |
| International ADRs/cross-listed | ~80 | ✅ Full coverage |
| ETFs/funds | ~20 | ❌ Empty data (expected) |
| Micro-cap / OTC | ~10 | ⚠ Partial coverage expected |

**Estimated data coverage: ~95% of equities, ~0% of ETFs**
