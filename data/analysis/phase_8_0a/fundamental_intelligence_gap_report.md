# Fundamental Intelligence Gap Report
**Phase 8.0A | Q7: What fundamental questions can SIH currently NOT answer, and how material are those gaps?**

Generated: 2026-06-02

---

## Overview

The SIH is a **signal intelligence system**, not a fundamental analysis system. Its current data architecture aggregates consensus signals from LSEG ESS, Zacks, and Danelfin AI — all of which are downstream of analyst research, earnings expectations, and price momentum. This report catalogs the specific fundamental questions SIH cannot currently answer and assesses the materiality of each gap.

---

## Gap 1: Revenue Growth Trajectory

**Question SIH Cannot Answer**: Is this company's revenue growth accelerating, stable, or decelerating?

**Why It Matters**: Revenue acceleration is the most powerful fundamental indicator of business momentum. A company like VRT growing at 14% → 29% → 36% has a fundamentally different risk/reward profile than one growing at 10% → 8% → 5% — even if both hold the same ESS score in the current snapshot.

**Current SIH Data**: None. SIH contains no revenue data for any symbol.

**Signals That Partially Capture This**: ESS incorporates analyst earnings sentiment, which is influenced by revenue expectations. But ESS cannot tell you *why* analysts are bullish or whether revenue growth is accelerating.

**Materiality**: CRITICAL. Revenue acceleration/deceleration is the primary driver of long-term position quality. Without this, SIH cannot distinguish structural leaders from cyclical bounce-backs.

**Resolution**: FMP API provides quarterly revenue with 1-day lag post-filing. ~$19/month.

---

## Gap 2: Analyst Estimate Revision Direction

**Question SIH Cannot Answer**: Are analyst earnings estimates being revised upward or downward, and at what pace?

**Why It Matters**: Estimate revisions are the core driver of Zacks Rank. But SIH ingests only the **current rank** — not the underlying revision count, revision magnitude, or trend direction. If 5 analysts raised estimates last week and 2 lowered this week, SIH sees Rank 1 both times but the trend is changing.

**Current SIH Data**: Zacks Rank (current snapshot). No revision history.

**Signals That Partially Capture This**: Zacks Rank is a proxy. ESS also incorporates revision sentiment. But both are black-box aggregations.

**Materiality**: HIGH. The revision trend is a leading indicator of signal score changes. Early access to revision momentum (before it affects rank) is a meaningful edge.

**Resolution**: FMP Premium ($29/month) or Zacks Data Feed includes revision counts. LSEG subscription may include this data.

---

## Gap 3: Earnings Beat/Miss History

**Question SIH Cannot Answer**: Has this company been consistently beating, meeting, or missing analyst earnings estimates?

**Why It Matters**: A company that has beaten EPS estimates 8 of the last 8 quarters has a different quality profile than one that has missed 3 of the last 4. Beat rate is predictive of future estimate revision direction. Companies with strong beat rates tend to hold signal scores better.

**Current SIH Data**: None.

**Signals That Partially Capture This**: Indirectly — high beat rates eventually show up in ESS and Zacks scores. But there is a multi-month lag.

**Materiality**: HIGH. Beat rate is also a proxy for management conservatism in guidance — "sandbagging" vs. realistic or aggressive guidance.

**Resolution**: Finnhub free tier provides earnings surprise data. $0/month for basic coverage.

---

## Gap 4: Forward Valuation Metrics (PE, PEG, EV/EBITDA)

**Question SIH Cannot Answer**: Is the current signal leader's stock price a reasonable valuation relative to its growth rate?

**Why It Matters**: The PSX case demonstrated this gap directly — PSX's ESS is Very Bullish, but at $180 with declining revenue and $119M FCF, the question "what are investors paying for?" cannot be answered. A Very Bullish ESS on a 30x PE company vs a 10x PE company have very different risk profiles.

**Current SIH Data**: None. No price-based valuation ratios.

**Signals That Partially Capture This**: Not really. ESS, Zacks, and Danelfin are signal-based and price-agnostic in their scoring logic.

**Materiality**: HIGH for position sizing. A signal leader at 2x PEG is riskier than the same signal leader at 0.5x PEG.

**Resolution**: Yahoo Finance (yfinance) or FMP provides Forward PE, PEG, EV/EBITDA in real-time. Near-free to automate.

---

## Gap 5: Free Cash Flow Quality Assessment

**Question SIH Cannot Answer**: Is this company's reported profit backed by actual cash generation, or is it an accounting artifact?

**Why It Matters**: PSX is the most glaring example — reported EPS of $10.15 for FY2025 with only $119M of FCF on a $72B market cap. If earnings quality is assessed, PSX's signal elevation becomes a potential false positive. VRT's EPS is backed by $2.28B FCF (FCF/NI > 1x) — a signal of exceptional earnings quality.

**Current SIH Data**: None.

**Signals That Partially Capture This**: Partly — Zacks Rank incorporates earnings quality via revision sentiment. But it does not directly measure FCF/NI conversion.

**Materiality**: MEDIUM-HIGH. Most relevant for commodity/energy companies (where FCF and EPS diverge in commodity cycles) and financial companies (where FCF is structurally different from NI).

