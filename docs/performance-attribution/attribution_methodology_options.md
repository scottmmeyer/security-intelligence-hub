# ATTRIBUTION METHODOLOGY OPTIONS
**Date:** 2026-06-11
**Purpose:** Document attribution calculation approaches with accuracy and feasibility assessment

---

## 1. Portfolio Return Calculation

### Method A — Fidelity-Native Returns (Recommended for 3M+)

Fidelity calculates time-weighted or money-weighted returns with proper cash flow adjustments, dividend reinvestment, and corporate actions.

**Accuracy:** HIGH — authoritative
**Operational requirement:** Manual entry of portfolio return from Fidelity Performance tab, or import of Fidelity performance report CSV

**Implementation pattern:**
```python
# Operator-supplied return from Fidelity (manual or imported)
portfolio_returns = {
    "1d":  -0.12,  # percent
    "5d":  -0.88,
    "1m":  -1.46,
    "3m":  +2.31,
    "ytd": +8.47,
    "1y":  +18.20,
}
```

### Method B — Weight × Return Approximation (Recommended for 1D/5D/1M)

Compute portfolio return as:
```
Portfolio Return ≈ Σ (weight_i × return_i)
```

where `weight_i` = percent_of_portfolio from last PAR, `return_i` = return from yfinance price_context.

**Accuracy:** MEDIUM — valid approximation for short windows; drift error accumulates over longer periods
**Operational requirement:** None — fully automated
**Available inputs:**
- `percent_of_portfolio` — in every PAR holdings.csv
- `return_1d`, `return_5d`, `return_1m` — in price_context_by_symbol (already computed)

```python
def compute_portfolio_return(holdings, price_context, window="return_1m"):
    total = 0.0
    for h in holdings:
        sym = h["symbol"].upper()
        weight = float(h["percent_of_portfolio"]) / 100.0
        pc = price_context.get(sym, {})
        sec_return = pc.get(window)
        if sec_return is not None:
            total += weight * sec_return
    return total
```

**Known limitations:**
- Does not account for cash drag
- Does not account for dividends received during the period
- Uses beginning-of-period weights (not daily rebalanced)
- Cash/equivalents have near-zero returns but still carry weight

---

## 2. Contribution Analysis

### Standard Brinson Method

**Contribution to portfolio return:**
```
Contribution_i = Weight_i × Return_i
```

**Required inputs:**
- Portfolio weight at start of period (from holdings.csv)
- Security return over period (from price_context_by_symbol)

**Example calculation:**
```
VRT:  weight = 2.1%, return_1m = +20.0%  →  contribution = +0.42%
CVE:  weight = 1.8%, return_1m = +15.0%  →  contribution = +0.27%
KGC:  weight = 1.4%, return_1m = -25.0%  →  contribution = -0.35%
```

**Accuracy:**
- Accurate for short windows (1D, 5D)
- Approximate for 1M (beginning weights drift vs. actual daily weights)
- Not recommended for 3M+ without daily snapshots

**Data available:** ✅ Both inputs exist in current SIH infrastructure.

---

## 3. Allocation Attribution

### Simplified Sector/Node Allocation Attribution

```
Allocation Effect = (Portfolio Weight - Benchmark Weight) × (Benchmark Sector Return - Total Benchmark Return)
```

**Inputs required:**
- Portfolio allocation by node/sector (available from alignment.csv)
- Benchmark allocation by sector (requires building sector weight map for SPY/VTI)
- Sector returns for benchmark components (requires periodic sector ETF returns — XLK, XLF, etc.)

**Assessment:** This is the most complex attribution component. Not feasible in Phase 1 without building benchmark sector weight infrastructure.

**Phase 1 simplified approach:**
Report allocation *weight differences* vs. benchmark (what SIH already computes in alignment.csv) and note directional impact using contemporaneous returns:

```
International Overweight (+3.2pp vs SPY):
  VEA return -5.1% during period → estimated drag -0.16%

US Large Underweight (-4.8pp vs SPY):
  SPY return -1.65% during period → estimated benefit +0.08%
```

This is directionally correct even if not arithmetically exact.

---

## 4. Trade Attribution

### Method: Return Since Entry Date

For each transaction identifiable from PAR sequence:

```
Trade Return = (Current Price - Entry Price) / Entry Price
```

Available inputs:
- `cost_basis` in holdings.csv — can be used to back-calculate approximate entry price
- `quantity` — shares held
- PAR run date — approximate acquisition window
- `current_price` from price_context_by_symbol

```python
def compute_trade_return(holding, current_price):
    cost_basis = float(holding.get("cost_basis", 0))
    quantity   = float(holding.get("quantity", 0))
    if quantity > 0 and cost_basis > 0:
        avg_cost = cost_basis / quantity
        return (current_price - avg_cost) / avg_cost * 100
    return None
```

**Limitation:** Does not distinguish between positions acquired in different tranches. Uses average cost basis.

---

## 5. Method Selection Matrix

| Attribution Component | Phase 1 Method | Data Available | Accuracy | Effort |
|----------------------|---------------|----------------|----------|--------|
| Portfolio 1D/5D/1M return | Weight × Return (yfinance) | ✅ | Medium | Low |
| Portfolio 3M/YTD/1Y return | Fidelity manual entry | Partial | High | Low |
| Benchmark 1D-1Y return | yfinance (SPY/VTI/ACWI) | ✅ | High | Low |
| Excess return (alpha) | Subtract | ✅ | Medium-High | Trivial |
| Contribution analysis | Weight × Return | ✅ | Medium | Low |
| Allocation attribution | Simplified directional | ✅ (partial) | Low-Medium | Medium |
| Trade attribution | Cost basis method | ✅ | Medium | Low |

---

## 6. Accuracy Governance

All computed attribution values are **approximations** derived from end-of-period weights and point-in-time prices. They are not audit-grade calculations. SIH must display appropriate disclaimers:

> *"Attribution values are estimates based on end-of-period portfolio weights and approximate security returns. Cash flows, dividends, and intra-period weight changes are not reflected. For precise performance figures, refer to Fidelity account statements."*

This disclaimer is governance-mandatory and must appear on every attribution display.
