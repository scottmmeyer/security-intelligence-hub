# PERFORMANCE ATTRIBUTION DISCOVERY — PHASE 01A
**Date:** 2026-06-11
**Status:** Design Only — No Implementation

---

## 1. Motivation

During live portfolio management sessions, SIH demonstrated a systematic intelligence gap:

SIH explains *what* to do and *why* individual securities are attractive or deteriorating.

SIH **cannot explain why the portfolio performed the way it did.**

**Live example from 2026-06:**
- Fidelity reports: Portfolio 1M = -1.46%, S&P 500 = -1.65%, Excess Return = +0.19%
- SIH cannot answer: "Why did we beat the S&P?"
- Operator must manually interpret Fidelity performance reports outside SIH

This gap grows more critical as portfolio turnover increases and as the operator needs to validate that Concentrated Alpha decisions are generating alpha relative to passive benchmarks.

---

## 2. Existing Infrastructure Audit

### 2.1 Data Already Available in SIH

| Asset | Location | Content | Usable for Attribution? |
|-------|----------|---------|------------------------|
| Holdings snapshots | `holdings.csv` per PAR | symbol, market_value, percent_of_portfolio, cost_basis, snapshot_date | ✅ YES |
| Security price context | `price_context_by_symbol` (API) | return_1d, return_5d, return_1m, pct_52w_range | ✅ YES (1D/5D/1M only) |
| Benchmark returns | `data/current/benchmark_returns.csv` | Placeholder only (TEST data, 2 rows) | ❌ NOT PRODUCTION-READY |
| Replay performance series | `data/current/replay_performance_series.csv` | Daily price series for replay periods | ✅ YES (strategy-level, not portfolio-level) |
| Investable vehicle returns | `data/current/investable_vehicle_returns.csv` | Placeholder only | ❌ NOT PRODUCTION-READY |
| PAR run history | 230 PAR runs, 2026-05-21 through 2026-06-11 | Snapshots with weights, but only ~3 weeks of data | ⚠️ LIMITED |
| Fidelity native CSV | `incoming/portfolio/` | `Today's Gain/Loss Dollar`, `Today's Gain/Loss Percent`, `Total Gain/Loss Dollar`, `Cost Basis Total` | ✅ YES (Fidelity-calculated) |

### 2.2 Key Finding: Fidelity CSV Already Provides Return Data

The Fidelity portfolio export (`Portfolio_Positions_*.csv`) already contains:
- `Today's Gain/Loss Dollar` and `Today's Gain/Loss Percent` — position-level daily return
- `Total Gain/Loss Dollar` and `Total Gain/Loss Percent` — total unrealized P&L since purchase
- `Current Value` and `Cost Basis Total` — sufficient for simple return calculation

**What Fidelity does NOT provide in the position export:**
- Time-windowed portfolio returns (1M, 3M, YTD, 1Y, etc.) — these appear in Fidelity's Performance tab, not in the CSV export
- Benchmark comparison series
- Attribution detail

### 2.3 PAR Run History Depth
- 230 PAR runs spanning 2026-05-21 to 2026-06-11 (~21 calendar days)
- Each PAR stores a full holdings snapshot with weights and market values
- **Critical limitation:** 21 days of snapshots is insufficient for 3M, YTD, 1Y attribution

---

## 3. Summary Architecture Assessment

### Return Source Options

| Option | Source | Accuracy | Operational Cost |
|--------|--------|----------|-----------------|
| A — Fidelity native | Import via CSV or manual entry | HIGH (Fidelity's calculation is authoritative) | LOW — already ingested |
| B — yfinance calculation | Compute from security returns × weights | MEDIUM (point-in-time approximation) | LOW — infrastructure exists |
| C — Daily snapshot reconstruction | Accumulate PAR snapshots over time | HIGH (grows over time) | MEDIUM — requires consistent daily ingestion |
| D — Brinson attribution | Weight × security return per PAR period | MEDIUM-HIGH | MEDIUM — methodologically sound |

### Recommended Approach: Hybrid A+B+D
- **Return series (1D, 5D, 1M):** Compute from yfinance (infrastructure exists in `_build_price_context_payload`)
- **Longer windows (3M, YTD, 1Y):** Accept Fidelity as source of truth; ingest from Fidelity CSV or manual entry
- **Contribution analysis:** Simple Brinson (Weight × Return) using holdings weights from PAR + security returns from yfinance
- **Benchmark comparison:** yfinance for SPY, VTI, ACWX (no API cost, already used for price data)

---

## 4. Governance Confirmation

Performance Attribution is classified as a **display-only operator intelligence module.**

**Zero impact on:**
- CW-DAS scoring
- ESS signal
- PAP recommendation generation
- CRA capital rotation logic
- DIL posture determination
- Deployment Queue ranking
- Reduction Queue ranking

Attribution explains historical outcomes. It never influences forward-looking recommendations.