**Resolution**: SEC EDGAR XBRL provides cash flow statements for free. FCF = Operating Cash Flow − CapEx. Derivable without a paid API.

---

## Gap 6: Margin Expansion vs Contraction

**Question SIH Cannot Answer**: Are this company's profit margins expanding or contracting over time?

**Why It Matters**: Margin expansion is evidence of pricing power, cost efficiency, or operating leverage. VRT's gross margin expansion from 28% to 37% over 4 years demonstrates a fundamental shift in business quality. Margin contraction in a signal leader is a warning sign that the earnings growth may not be sustainable.

**Current SIH Data**: None.

**Signals That Partially Capture This**: ESS analysts model margin expectations — so ESS scores partly reflect this. But the data is not directly accessible.

**Materiality**: MEDIUM. More relevant for high-margin businesses (Technology, Healthcare) than low-margin distributors (ARW, SNX).

**Resolution**: SEC EDGAR XBRL or FMP provides margin history. Near-free.

---

## Gap 7: Analyst Coverage Depth and Consensus Reliability

**Question SIH Cannot Answer**: How many analysts cover this company, and is the consensus reliable or noise-driven?

**Why It Matters**: ARW with 4 analysts has a fundamentally different signal reliability profile than VRT with 25. With 4 analysts where one is a Sell and one is a Hold, the "consensus" is heavily influenced by statistical noise. ESS and Zacks don't weight for coverage depth.

**Current SIH Data**: None (analyst count not ingested).

**Materiality**: MEDIUM. Most significant for smaller companies in the SIH universe.

**Resolution**: FMP, Finnhub, or stockanalysis.com provide analyst count. Free or low-cost.

---

## Gap 8: Debt Trajectory and Balance Sheet Risk

**Question SIH Cannot Answer**: Is this company's debt load increasing or decreasing, and is the interest coverage adequate?

**Why It Matters**: A signal leader with rapidly increasing leverage is at risk of earnings deterioration if interest rates rise or revenue slows. VRT's 1.3x Debt/EBITDA with 27.9x interest coverage is low risk. A different signal leader with 8x Debt/EBITDA and 1.5x coverage would be high risk regardless of its ESS score.

**Current SIH Data**: None.

**Signals That Partially Capture This**: ESS incorporates analyst risk assessments including balance sheet. Partially captured via Danelfin's technical signals.

**Materiality**: MEDIUM. Most relevant during rate cycle peaks and for leveraged buyout-era companies.

**Resolution**: SEC EDGAR XBRL or FMP balance sheet data.

---

## Summary Gap Priority Matrix

| Gap | SIH Can Answer | Materiality | Resolution Cost | Priority |
|-----|----------------|-------------|-----------------|----------|
| 1. Revenue growth trajectory | ❌ None | CRITICAL | $19/mo | P1 |
| 2. Estimate revision direction | ⚠️ Partial (Zacks) | HIGH | $29/mo | P1 |
| 3. Earnings beat/miss history | ❌ None | HIGH | $0 (Finnhub free) | P1 |
| 4. Forward valuation (PE, PEG) | ❌ None | HIGH | $0–19/mo | P1 |
| 5. FCF quality vs EPS | ❌ None | MEDIUM-HIGH | $0 (EDGAR) | P2 |
| 6. Margin expansion/contraction | ❌ None | MEDIUM | $0–19/mo | P2 |
| 7. Analyst coverage depth | ❌ None | MEDIUM | $0 | P2 |
| 8. Debt trajectory | ❌ None | MEDIUM | $0 (EDGAR) | P3 |

---

## Core Finding: The ESS-Zacks-Danelfin Trilemma

The three SIH signal sources each capture *downstream* reflections of fundamental momentum:

1. **ESS** (LSEG StarMine) — synthesizes analyst estimates, recommendation changes, and earnings momentum. It is fundamentals-informed but not fundamentals-transparent.
2. **Zacks Rank** — directly driven by earnings estimate revisions. The best current proxy for Gap 2 (revision direction) but a black-box.
3. **Danelfin AI** — technical/ML-based signals. Potentially picks up on price momentum that leads fundamental revisions.

None of the three sources directly answers the 8 gaps above. All three could score a commodity-cycle company (PSX) as Very Bullish / Rank 1 during a cyclical upturn while ignoring that FCF has collapsed 95%.

**The SIH is signal-complete but fundamentals-blind.** FMI fills the blind spot.

---

## Estimated Cost to Close P1 Gaps

| Item | Source | Monthly Cost |
|------|--------|--------------|
| Revenue + EPS history | EDGAR XBRL (free) or FMP ($19) | $0–19 |
| Forward estimates | FMP Starter | $19 |
| Beat/miss history | Finnhub (free tier) | $0 |
| Forward PE / PEG (calculated) | FMP or derived | $0 |
| Estimate revision counts | FMP Starter or Finnhub Premium | $0–29 |
| **Total P1 gap closure** | **FMP Starter** | **~$19/month** |

The full Phase 8.0B FMI data pipeline can be built for **~$19/month** (FMP Starter tier) if estimate revision counts are not required at daily granularity. For full revision tracking: ~$29/month (Finnhub Premium or FMP Professional).
