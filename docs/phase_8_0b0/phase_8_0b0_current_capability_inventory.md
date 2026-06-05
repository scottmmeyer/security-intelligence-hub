# Phase 8.0B.0 — Current Capability Inventory

**Date:** 2026-06-04  
**Type:** Capability audit — no implementation

---

## Signal Sources and Scores

### 1. ESS (Equity Summary Score) — StarMine / Zacks
| Field | Where Stored | Used In | Scoring Impact |
|-------|-------------|---------|----------------|
| `ess_score_text` | analytical_universe.csv, security_overlays.csv | CW-DAS signal component, opportunity_flag, STI classification | 55% weight in composite_score (primary signal) |
| `starmine_ess_numeric` | incoming/ess/starmine/ | Normalization only | Converted to text scale |
| `ess_score_text` values | VERY_BULLISH / BULLISH / NEUTRAL / BEARISH / VERY_BEARISH | Direction gates (signal_direction) | Determines BULLISH/BEARISH conviction classification |

**What it tells us:** Analyst consensus quality signal — StarMine's proprietary model weighting analyst accuracy.  
**What it does NOT tell us:** Why. No earnings context, no valuation context, no growth trajectory.

---

### 2. Zacks Rank
| Field | Where Stored | Used In | Scoring Impact |
|-------|-------------|---------|----------------|
| `zacks_rating` | analytical_universe.csv, security_overlays.csv | composite_score (normalized 1–5), consensus_matrix | ~20% weight in composite_score |
| `zacks_score` (normalized) | analytical_universe.csv | compute_consensus_matrix | Near-term earnings revision signal |

**What it tells us:** Near-term earnings revision momentum (Zacks 1–5 where 1=Strong Buy).  
**What it does NOT tell us:** Valuation, growth rates, earnings surprise history.

---

### 3. Danelfin AI Score
| Field | Where Stored | Used In | Scoring Impact |
|-------|-------------|---------|----------------|
| `danelfin_score` | analytical_universe.csv, security_overlays.csv | composite_score | ~20% weight; AI-generated technical/fundamental score |

**What it tells us:** Machine learning score (1–10) reflecting technical, fundamental, and sentiment signals. Fetched via Danelfin API daily.  
**What it does NOT tell us:** Component breakdown not surfaced in SIH. Treats as a black box.

---

### 4. Yahoo Finance Supplemental
| Field | Where Stored | Used In | Scoring Impact |
|-------|-------------|---------|----------------|
| `price_target` | data/signals/yahoo/latest_yahoo_supplemental.csv | composite_v2_yahoo, yahoo_abr_normalized | Upside calculation |
| `abr` (Analyst Buy Ratio, normalized 1–5) | Same | consensus_matrix | ~10% weight in composite_score |
| `upside_pct` | Same | UI display | Not used in scoring directly |
| `eps_growth_5yr` | Same | Not used in scoring | Stored but not consumed |

**What it tells us:** Price target consensus and analyst buy sentiment.  
**Critical gap noted:** `eps_growth_5yr` is fetched but **not used in any scoring**.

---

### 5. Replay Intelligence (proprietary)
| Field | Where Stored | Used In | Scoring Impact |
|-------|-------------|---------|----------------|
| `replay_supported` | security_overlays.csv | CW-DAS binary gate (+20 pts if True) | HIGH — binary gate, major CW-DAS differentiator |
| `best_replay_return` | security_overlays.csv | UI transparency | Not in composite_score |
| `replay_percentile` | security_overlays.csv | UI transparency | Not in composite_score |
| `replay_eligible` | analytical_universe.csv | Eligibility filtering | Determines if replay analysis ran |

**What it tells us:** Whether historical ESS signals for this security have actually generated positive returns (backtested signal validity).  
**What it does NOT tell us:** Whether recent price decline is replay-explainable.

---

### 6. Portfolio-Level Scores (derived)
| Field | Derived From | Used In |
|-------|-------------|---------|
| `composite_score` | ESS + Zacks + Danelfin + Yahoo ABR weighted sum | CW-DAS signal component, opportunity_flag, STI |
| `composite_v2_yahoo` | composite_score + yahoo upside weight | Stored, not primary |
| CW-DAS deployment_score | composite + replay + conviction tier + sizing headroom | Deployment queue ranking |
| `strategic_anchor_rank` | STI classification | CRA sell ordering |
| `trim_priority_score` | STI multi-factor analysis | CRA source sizing |
| `narrative_tier` (CCL/HCA) | Replay + composite + conviction | CW-DAS tier assignment |

---

## Structural / Classification Data
| Field | Source | Used In |
|-------|--------|---------|
| `market_cap_bucket` | Analytical universe | Allocation node derivation |
| `geography` | Analytical universe | Allocation node, alignment |
| `sector` / `industry` | Analytical universe | Thematic clustering, STI |
| `security_type` | Ingestion classification | Eligibility gating |
| `allocation_eligible` | Analytical universe | Deployment queue eligibility |
| `benchmark_id` | Analytical universe | Benchmark comparison |

---

## What SIH Cannot Currently Answer

| Question | Current Capability | Gap |
|----------|------------------|-----|
| Is this company growing revenue? | ❌ No fundamental data | Missing |
| Is valuation cheap after a pullback? | ❌ No P/E, EV/EBITDA | Missing |
| Did estimates get revised up or down? | ❌ No estimate revision data | Missing |
| Did the company beat earnings? | ❌ No earnings surprise data | Missing |
| Is FCF strong or deteriorating? | ❌ No cash flow metrics | Missing |
| Is ROIC above/below cost of capital? | ❌ No quality metrics | Missing |
| What is the upside to intrinsic value? | Partial (price target only) | Incomplete |
| Why did the stock drop? | ❌ Cannot diagnose | Missing |
