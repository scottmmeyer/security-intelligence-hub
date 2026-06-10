# Decision Intelligence Layer — Signal Inventory

**Date:** 2026-06-10

---

## Currently Available Signals (No New Integration Required)

### Tier 1: Already in SIH (in _lastAnalysisData)

| Signal | Source | Field | Availability | DIL Use |
|---|---|---|---|---|
| StarMine ESS | Fidelity (daily) | `fidelity_signals.ess_text` | COVERED for ~80 symbols | Signal quality assessment |
| Fidelity StarMine Rating | Fidelity (daily) | `fidelity_signals.fidelity_rating` | Same as ESS | Primary signal direction |
| Consensus Matrix | Computed from ESS+Yahoo+Zacks | `fidelity_signals.consensus_matrix` | All scored symbols | Signal alignment classification |
| Analyst ABR | Yahoo supplemental (weekly) | `analyst_consensus.abr` | Most portfolio symbols | Street vs. model divergence |
| Analyst Count | Yahoo supplemental | `analyst_consensus.analyst_count` | Same | Coverage depth |
| Price Target | Yahoo supplemental | `analyst_consensus.price_target` | Most symbols | Upside/downside context |
| Upside % | Computed | `analyst_consensus.upside_pct` | Most symbols | Valuation context |
| Consensus Label | Computed | `analyst_consensus.consensus_label` | Most symbols | BUY / HOLD / SELL classification |
| Zacks Rating | Zacks (weekly) | `security_overlays.zacks_rating` | ~80 symbols | Earnings-momentum signal |
| Danelfin Score | Danelfin (weekly) | `security_overlays.danelfin_score` | ~80 symbols | Technical/ML signal |
| UCF Score & Label | Computed | `ucf_verdicts_by_symbol` | All scored | Portfolio conviction rank |
| Composite Score | Computed | `security_overlays.composite_score` | All scored | Multi-signal aggregate |
| Replay Percentile | Computed | `security_overlays.replay_percentile` | Replay-eligible | Historical outcome positioning |

### Tier 2: Available via FMP (already ingested via fmp_universe_enrichment)

| Signal | Field | Availability | DIL Use |
|---|---|---|---|
| EPS Surprise Q1 | `latest_eps_surprise_pct` | FMP FULL coverage | "EPS miss/beat" event trigger |
| Beat Rate 8Q | `beat_rate_8q` | FMP FULL coverage | Earnings track record |
| Q1–Q4 Surprise History | `q1_surprise_pct`…`q4_surprise_pct` | FMP FULL | Trend in surprise direction |
| Revenue Growth Q1 YoY | `revenue_growth_q1_yoy` | FMP FULL | Revenue trajectory |
| EPS Growth Q1 YoY | `eps_growth_q1_yoy` | FMP FULL | Earnings trajectory |
| Revenue Acceleration | `revenue_acceleration` | FMP FULL | Momentum in revenue growth |
| Buy/Hold/Sell Counts | `buy_count`, `hold_count`, `sell_count` | FMP FULL | Analyst distribution |
| EV/EBITDA | `ev_ebitda_ttm` | FMP FULL | Relative valuation |
| FCF Yield | `fcf_yield_ttm` | FMP FULL | Cash generation quality |
| ROE / ROIC | `roe_ttm`, `roic_ttm` | FMP FULL | Capital efficiency |
| Net Buy Score | `net_buy_score` | FMP FULL | Net analyst conviction |

### Tier 3: Available in SIH but not yet surfaced in DIL context

| Signal | Location | DIL Use |
|---|---|---|
| Signal refresh dates | `signal_source_metadata.zacks_refresh_date`, `danelfin_refresh_date` | Data freshness indicator — flag stale signals |
| Replay performance percentile | `ucf_verdicts_by_symbol.signal_summary` | Historical outcome context |
| Company profile / business summary | `data/signals/company_profile/latest_company_profile.csv` | Business context for unfamiliar symbols |
| FVI tier | `fvi_data` | Vehicle quality context |
| Policy state | `security_overlays.policy_type` | Operator constraint awareness |
| CRA source category + evidence | `_craProposal.sources[].evidence_summary` | Reduction rationale already computed |
| Allocation node drift | `alignment` data | Why position is in overweight/underweight context |

---

## Currently Unavailable Signals (Require New Integration)

### High Value, Moderate Complexity

| Signal | Source | Complexity | Governance Burden | Value |
|---|---|---|---|---|
| **1D / 5D / 30D price return** | Yahoo Finance yfinance (already installed) | Low | Low — display only | HIGH — explains "why did this appear now" |
| **Earnings date (next/last)** | Yahoo Finance calendar | Low | Low | HIGH — context for guidance-driven moves |
| **Intraday price change** | Yahoo Finance | Low | Low | HIGH — "stock down 15% today" context |
| **Analyst revision count (30D)** | FMP or Yahoo | Medium | Low | HIGH — are targets stale? |

### Medium Value, Medium Complexity

| Signal | Source | Complexity | Value |
|---|---|---|---|
| PE ratio vs. sector | FMP / Yahoo | Low | MEDIUM — valuation context |
| 52-week high/low | Yahoo Finance | Low | MEDIUM — technical context |
| Relative strength vs. index | Computed from prices | Medium | MEDIUM — market context |
| Earnings date / EPS estimate | Yahoo Finance | Medium | MEDIUM |

### Lower Value or High Complexity

| Signal | Source | Complexity | Value | Notes |
|---|---|---|---|---|
| News headlines | NewsAPI / Benzinga | High | HIGH potential | Requires API key, content policy review |
| Earnings call transcripts | FMP premium | High | HIGH potential | Expensive, governance heavy |
| Analyst reports | Premium data | Very High | HIGH | Cost-prohibitive for MVP |
| Insider transactions | SEC EDGAR | Medium | MEDIUM | Useful but not urgent |

---

## PRIM Signal Inventory (Example)

Based on current SIH data (PAR-20260609-87134CE1):

| Signal | Value | Source | Freshness |
|---|---|---|---|
| StarMine ESS | BEARISH (2.0) | Fidelity | 2026-06-09 |
| Fidelity Rating | SELL | Fidelity StarMine | 2026-06-09 |
| Zacks | 1.0 (STRONG BUY) | Zacks | 2026-06-09 |
| Danelfin | 5.0 (BULLISH) | Danelfin | 2026-06-09 |
| ABR | 1.86 (BUY) | Yahoo, 14 analysts | 2026-06-05 |
| Price Target | $143.79 | Yahoo | 2026-06-05 |
| Upside % | +18.0% | Computed | 2026-06-05 |
| Signal Alignment | PARTIAL_ALIGNMENT | Computed | 2026-06-09 |
| EPS Surprise Q1 | -30.6% | FMP | 2026-06-04 |
| Beat Rate 8Q | 85.7% | FMP | 2026-06-04 |
| Revenue Growth Q1 | +18.9% YoY | FMP | 2026-06-04 |
| Net Buy Score | +15 | FMP | 2026-06-04 |
| UCF Label | TRIM_WATCH | Computed | PAR time |
| Composite Score | 2.06 | Computed | PAR time |
| Company Profile | Primoris Services Corp, infrastructure EPC contractor | Company profile | 2026-06-04 |

**Gaps (require new data):**
- Current price / 1D return (not in SIH today)
- Next earnings date
- Analyst revision history (pre- vs. post-earnings targets)
- Recent news context
