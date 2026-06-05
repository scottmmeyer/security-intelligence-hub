# Phase 8.0B.1B — Symbol Validation

## Validation Results (Live Data — June 4, 2026)

### Q1: Are all fields attached correctly?

**YES — 10/11 equity symbols have all fields populated. `pe_ratio_ttm` is universally null (FMP Starter plan limitation, known since Phase 8.0B.1A.1).**

### Q2: Are ADRs working?

**YES — 3/3 ADRs (TSM, ASML, CVE) return FULL coverage.**

### Q3: Are international holdings working?

**YES — TSM (Taiwan), ASML (Netherlands), CVE (Canada) all return FULL coverage.**

### Q4: Are ETFs handled gracefully?

**YES — VXUS returns NO_DATA (not in analytical universe, FMP returns no data). This is correct behavior.**

### Q5: Are nulls handled correctly?

**YES — empty fields return empty string (not "None", "nan", or error). `pe_ratio_ttm` is consistently empty for all symbols, which is correct given the FMP Starter plan limitation.**

---

## Per-Symbol Validation Table

| Symbol | Type | Coverage | EV/EBITDA | ROE | ROIC | Beat Rate | Rev Growth | Consensus | Notes |
|--------|------|----------|-----------|-----|------|-----------|------------|-----------|-------|
| VRT | US Equity | FULL | 53.4x | 42.1% | 20.3% | 100% | +27.7% | BUY | All fields populated |
| DELL | US Equity | FULL | 27.4x | −363% | 18.5% | 85.7% | +18.8% | BUY | Negative ROE is real (leveraged balance sheet) |
| ARW | US Equity | FULL | 10.3x | 11.2% | 8.9% | 100% | +10.5% | BUY | All fields populated |
| PSX | US Equity | FULL | 8.3x | 14.7% | 7.8% | 71.4% | −7.6% | BUY | Revenue decline noted; energy commodity cycle |
| CAH | US Equity | FULL | 17.2x | −55.7% | 11.6% | 100% | −1.9% | BUY | Negative ROE is real (write-downs); ROIC positive |
| SNX | US Equity | FULL | 11.5x | 11.6% | 8.8% | 85.7% | +6.9% | BUY | All fields populated |
| TSM | ADR (Taiwan) | FULL | 20.4x | 36.9% | 25.8% | 85.7% | +32.9% | BUY | International ADR — FULL coverage confirmed |
| ASML | ADR (Netherlands) | FULL | 44.7x | 52.0% | 34.9% | 57.1% | +15.6% | BUY | International ADR — FULL coverage confirmed |
| CVE | ADR (Canada) | FULL | 7.7x | 15.2% | 10.1% | 83.3% | −14.0% | BUY | International ADR — FULL coverage confirmed |
| TSLA | US Equity | FULL | 149.3x | 4.8% | 3.2% | 57.1% | −2.9% | BUY | High EV/EBITDA reflects growth premium |
| AVGO | US Equity | FULL | 48.6x | 36.4% | 19.5% | 100% | +23.9% | BUY | All fields populated |
| VXUS | ETF (not in universe) | NO_DATA | — | — | — | — | — | — | Not in analytical universe; FMP returns no data |

---

## Data Quality Observations

### pe_ratio_ttm
- **100% null across all symbols**
- Confirmed absent from FMP Starter `/stable/key-metrics-ttm` response
- Not a data quality issue — it's a subscription tier limitation
- Field retained in schema for future upgrade compatibility

### Negative ROE values (DELL, CAH)
- DELL ROE = −363%: Correct — Dell has negative book equity from aggressive share buybacks and debt structure. EV/EBITDA (27.4x) and ROIC (18.5%) are more meaningful metrics.
- CAH ROE = −55.7%: Correct — Cardinal Health had significant write-downs. ROIC (11.6%) is positive and more meaningful.
- **Negative ROE values are valid financial data, not errors. They must NOT be treated as null or filtered.**

### Revenue declines (PSX, CAH, CVE, TSLA)
- Revenue growth < 0 is valid data reflecting commodity cycle dynamics (PSX, CVE) or business softness (TSLA)
- These values should render as-is in any diagnostic display

### ADR Handling
- FMP returns data by ticker symbol without requiring special ADR handling
- TSM, ASML, CVE all fetch correctly under their US ticker
