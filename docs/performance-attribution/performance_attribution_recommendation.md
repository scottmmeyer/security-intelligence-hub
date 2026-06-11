# PERFORMANCE ATTRIBUTION RECOMMENDATION
**Date:** 2026-06-11
**Purpose:** Implementation recommendation and data structure specifications

---

## 1. Implementation Recommendation

### Recommended Approach: Hybrid Model

**Tier 1 — Automated (implement Phase 1):**
- 1D/5D/1M security returns via yfinance (infrastructure exists)
- Portfolio 1D/5D/1M computed as Weight × Return
- Benchmark 1D/5D/1M via yfinance (SPY, VTI, ACWI)
- Contribution analysis (Top 5 contributors, Top 5 detractors)
- Trade return since cost basis

**Tier 2 — Manual entry (Phase 1 via operator import):**
- Portfolio 3M/YTD/1Y — operator enters Fidelity figures
- These appear in SIH as "Fidelity Reported" figures with timestamp

**Tier 3 — Future (Phase 2):**
- Daily snapshot accumulation for long-window computation
- Transaction-level trade attribution
- Brinson-Fachler allocation/selection/interaction decomposition
- Custom Concentrated Alpha benchmark

---

## 2. API Payload Design

### `portfolio_attribution` result dict field

```json
{
  "portfolio_attribution": {
    "as_of_date": "2026-06-11",
    "computation_method": "WEIGHT_X_RETURN",
    "portfolio_returns": {
      "1d":   { "value": -0.12, "source": "COMPUTED" },
      "5d":   { "value": -0.88, "source": "COMPUTED" },
      "1m":   { "value": -1.46, "source": "COMPUTED" },
      "3m":   { "value":  2.31, "source": "FIDELITY_REPORTED" },
      "ytd":  { "value":  8.47, "source": "FIDELITY_REPORTED" },
      "1y":   { "value": 18.20, "source": "FIDELITY_REPORTED" }
    },
    "benchmark_returns": {
      "SP500": {
        "1d": -0.31, "5d": -1.04, "1m": -1.65
      },
      "TOTAL_MARKET": {
        "1d": -0.28, "5d": -0.98, "1m": -1.52
      }
    },
    "excess_returns": {
      "vs_SP500": {
        "1d": +0.19, "5d": +0.16, "1m": +0.19
      }
    },
    "top_contributors": [
      { "symbol": "VRT",  "weight_pct": 2.1, "return_1m": 20.0, "contribution_1m": 0.42 },
      { "symbol": "CVE",  "weight_pct": 1.8, "return_1m": 15.0, "contribution_1m": 0.27 },
      { "symbol": "TSM",  "weight_pct": 1.9, "return_1m": 10.0, "contribution_1m": 0.19 }
    ],
    "top_detractors": [
      { "symbol": "KGC",   "weight_pct": 1.4, "return_1m": -25.0, "contribution_1m": -0.35 },
      { "symbol": "PRIM",  "weight_pct": 0.8, "return_1m": -27.5, "contribution_1m": -0.22 },
      { "symbol": "DODFX", "weight_pct": 2.2, "return_1m":  -5.0, "contribution_1m": -0.11 }
    ],
    "trade_attribution": [
      {
        "symbol": "VRT", "action": "BUY",
        "entry_price_est": 285.0, "current_price": 376.80,
        "return_since_entry_pct": 32.2,
        "source": "COST_BASIS_EST"
      },
      {
        "symbol": "ARW", "action": "BUY",
        "entry_price_est": 127.0, "current_price": 131.3,
        "return_since_entry_pct": 3.4,
        "source": "COST_BASIS_EST"
      }
    ],
    "allocation_attribution": [
      {
        "node": "EQUITIES.INTL",
        "portfolio_weight_pct": 15.2,
        "benchmark_weight_pct": 12.0,
        "overweight_pp": 3.2,
        "node_return_1m": -5.1,
        "estimated_drag_pp": -0.16,
        "direction": "DETRACTOR"
      }
    ],
    "governance_disclaimer": "Attribution values are approximations. Refer to Fidelity account statements for audited performance figures."
  }
}
```

