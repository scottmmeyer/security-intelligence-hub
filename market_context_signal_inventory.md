# Market Context Signal Inventory

Project: Security Intelligence Hub (SIH)  
Assessment: MCI Signal Inventory  
Date: 2026-06-06

## Q1) Market-Wide Phenomena SIH Should Attempt to Detect

Priority set (deterministic-first):

1. Macro regime shifts
- high-level risk-on/risk-off state
- inflation-growth regime direction (coarse labels only)

2. Volatility regime changes
- VIX absolute level and short-window change
- realized index volatility jump flags

3. Rate-shock context
- UST 2Y and 10Y absolute/relative move shock bands
- yield-curve shift steepening/flattening bands

4. Credit stress context
- IG/HY spread widening flags (or ETF proxy spread signals)

5. Sector rotation and breadth stress
- sector-relative drawdown concentration
- breadth deterioration (advancers/decliners, equal-weight vs cap-weight divergence)

6. Event-window context (scheduled)
- FOMC windows
- CPI/PPI/NFP windows
- Treasury refunding/issuance windows

7. Liquidity event proxies
- large issuance/IPO week flag (calendar-based)
- index-level gap+volume stress pattern flags

8. Commodity-linked shock context
- energy/metals/agriculture index shock flags for affected sectors

9. Geopolitical/regulatory shock markers
- only as external event tags with confidence LOW unless corroborated by measurable market-state changes.

## Q2) Data Sources Evaluation

| Source | Availability | Cost | Reliability | Implementation Complexity | Notes |
|---|---|---|---|---|---|
| Yahoo Finance (indices, VIX proxies, sector ETFs, yields via symbols) | High | Low/Free | Medium | Low | Best near-term bootstrap; rate/yield proxy quality must be validated. |
| FMP (market/economic endpoints where available) | Medium | Plan-dependent | Medium | Medium | Useful if already contracted; endpoint coverage varies by plan. |
| FRED (Federal Reserve Economic Data) | High | Free | High | Low-Medium | Strong for rates/spreads/macroecon series; deterministic and stable. |
| Treasury datasets (auctions/issuance schedules) | High | Free | High | Medium | Good for scheduled liquidity context; requires parser normalization. |
| CBOE VIX data (direct) | Medium | Varies | High | Medium | Better provenance than proxy symbols when licensed. |
| Economic calendar providers | Medium | Free->Paid tiers | Medium | Medium | Scheduled-event windows are useful; real-time revisions vary by provider. |
| News APIs (headline streams) | Medium | Paid for quality | Medium | High | High narrative risk and parsing ambiguity; not suitable for deterministic v1 scoring effects. |
| Alternative data (social/sentiment, options flow feeds) | Low-Medium | High | Variable | High | Defer for mature phase only after strict evidence gates. |

## Deterministic Signal Classes

### A. Objectively Measurable (Fail-Closed Friendly)
- index return shock thresholds
- VIX level and delta bands
- sector drawdown concentration
- breadth deterioration thresholds
- treasury yield move thresholds
- spread widening thresholds
- scheduled event-window flags

### B. Semi-Structured (Use with caution)
- large IPO calendar impact flags
- treasury issuance pressure flags beyond simple schedule windows

### C. Subjective/Narrative (Not Fail-Closed)
- "because of" headline attribution
- geopolitical causal narratives without corroborating state signals

## Recommended v1 Inventory (Minimum)

1. Risk regime label: RISK_ON / NEUTRAL / RISK_OFF
2. Volatility regime: NORMAL / ELEVATED / STRESS
3. Rates shock flag: NONE / MODERATE / SHARP
4. Sector breadth stress flag
5. Scheduled macro-event window flag
6. Evidence vector emitted with raw numeric drivers

This set is deterministic, low-cost, and auditable.
