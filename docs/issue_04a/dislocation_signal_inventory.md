# Dislocation Signal Inventory
## ISSUE-04A Design Phase — June 5, 2026

---

## 1. Purpose

Catalog every currently-available SIH data source and classify its usability
for dislocation detection. "Usability" means: the field is reliable, available
with sufficient coverage, and provides non-redundant evidence of divergence.

---

## 2. Primary Signals

### ESS (Equity Summary Score — StarMine)

| Attribute | Value |
|-----------|-------|
| Source | StarMine via Fidelity export |
| Coverage | ~690 symbols (portfolio + universe) |
| Data type | Categorical: VERY_BULLISH, BULLISH, NEUTRAL, BEARISH, VERY_BEARISH |
| Refresh | Daily (from `EquitySummaryScores-DDMMMYYYY.csv`) |
| Composite weight | 55% |
| **Dislocation usability** | **✅ CORE** |

**Role:** ESS weakness (BEARISH or NEUTRAL) while fundamentals are strong is
the primary divergence signal. ESS is model-driven and aggregates multiple
sub-signals. When ESS is bearish but FMP fundamentals are intact, this is
the textbook dislocation condition. Used in Classes A1, A3, B1, B2.

---

### Danelfin Score

| Attribute | Value |
|-----------|-------|
| Source | Danelfin AI platform |
| Coverage | ~portfolio universe, normalized 1–10 |
| Data type | Float 1.0–10.0 |
| Refresh | Periodic |
| **Dislocation usability** | **✅ CORE** |

**Role:** AI-based short-term signal. Low Danelfin (< 3.0) alongside strong
fundamentals is the AI-divergence signal. Danelfin captures price momentum and
technical patterns; when these are bearish but business fundamentals are intact,
the divergence is meaningful. Used in Classes A1, B1, B2.

**Caution:** Danelfin is short-term biased. A low score may simply reflect
near-term volatility, not structural undervaluation. Should not be the sole
trigger.

---

### Zacks Rating (Normalized)

| Attribute | Value |
|-----------|-------|
| Source | Zacks Investment Research |
| Coverage | ~portfolio universe |
| Data type | Float 1.0–5.0 (normalized) |
| **Dislocation usability** | **⚠️ SUPPORTING** |

**Role:** Useful as a confirming signal in Class B1 (consensus-signal split)
but less reliable as a standalone dislocation indicator. Zacks is
trend-following and often lags ESS. Best used as a third confirmation rather
than a primary trigger.

---

### ABR (Average Broker Recommendation — Yahoo)

| Attribute | Value |
|-----------|-------|
| Source | Yahoo Finance (`recommendationMean`) |
| Coverage | 65.4% (1,681 / 2,570) — lower coverage than ESS |
| Data type | Float 1.0–5.0 (1.0 = Strong Buy) |
| Refresh | Daily |
| **Dislocation usability** | **✅ SUPPORTING** |

**Role:** ABR provides the analyst-consensus direction. When ABR indicates
strong buy sentiment (≤ 2.0) but ESS/Danelfin are weak, this is a Class B2
divergence. ABR alone is insufficient — coverage gaps at 65.4% mean many
symbols will lack this signal.

**Coverage constraint:** For the ~35% of symbols without ABR, Class B2 cannot
fire. The dislocation engine must gracefully handle ABR absence.

---

### Analyst Count

| Attribute | Value |
|-----------|-------|
| Source | Yahoo Finance (`numberOfAnalystOpinions`) — ISSUE-08 complete |
| Coverage | ~53 portfolio symbols populated (full universe next refresh) |
| Data type | Integer |
| **Dislocation usability** | **✅ GATING** |

**Role:** Does not drive dislocation detection directly, but gates Class B2 and
Class C signals. A low analyst count (< 5) means thin coverage — dislocation
signals from thin coverage names should be heavily discounted or suppressed.
Threshold recommendation: require analyst_count ≥ 10 for Class B2 and C triggers.

---

### Price Target / Upside %

| Attribute | Value |
|-----------|-------|
| Source | Yahoo Finance (`targetMeanPrice`) |
| Coverage | 97.9% (2,515 / 2,570) |
| Data type | Float (USD) and derived upside_pct |
| **Dislocation usability** | **⚠️ SUPPORTING with constraints** |

**Role:** High upside_pct alongside weak AI signals is informative. However,
analyst price targets have systematic upward bias and can lag events significantly.
Use as a co-occurrence requirement (Class C) only, not as a standalone trigger.
**Never use as the sole dislocation criterion.**

---

## 3. Fundamental Signals (FMP)

### Beat Rate (8Q)

| Attribute | Value |
|-----------|-------|
| Source | FMP (`earnings_surprises`) |
| Coverage | 98.7% (FULL) for the 2,475-symbol universe |
| Data type | Float 0.0–1.0 (proportion of 8 recent quarters with positive surprise) |
| **Dislocation usability** | **✅ CORE** |

