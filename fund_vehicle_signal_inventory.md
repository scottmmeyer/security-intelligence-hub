# Fund Vehicle Intelligence (FVI) Signal Inventory

Project: Security Intelligence Hub (SIH)  
Assessment: ISSUE-19 FVI Signal Framework  
Date: 2026-06-06

## Q2) Fund Evaluation Factors

FVI should use a multi-factor quality model with five required dimensions and one contextual dimension.

## 1) Performance Quality (Peer-Relative)

Signals:
- Total return percentile: 1Y, 3Y, 5Y, 10Y
- Rolling period consistency percentile (for example 3Y rolling windows)
- Benchmark-relative excess return percentile

Why it matters:
- Captures sustained delivery, not isolated recent outperformance.

Weight recommendation:
- High

## 2) Risk and Downside Quality

Signals:
- Sharpe percentile
- Sortino percentile
- Max drawdown percentile
- Downside capture percentile
- Volatility percentile

Why it matters:
- Distinguishes "high return through high risk" from durable quality.

Weight recommendation:
- High

## 3) Cost and Friction Efficiency

Signals:
- Expense ratio percentile within category and share class
- Load structure metadata (front-end, deferred, no-load)
- Estimated net cost drag

Why it matters:
- Costs are persistent and compound over holding horizon.

Weight recommendation:
- High

## 4) Manager and Process Stability

Signals:
- Lead manager tenure
- Team turnover/stability flags
- Style drift indicator versus mandate
- Holdings turnover trend

Why it matters:
- Stable process quality improves persistence of outcomes.

Weight recommendation:
- Medium-High

## 5) Peer Standing and Persistence

Signals:
- Category rank percentile
- Quartile distribution frequency
- Consistency ranking (multi-period)

Why it matters:
- Converts many indicators into interpretable peer-relative standing.

Weight recommendation:
- Medium-High

## 6) Portfolio Construction Characteristics (Context)

Signals:
- Concentration (top holdings weight)
- Sector/region tilts vs category norm
- Active share proxy (when available)
- Turnover

Why it matters:
- Explains how the fund generates outcomes and where hidden risks exist.

Weight recommendation:
- Medium

## Factor Priority Recommendation

Most important factors for initial governance-safe FVI:
1. Risk-adjusted peer performance persistence
2. Cost efficiency
3. Downside behavior
4. Manager/process stability
5. Portfolio characteristic diagnostics

## Proposed Initial Composite Structure

For initial quality scoring (advisory only):
- Performance persistence: 30%
- Risk/downside quality: 30%
- Cost efficiency: 20%
- Manager/process stability: 10%
- Portfolio characteristics/context: 10%

Governance note:
- Weights are an initial assessment recommendation and should remain configurable.
- No replacement action should be triggered by a single metric.
