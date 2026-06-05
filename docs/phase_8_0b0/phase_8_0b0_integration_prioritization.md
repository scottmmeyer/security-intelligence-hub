# Phase 8.0B.0 — Integration Prioritization

**Date:** 2026-06-04  

---

## Evaluation Criteria

| Criterion | Description |
|-----------|-------------|
| **Implementation Effort** | 1=trivial, 5=complex |
| **Data Quality** | FMP data reliability and coverage for SIH universe (~689 symbols) |
| **Coverage** | % of SIH analytical universe covered by FMP |
| **Scoring Impact** | Which SIH scoring systems benefit |
| **Operator Value** | How directly this improves CRA/CW-DAS output quality |

---

## Top 10 Highest-Value FMP Integrations

### Rank 1 — Earnings Surprise History
**Endpoint:** `/earnings?symbol=X` (last 8 quarters)

| Criterion | Score | Notes |
|-----------|-------|-------|
| Implementation Effort | 2/5 | Simple per-symbol fetch, store as rolling array |
| Data Quality | Excellent | FMP earnings data is reliable and timely |
| Coverage | ~95% | Available for most US equities; less for international |
| Scoring Impact | CW-DAS momentum (+10), STI conviction, CRA category clarity |
| Operator Value | **Highest** — enables dislocation vs deterioration classification |

**What it enables:** Persistent beat history → conviction amplifier. Miss + guidance cut → thesis break confirmation. Prevents false sell signals after temporary earnings reactions.

---

### Rank 2 — Revenue and EPS Growth (Quarterly)
**Endpoint:** `/income-statement-growth?symbol=X&period=quarter`

| Criterion | Score | Notes |
|-----------|-------|-------|
| Implementation Effort | 2/5 | Same structure as earnings, 4-period rolling window |
| Data Quality | Excellent | Directly from financial statements |
| Coverage | ~95% US, ~80% international |
| Scoring Impact | CW-DAS momentum, CRA signal quality, STI growth classification |
| Operator Value | **Very High** — fundamental growth trajectory drives thesis validity |

**What it enables:** Revenue acceleration = conviction amplifier. Deceleration for 3+ quarters = thesis break signal. Required for dislocation framework.

---

### Rank 3 — Key Metrics TTM (Bulk)
**Endpoint:** `/key-metrics-ttm-bulk` (all symbols in one request)

| Criterion | Score | Notes |
|-----------|-------|-------|
| Implementation Effort | 1/5 | Single bulk API call, one response for entire universe |
| Data Quality | Good | Calculated from standardized FMP financials |
| Coverage | ~95% |
| Scoring Impact | Valuation gate for CW-DAS sizing, CRA TAX_AWARE_EXIT quality check |
| Operator Value | **Very High** — P/E, EV/EBITDA, FCF yield for every symbol at once |

**What it enables:** Valuation context for deployment decisions. FCF yield supports position sizing conviction. Prevents deploying into overvalued positions even when signal is strong.

---

### Rank 4 — Estimate Revisions (Grades/Upgrades/Downgrades)
**Endpoint:** `/grades?symbol=X` (last 90 days) or `/upgrades-downgrades-consensus-bulk`

| Criterion | Score | Notes |
|-----------|-------|-------|
| Implementation Effort | 2/5 | Rolling window, net upgrade/downgrade ratio |
| Data Quality | Good | Reflects institutional analyst actions |
| Coverage | ~85% US equities |
| Scoring Impact | CW-DAS momentum component, CRA signal validation |
| Operator Value | **High** — captures analyst sentiment shifts not yet in ESS |

**What it enables:** Estimate revision momentum = leading indicator for ESS direction. Upgrades following a dip → buying signal. Downgrades → thesis break confirmation.

---

### Rank 5 — Analyst Count and Target Distribution
**Endpoint:** `/price-target-summary?symbol=X`

| Criterion | Score | Notes |
|-----------|-------|-------|
| Implementation Effort | 1/5 | Already in Yahoo flow; FMP replaces/augments |
| Data Quality | Very Good | More consistent than Yahoo for mid/small caps |
| Coverage | ~90% |
| Scoring Impact | Confidence weighting in composite; thin coverage = uncertainty discount |
| Operator Value | **Medium-High** — analyst count weights signal reliability |

**What it enables:** Low analyst count (< 3 analysts) = lower confidence weight in composite. High analyst count with tight target range = high conviction signal. Replaces/augments Yahoo supplemental.

---