**Role:** Beat rate is the single most useful fundamental dislocation signal.
It directly measures whether the company has consistently exceeded what analysts
expected — the same analysts whose ESS and ABR are now potentially diverging.
Threshold: ≥ 75% (6/8 quarters) for Class A1; ≥ 87.5% (7/8) for HIGH CONVICTION.

---

### Thesis Integrity

| Attribute | Value |
|-----------|-------|
| Source | FMP-derived via `_classify_thesis_integrity()` |
| Values | INTACT, QUESTIONABLE, DETERIORATING, INSUFFICIENT_DATA |
| **Dislocation usability** | **✅ GATING** |

**Role:** Thesis integrity is the primary gate for all dislocation detection.
A DETERIORATING or QUESTIONABLE thesis means the fundamental case is weakening —
this is the opposite of dislocation (it's validation of signal weakness). Only
INTACT thesis should trigger dislocation classes A1, A3, B1, B2, D1.

QUESTIONABLE thesis may qualify for a lower-confidence WATCH tier only.

---

### Fundamental Consistency

| Attribute | Value |
|-----------|-------|
| Source | FMP-derived via `_classify_fundamental_consistency()` |
| Values | CONSISTENT, MIXED, CONTRADICTORY, DATA_ANOMALY, INSUFFICIENT_DATA |
| **Dislocation usability** | **✅ SUPPORTING** |

**Role:** CONSISTENT fundamentals alongside signal weakness is a stronger
dislocation signal. CONTRADICTORY fundamentals should suppress the dislocation
classification — if the fundamentals themselves are sending mixed messages,
the "divergence" may simply be rational market uncertainty, not a dislocation.

---

### Revenue Growth (FMP)

| Attribute | Value |
|-----------|-------|
| Source | FMP income growth (`fmp_revenue_growth`) |
| Data type | Float (e.g., 0.15 = +15%) |
| **Dislocation usability** | **⚠️ SUPPORTING** |

**Role:** Positive revenue growth alongside signal weakness is a confirming
signal for Class A1. However, revenue growth alone is not sufficient — it must
be combined with beat rate (which controls for analyst expectations) to avoid
false positives in high-capex industries where growth is expected.

---

### ROIC / FCF Yield (FMP)

| Attribute | Value |
|-----------|-------|
| Source | FMP key metrics (`fmp_roic`, `fmp_fcf_yield`) |
| **Dislocation usability** | **⚠️ LOW PRIORITY** |

**Role:** Useful for confirming INTACT thesis, but SIH already uses these in
`_classify_thesis_integrity()` and `_classify_fundamental_consistency()`. Using
them again in dislocation scoring would introduce redundancy with the existing
Fundamental Modifier. Better to rely on thesis/consistency classifications as
proxies.

---

## 4. Position / Portfolio Signals

### Composite Score

| Attribute | Value |
|-----------|-------|
| Source | Computed from ESS (55%), Danelfin, Zacks, ABR |
| Range | 0.0–5.0 |
| **Dislocation usability** | **⚠️ INDIRECT** |

**Role:** Composite score summarizes all signal inputs. A high composite score
contradicts a dislocation hypothesis — if the signals agree with the fundamentals,
there is no divergence. Low composite score (≤ 3.0) alongside strong fundamentals
is a useful confirmation but already captured by ESS and Danelfin individually.

**Do not use as a primary dislocation driver.** It is a derived signal and its
components are better used directly.

---

### CW-DAS Score

| Attribute | Value |
|-----------|-------|
| Source | `compute_cw_das()` in `deployment_queue.py` |
| Range | 0–100+ |
| **Dislocation usability** | **❌ NOT APPROPRIATE** |

**Role:** CW-DAS is a deployment priority score, not a signal quality score.
A low CW-DAS score may reflect node overweight, concentration penalty, or
non-eligibility — none of which constitute dislocation. Using CW-DAS for
dislocation detection would conflate deployment mechanics with investment signal.

---

### Fundamental Modifier

| Attribute | Value |
|-----------|-------|
| Source | `compute_fundamental_modifier()` in `deployment_queue.py` |
| Range | -5.0 to +3.0 |
| **Dislocation usability** | **⚠️ SUPPORTING — partially** |

**Role:** A positive modifier (+2.0 to +3.0) indicates strong beat rate + INTACT
thesis + CONSISTENT fundamentals — this is exactly the condition that supports a
HIGH CONVICTION dislocation when signals are simultaneously weak. However, the
modifier is CW-DAS-internal and represents the same FMP inputs already being
considered. It could serve as a fast-path indicator: `fundamental_modifier ≥ 2.0
AND (ESS weak OR Danelfin ≤ 3.0)` as a shorthand trigger.

---

### Replay Percentile

| Attribute | Value |
|-----------|-------|
| Source | `replay_percentile` in `security_overlays` |
| Range | 0–100 |
| **Dislocation usability** | **✅ CORE for Class D1** |

**Role:** Historical replay support is one of SIH's most distinctive signals.
A high replay percentile (≥ 65th) means the security has historically strong
performance evidence. When current signals (ESS, Danelfin) are weak despite this
evidence, that is a replay-based dislocation. This is the strongest defensible
class because it is grounded in actual historical outcomes, not analyst opinion.

---

### replay_supported (Boolean)

| Attribute | Value |
|-----------|-------|
| Source | `replay_supported` in `security_overlays` |
| Type | Boolean |
| **Dislocation usability** | **✅ GATING for Class D1** |

**Role:** Gate: `replay_supported = True` is a prerequisite for Class D1.
Without verified replay support, the historical evidence claim is unsubstantiated.

---

### narrative_tier (CCL / HCA)

| Attribute | Value |
|-----------|-------|
| Source | Strategic Profile / UCF |
| Values | CORE_CONVICTION_LEADER, HIGH_CONVICTION_ANCHOR, others |
| **Dislocation usability** | **⚠️ CONTEXT ONLY** |

**Role:** CCL/HCA status should not gate dislocation detection — non-CCL/HCA
names can still be dislocated. However, tier context is useful for the watchlist
display: a CCL-tier holding with a HIGH CONVICTION dislocation has higher
operator relevance than a WATCH-TRIM holding with the same signal.

---

### Allocation Drift (Over/Under weight)

| Attribute | Value |
|-----------|-------|
| Source | `alignment_results` |
| **Dislocation usability** | **❌ NOT APPROPRIATE** |

**Role:** Allocation drift reflects portfolio construction decisions, not
security-level signal divergence. An underweight holding with strong signals
is a deployment queue concern (CW-DAS captures this via `headroom_pct`),
not a dislocation.

---

### STI Classification

| Attribute | Value |
|-----------|-------|
| Source | `HoldingStrategicProfile.strategic_classification` |
| Values | HIGH_CONVICTION_RETAIN, CORE_RETAIN, WATCH_TRIM_CANDIDATE, TRIM_CANDIDATE |
| **Dislocation usability** | **⚠️ CONTEXT ONLY** |

**Role:** Strategic classification provides context for how significant a
dislocation is for the operator. A HIGH_CONVICTION_RETAIN holding with a
dislocation signal warrants immediate attention. A WATCH_TRIM_CANDIDATE with
a dislocation signal suggests signal confusion requiring review. Do not use
as a detection input — use as a display context field.

---

### Market Cap

| Attribute | Value |
|-----------|-------|
| Source | Holdings enrichment |
| **Dislocation usability** | **❌ NOT APPROPRIATE** |

**Role:** Market cap is not relevant to signal divergence detection. Small-cap
names may have less analyst coverage (captured by analyst_count) but market cap
itself is not a dislocation input.

---

### Portfolio Weight

| Attribute | Value |
|-----------|-------|
| Source | `percent_of_portfolio` in holdings |
| **Dislocation usability** | **❌ NOT APPROPRIATE** |

**Role:** Portfolio weight determines deployment priority (CW-DAS headroom),
not signal divergence. A large position with dislocation signals is more
*important* to act on, but the weight doesn't define *whether* dislocation exists.

---

## 5. Summary Table

| Signal | Class | Usage |
|--------|-------|-------|
| ESS | A1, A3, B1, B2, D1 | ✅ CORE |
| Beat Rate (FMP) | A1, A3 | ✅ CORE |
| Thesis Integrity | All | ✅ GATING |
| Replay Percentile | D1 | ✅ CORE |
| replay_supported | D1 | ✅ GATING |
| ABR | B1, B2, C | ✅ SUPPORTING |
| Analyst Count | B2, C | ✅ GATING |
| Danelfin | A1, B1, B2 | ✅ CORE |
| Fundamental Consistency | All | ✅ SUPPORTING |
| Fundamental Modifier | Shortcut trigger | ⚠️ SUPPORTING |
| Upside % | C only | ⚠️ SUPPORTING (co-occurrence) |
| Revenue Growth (FMP) | A1 confirming | ⚠️ SUPPORTING |
| Zacks | B1 confirming | ⚠️ SUPPORTING |
| Composite Score | Confirmation | ⚠️ INDIRECT |
| ROIC / FCF Yield | Redundant with thesis | ⚠️ LOW PRIORITY |
| narrative_tier | Display context | ⚠️ CONTEXT ONLY |
| STI Classification | Display context | ⚠️ CONTEXT ONLY |
| CW-DAS Score | ❌ | NOT APPROPRIATE |
| Allocation Drift | ❌ | NOT APPROPRIATE |
| Portfolio Weight | ❌ | NOT APPROPRIATE |
| Market Cap | ❌ | NOT APPROPRIATE |
