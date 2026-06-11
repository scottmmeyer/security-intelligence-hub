# FIDELITY PERFORMANCE DATA INVENTORY
**Date:** 2026-06-11
**Purpose:** Identify all available Fidelity data sources for performance attribution

---

## 1. Fidelity Portfolio Position Export (Available)

**File pattern:** `Portfolio_Positions_<Month>-<DD>-<YYYY>.csv`
**Location in SIH:** `incoming/portfolio/`
**Ingestion frequency:** Manual (operator drops file; SIH processes it)

### Fields Available Per Position

| Fidelity Field | SIH Canonical Field | Attribution Use |
|----------------|--------------------|-----------------| 
| Symbol | symbol | Key |
| Current Value | market_value | Portfolio weight denominator |
| Today's Gain/Loss Dollar | — | 1D absolute contribution |
| Today's Gain/Loss Percent | — | 1D security return |
| Total Gain/Loss Dollar | — | Unrealized P&L since entry |
| Total Gain/Loss Percent | — | Total return since entry |
| Cost Basis Total | cost_basis | Entry price basis |
| Percent Of Account | percent_of_portfolio | Portfolio weight |
| Quantity | quantity | Share count |

### Limitation
The position CSV does **not** contain:
- Time-windowed portfolio returns (1M, 3M, YTD, 1Y)
- Benchmark comparisons
- Portfolio-level aggregate return
- Transaction history

---

## 2. Fidelity Performance Tab Data (Not Yet Imported)

Fidelity provides portfolio-level performance data at:
`Accounts → Performance → [select account] → Time Period`

**Available in Fidelity UI but not yet imported into SIH:**

| Return Period | Available in Fidelity | In SIH? |
|--------------|----------------------|---------|
| 1-Day | ✅ | ❌ |
| 5-Day (week) | ✅ | ❌ |
| 1-Month | ✅ | ❌ |
| 3-Month | ✅ | ❌ |
| YTD | ✅ | ❌ |
| 1-Year | ✅ | ❌ |
| 3-Year | ✅ | ❌ |
| 5-Year | ✅ | ❌ |
| Since Inception | ✅ | ❌ |

Fidelity also provides benchmark comparison in the same view (S&P 500, Total Market, ACWI ex-US).

### Import Path Options

**Option A — Manual entry:** Operator enters portfolio return values directly in SIH
- Low technical overhead
- Requires operator action each session
- Highest accuracy (Fidelity-calculated figures are authoritative)

**Option B — Fidelity Performance Report CSV:** Fidelity offers downloadable performance reports
- Medium technical overhead (ingest new file format)
- Semi-automated once ingestion pipeline is built
- Fields vary by report type

**Option C — yfinance portfolio return calculation:** Reconstruct from holdings × security returns
- Fully automated
- Approximate (ignores cash flows, dividends, corporate actions)
- Good for 1D/5D/1M; unreliable for longer windows

---

## 3. Fidelity Transaction History (Not Yet Imported)

Fidelity provides trade history exports showing:
- Buy/sell transactions with date, price, quantity, total cost
- Dividends received
- Corporate actions (splits, mergers)

**Required for:**
- Trade attribution ("VRT bought on X date at $Y price, now +Z%")
- Accurate long-window returns with cash flow adjustments

**Not currently imported into SIH.** Would require new `incoming/transactions/` pipeline.

---

## 4. SIH Internal Return Infrastructure (Existing)

### 4.1 `_build_price_context_payload()` — OPERATIONAL

Fetches via yfinance for every PAR holding:
- `return_1d` — previous close to current (1 calendar day)
- `return_5d` — 5 trading days ago to current
- `return_1m` — 1 month ago to current
- `pct_52w_range` — position in 52-week range

**Coverage limitation:** Only 1-month lookback. Cannot compute 3M, YTD, 1Y from current implementation.

### 4.2 `benchmark_returns.csv` — PLACEHOLDER ONLY

Current content is TEST data (2 rows). Not production-ready for attribution.

**Extension needed:** Add SPY, VTI, ACWX benchmark tickers to yfinance fetch.

### 4.3 `replay_performance_series.csv` — STRATEGY-LEVEL ONLY

Contains daily return series for replay strategy backtests. Not linked to live portfolio positions or actual account weights.

### 4.4 PAR Run Sequence — LIMITED HISTORY

230 PAR runs spanning ~21 calendar days.
- Sufficient for: short-window weight reconstruction, recent trade attribution
- Insufficient for: 3M, YTD, 1Y portfolio return calculation

---

## 5. Data Gap Matrix

| Attribution Need | Fidelity CSV | yfinance | PAR History | Gap |
|-----------------|-------------|----------|-------------|-----|
| 1D portfolio return | ✅ (today's G/L) | ✅ (compute) | ✅ | None |
| 5D portfolio return | ❌ | ✅ (compute) | ⚠️ (limited) | Minor |
| 1M portfolio return | ❌ | ✅ (compute) | ⚠️ (limited) | Minor |
| 3M portfolio return | ❌ | ⚠️ (approximate) | ❌ | Gap |
| YTD portfolio return | ❌ | ⚠️ (approximate) | ❌ | Gap |
| 1Y portfolio return | ❌ | ⚠️ (approximate) | ❌ | Gap |
| Benchmark 1D/5D/1M | ❌ | ✅ (SPY/VTI/ACWX) | N/A | None |
| Benchmark 3M/YTD/1Y | ❌ | ✅ (SPY/VTI/ACWX) | N/A | None |
| Contribution (1D) | ✅ (position G/L) | ✅ (weight × return) | ✅ | None |
| Trade attribution | ❌ | ✅ (return since PAR date) | ✅ | Partial |
| Allocation attribution | ❌ | ✅ (compute from weights) | ✅ | None |
| Dividends/income | ✅ | ❌ | ❌ | Gap (long windows only) |