### Rank 6 — TTM Financial Ratios (Bulk)
**Endpoint:** `/ratios-ttm-bulk`

| Criterion | Score | Notes |
|-----------|-------|-------|
| Implementation Effort | 1/5 | Single bulk call |
| Data Quality | Good |
| Coverage | ~90% |
| Scoring Impact | Quality gate; STI classification of high-quality vs deteriorating businesses |
| Operator Value | **Medium-High** — gross margin and FCF margin trend |

**What it enables:** Business quality scoring. Declining gross margins = thesis risk. High FCF margin = durable business. Supports STI classification improvements.

---

### Rank 7 — Earnings Calendar
**Endpoint:** `/earnings-calendar` (upcoming 30 days)

| Criterion | Score | Notes |
|-----------|-------|-------|
| Implementation Effort | 1/5 | Simple calendar fetch |
| Data Quality | Excellent |
| Coverage | ~98% for US equities |
| Scoring Impact | CRA timing context; deployment risk management |
| Operator Value | **Medium** — "don't deploy into AVGO 2 days before earnings" |

**What it enables:** Upcoming earnings flag on CRA deployment targets. Allows operator to defer allocation or add pre-earnings context. Not scored — informational.

---

### Rank 8 — Income Statement Growth Bulk
**Endpoint:** `/income-statement-growth-bulk?year=2026&period=Q1`

| Criterion | Score | Notes |
|-----------|-------|-------|
| Implementation Effort | 1/5 | Single bulk call per quarter |
| Data Quality | Good |
| Coverage | ~90% |
| Scoring Impact | Same as Rank 2 but more efficient at scale |
| Operator Value | **Medium-High** — efficient coverage of full universe |

**Note:** Rank 2 and Rank 8 are the same data; Rank 8 is the efficient bulk approach vs per-symbol fetch.

---

### Rank 9 — Piotroski F-Score
**Endpoint:** `/financial-scores?symbol=X`

| Criterion | Score | Notes |
|-----------|-------|-------|
| Implementation Effort | 2/5 | Per-symbol call, annual update |
| Data Quality | Good |
| Coverage | ~85% |
| Scoring Impact | Quality screening; LOW_CONVICTION_REDUCTION validation |
| Operator Value | **Medium** — confirms business health for sell candidates |

**What it enables:** F-Score ≥ 7 = financially healthy (strong evidence against selling). F-Score ≤ 3 = financial deterioration (supports sell signal). Used as a quality filter in CRA source generation.

---

### Rank 10 — Sector PE Snapshot (Relative Valuation Context)
**Endpoint:** `/sector-pe-snapshot` and `/historical-sector-pe`

| Criterion | Score | Notes |
|-----------|-------|-------|
| Implementation Effort | 1/5 | Single call, sector-level not per-symbol |
| Data Quality | Good |
| Coverage | All sectors |
| Scoring Impact | Relative valuation context; cheap vs expensive vs sector |
| Operator Value | **Medium** — "AVGO trades at 14x when semis are at 22x = cheap" |

**What it enables:** Sector-relative P/E comparison. Supports dislocation framework ("valuation below sector average" condition).

---

## Integrations to Avoid

| Endpoint | Why Not |
|----------|---------|
| `/discounted-cash-flow` | Model-dependent, high variance, not deterministic |
| `/historical-ratings` (FMP internal) | Redundant with ESS + Danelfin |
| Technical indicators | SIH uses replay-based validity, not TA patterns |
| News APIs | Not integrated into scoring; no NLP infrastructure |
| Institutional 13F data | Interesting but not scoring-relevant in v1 |
| COT reports | Futures positioning; out of scope |

---

## Estimated Impact Matrix

| FMP Integration | CW-DAS | CRA | STI | Dislocation |
|----------------|--------|-----|-----|-------------|
| Earnings Surprise | +++momentum | +++source quality | ++classification | ✅ critical |
| Revenue/EPS Growth | +++momentum | +++source quality | +++growth tier | ✅ critical |
| Key Metrics TTM Bulk | ++sizing | +quality check | +quality | ✅ critical |
| Estimate Revisions | ++momentum | ++validation | +revision | ✅ supporting |
| Price Target (FMP) | +signal | +context | — | — |
| Ratios TTM Bulk | +quality | ++quality gate | ++quality | ✅ supporting |
| Earnings Calendar | — | +timing | — | — |
| Piotroski Score | +quality | +source gate | +quality | — |
| Sector PE | +relative val | — | — | ✅ supporting |
