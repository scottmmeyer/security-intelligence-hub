# Phase 8.0B.1B — FMP Field Mapping

## Source-to-Output Field Mapping

### Dataset 1: key_metrics_ttm (`latest_fmp_key_metrics.csv`)

| Output Field | FMP API Field | FMP Endpoint | Null Rate (validation) |
|-------------|--------------|-------------|----------------------|
| `pe_ratio_ttm` | `peRatioTTM` | `/stable/key-metrics-ttm` | 100% — **field absent on Starter plan** |
| `ev_ebitda_ttm` | `evToEBITDATTM` | `/stable/key-metrics-ttm` | 0% |
| `price_to_fcf_ttm` | `priceToFreeCashFlowsTTM` | `/stable/key-metrics-ttm` | 0% |
| `fcf_yield_ttm` | `freeCashFlowYieldTTM` | `/stable/key-metrics-ttm` | 0% |
| `roe_ttm` | `returnOnEquityTTM` | `/stable/key-metrics-ttm` | 0% |
| `roic_ttm` | `returnOnInvestedCapitalTTM` | `/stable/key-metrics-ttm` | 0% |
| `earnings_yield_ttm` | `earningsYieldTTM` | `/stable/key-metrics-ttm` | 0% |

**Note on pe_ratio_ttm:** The FMP `/stable/key-metrics-ttm` endpoint does not return `peRatioTTM` in the Starter subscription. This was discovered during Phase 8.0B.1A.1 live API testing. The field is retained in the schema for future Tier upgrade compatibility. All other key_metrics fields are present and populated.

### Dataset 2: grades_consensus (`latest_fmp_grades_consensus.csv`)

| Output Field | FMP API Field | Null Rate |
|-------------|--------------|-----------|
| `strong_buy_count` | `strongBuy` | 0% |
| `buy_count` | `buy` | 0% |
| `hold_count` | `hold` | 0% |
| `sell_count` | `sell` | 0% |
| `strong_sell_count` | `strongSell` | 0% |
| `total_analysts` | sum of all | 0% |
| `net_buy_score` | derived | 0% |
| `consensus_label` | derived from score | 0% |

Consensus derivation: `net_buy_score = (strongBuy + buy) − (sell + strongSell)`; `consensus_label = BUY if score > 0, SELL if score < 0, HOLD if 0`

### Dataset 3: earnings_surprises (`latest_fmp_earnings_surprises.csv`)

| Output Field | FMP API Field | Null Rate |
|-------------|--------------|-----------|
| `latest_eps_surprise_pct` | computed from `epsActual` / `epsEstimated` | 0% |
| `beats_last_8q` | count of positive surprises | 0% |
| `beat_rate_8q` | beats / 8 | 0% |
| `q1–q8_surprise_pct` | per-row surprise % | 0% |

Beat/surprise calculation: `((epsActual − epsEstimated) / abs(epsEstimated)) × 100`
Filters: excludes future quarters (date > today); handles zero denominator.

### Dataset 4: income_growth (`latest_fmp_income_growth.csv`)

| Output Field | FMP API Field | Null Rate |
|-------------|--------------|-----------|
| `revenue_growth_q1_yoy` | `growthRevenue` (latest quarter) | 0% |
| `eps_growth_q1_yoy` | `growthEPS` (latest quarter) | 0% |
| `revenue_acceleration` | `growthRevenue[0] − growthRevenue[3]` | 0% |

Revenue acceleration: positive = revenue growth rate is accelerating vs. 4 quarters ago.

## Known Field Gaps

| Field | Status | Reason |
|-------|--------|--------|
| `pe_ratio_ttm` | Null for all symbols | Not returned by FMP Starter `/key-metrics-ttm` endpoint |
| `revenue_growth_q2–q4_yoy` | Available in raw CSV but not in enriched schema | Kept in earnings_surprises CSV; excluded from enriched schema to reduce width |
| `gross_profit_growth` | Available in raw CSV but not in enriched schema | Low operator value at Phase 1B |