---

## 3. Backend Implementation Map

### Phase 1 Components

| Component | Function | File | Effort |
|-----------|----------|------|--------|
| Portfolio return (1D/5D/1M) | `_compute_portfolio_return(holdings, price_ctx, window)` | `runner.py` | 1 hr |
| Benchmark return (1D/5D/1M) | `_fetch_benchmark_returns(tickers, window)` | `runner.py` (extend yfinance fetch) | 2 hrs |
| Excess return | arithmetic subtraction | `runner.py` | 30 min |
| Contribution analysis | `_compute_contribution_analysis(holdings, price_ctx)` | `runner.py` | 1 hr |
| Trade attribution | `_compute_trade_attribution(holdings, price_ctx)` | `runner.py` | 1 hr |
| Allocation attribution | `_compute_allocation_attribution(alignment, price_ctx)` | `runner.py` | 2 hrs |
| Fidelity return import | new operator input field | `api routes + state` | 2 hrs |
| API payload | add `portfolio_attribution` to result dict | `runner.py` | 30 min |
| UI rendering | `renderPerformanceAttribution(data)` | `app.js` | 4 hrs |

**Total Phase 1 estimated effort: ~14 hours**

---

## 4. UI Display Design

### Section Layout (proposed)

```
┌─────────────────────────────────────────────────────────┐
│  Portfolio Performance Attribution          2026-06-11   │
├─────────────┬──────────────┬──────────────┬─────────────┤
│  Period     │  Portfolio   │  S&P 500     │  Alpha      │
├─────────────┼──────────────┼──────────────┼─────────────┤
│  1D         │  -0.12%      │  -0.31%      │  +0.19% ▲   │
│  5D         │  -0.88%      │  -1.04%      │  +0.16% ▲   │
│  1M         │  -1.46%      │  -1.65%      │  +0.19% ▲   │
│  YTD *      │  +8.47%      │  +6.82%      │  +1.65% ▲   │
└─────────────┴──────────────┴──────────────┴─────────────┘
* Fidelity-reported figures

┌─────────────────────────────┐  ┌─────────────────────────┐
│  Top Contributors (1M)      │  │  Top Detractors (1M)    │
├─────────────────────────────┤  ├─────────────────────────┤
│  VRT    +0.42%              │  │  KGC    -0.35%          │
│  CVE    +0.27%              │  │  PRIM   -0.22%          │
│  TSM    +0.19%              │  │  DODFX  -0.11%          │
└─────────────────────────────┘  └─────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Trade Attribution                                       │
├──────────────┬──────────────┬───────────────────────────┤
│  VRT (BUY)   │  Est. entry: $285  │  +32.2% since entry │
│  ARW (BUY)   │  Est. entry: $127  │  +3.4% since entry  │
└──────────────┴──────────────┴───────────────────────────┘
```

---

## 5. Phase Sequencing

### Phase 1 — Core Attribution (Implement after PRA-IMPL-02 and AI-003)
- 1D/5D/1M portfolio return (computed)
- Benchmark comparison (SPY, VTI, ACWI via yfinance)
- Contribution analysis (Weight × Return)
- Trade attribution (cost basis method)
- Fidelity manual return import for 3M/YTD/1Y

### Phase 2 — Enhanced Attribution
- Daily PAR snapshot accumulation for long-window computation
- Brinson-Fachler full attribution decomposition
- Transaction-level trade attribution (requires transaction import)
- Custom Concentrated Alpha benchmark

### Phase 3 — Outcome Validation
- Correlate attribution with SIH recommendation history
- "SIH-recommended positions outperformed non-SIH positions by X%"
- Replay vs. live portfolio comparison
