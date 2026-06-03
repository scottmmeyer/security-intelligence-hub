# Phase 7.4A - Conviction Capital Deployment Analysis

**Account:** General Brokerage, Joint WROS - TOD, Individual - TOD  
**Snapshot Date:** 2026-05-30  
**Analysis Run:** `PAR-20260530-3A136D4F`  
**Mandate:** CONCENTRATED_ALPHA  
**Total Portfolio MV:** $473.9K  

> Advisory analysis only. No trade instructions. No execution sizing.
> Do not deploy capital based solely on this output.

---

## Step 1 - Deployable Capital

**Mandate target band:** 2.0-5.0% (CONCENTRATED_ALPHA)
**Target cash midpoint:** 3.00% = $14.2K

| Metric | Value |
|---|---|
| Actual Cash % | 8.96% |
| Actual Cash $ | $42.6K |
| Target Cash % | 3.00% |
| Target Cash $ | $14.2K |
| Excess Cash % | 5.96% |
| Excess Cash $ | $28.4K |
| **Deployable Cash** (above 2.0% floor) | **6.99%** |
| **Deployable $** | **$33.1K** |

**Cash instruments:**
- `SPAXX`: 8.96% ($42.6K)

> Cash is 5.96% above mandate target. Significant deployable capital identified.

---

## Step 2 - Conviction Universe (Owned Holdings Only)

Includes: CORE_CONVICTION_LEADER (CCL), HIGH_CONVICTION_ANCHOR (HCA)

**19 conviction-tier holdings identified in current portfolio.**

| Symbol | Weight | Composite | ESS | Zacks | Replay | Signal | Tier |
|---|---|---|---|---|---|---|---|
| `ARW` | 0.91% | 4.889 | VERY_BULLISH | 5.0 | Y | BULLISH | HCA |
| `PSX` | 0.74% | 4.722 | VERY_BULLISH | 5.0 | Y | BULLISH | HCA |
| `SNX` | 0.89% | 4.778 | VERY_BULLISH | 5.0 | Y | BULLISH | HCA |
| `AEIS` | 2.35% | 4.714 | UNKNOWN | 5.0 | Y | BULLISH | CCL |
| `LRCX` | 0.95% | 4.500 | VERY_BULLISH | 4.0 | Y | BULLISH | HCA |
| `SANM` | 0.67% | 4.714 | UNKNOWN | 5.0 | Y | BULLISH | HCA |
| `DELL` | 1.32% | 4.500 | VERY_BULLISH | 4.0 | Y | BULLISH | HCA |
| `VRT` | 3.62% | 4.556 | VERY_BULLISH | 4.0 | Y | BULLISH | CCL |
| `CVE` | 2.41% | 4.889 | VERY_BULLISH | 5.0 | Y | BULLISH | CCL |
| `ASML` | 0.68% | 4.722 | VERY_BULLISH | 4.0 | Y | BULLISH | HCA |
| `TSM` | 2.29% | 4.444 | VERY_BULLISH | 3.0 | Y | BULLISH | CCL |
| `STNG` | 0.47% | 4.714 | UNKNOWN | 5.0 | Y | BULLISH | HCA |
| `SIMO` | 0.30% | 4.571 | UNKNOWN | 5.0 | Y | BULLISH | HCA |
| `NVDA` | 3.20% | 4.111 | BULLISH | 4.0 | Y | BULLISH | CCL |
| `AVGO` | 0.93% | 4.000 | BULLISH | 4.0 | Y | BULLISH | HCA |
| `GTX` | 1.90% | 3.889 | BULLISH | 4.0 | Y | BULLISH | HCA |
| `MSFT` | 0.93% | 3.444 | BULLISH | 3.0 | Y | BULLISH | HCA |
| `MU` | 6.04% | 4.722 | VERY_BULLISH | 5.0 | Y | BULLISH | CCL |
| `SBS` | 3.85% | 3.714 | UNKNOWN | 4.0 | Y | BULLISH | HCA |

**Tier breakdown:** 6 CCL, 13 HCA

---

## Step 3 - Deployment Attractiveness Score (DAS) Methodology

### Formula

```
DAS = Signal(0-30) + Replay(0-20) + Conviction(0-25) + Sizing(0-15) + Momentum(0-10)
      - Redundancy Penalty(0-15) - Concentration Penalty(0-20)
Maximum possible: 100.0
```

### Component Definitions

| Component | Max | Calculation |
|---|---|---|
| Signal Quality | 30 | `composite / 5.0 x 30` (composite is 1-5 scale) |
| Replay Support | 20 | 20 if replay-supported, else 0 |
| Conviction Tier | 25 | CCL=25, HCA=20 |
| Sizing Headroom | 15 | `15 x (1 - current_pct / 6.0)` |
| Momentum | 10 | ESS+Signal: both bullish=10, one=7.5, neutral=4, bearish=0 |
| Redundancy Penalty | -15 | -15 if symbol node is OVERWEIGHT (MODERATE+) |
| Concentration Penalty | -20 | `-(pct - 6.0) x 4` when > 6%, capped at -20 |

### STI Tier Classification

Tiers derived by `build_strategic_profiles()` from the Trim Intelligence engine:

| Tier | Code | Criteria |
|---|---|---|
| CORE_CONVICTION_LEADER | CCL | BULLISH signal + replay + composite >= 4.0 + weight >= 1.5% |
| HIGH_CONVICTION_ANCHOR | HCA | strategic_classification == HIGH_CONVICTION_RETAIN |

### DAS Score Interpretation

| DAS Range | Interpretation |
|---|---|
| 75-100 | TIER 1 - High-priority deployment candidate |
| 55-74  | TIER 2 - Attractive deployment candidate |
| 35-54  | TIER 3 - Reasonable candidate, review context |
| <35    | Below threshold - limited attractiveness |

---

## Step 4 - Concentration Constraint Analysis

**Scenario:** Full deployable cash ($33.1K) into one position.
**Concentration ceiling:** 8.0%    **Soft-warn:** 6.0%

| Symbol | Current % | New % (full deploy) | Node | Flag |
|---|---|---|---|---|
| `MU` | 6.04% | 13.05% | `EQUITIES.US.MEGA` (OW) | RED CONCENTRATION_CONCERN |
| `VRT` | 3.62% | 10.63% | `EQUITIES.US.LARGE` | RED CONCENTRATION_CONCERN |
| `AEIS` | 2.35% | 9.35% | `EQUITIES.US.SMALL` | RED CONCENTRATION_CONCERN |
| `DELL` | 1.32% | 8.32% | `EQUITIES.US.LARGE` | RED CONCENTRATION_CONCERN |
| `LRCX` | 0.95% | 7.94% | `EQUITIES.US.LARGE` | YELLOW SOFT_WARN |

**Observations:**
- `MU`: Full deployment -> 13.05%, exceeds 8.0% ceiling.
- `VRT`: Full deployment -> 10.63%, exceeds 8.0% ceiling.
- `AEIS`: Full deployment -> 9.35%, exceeds 8.0% ceiling.
- `DELL`: Full deployment -> 8.32%, exceeds 8.0% ceiling.
- `LRCX`: Approaches 6.0% soft-warn at full deploy (7.94%).

---

## Step 5 - Top 15 Conviction Deployment Candidates

Ranked by DAS descending. Universe: 19 conviction-tier holdings.

| Rank | Symbol | Weight | Composite | Replay | Tier | DAS | Concentration Impact | Commentary |
|---|---|---|---|---|---|---|---|---|
| 1 | `ARW` | 0.91% | 4.889 | Yes | HCA | **92.06** | SOFT WARN - approaches 6% threshold | High conviction anchor; Strong composite (4.89); Replay-supported; ESS bullish; Warn: SOFT_WARN |
| 2 | `PSX` | 0.74% | 4.722 | Yes | HCA | **91.49** | SOFT WARN - approaches 6% threshold | High conviction anchor; Strong composite (4.72); Replay-supported; ESS bullish; Warn: SOFT_WARN |
| 3 | `SNX` | 0.89% | 4.778 | Yes | HCA | **91.44** | SOFT WARN - approaches 6% threshold | High conviction anchor; Strong composite (4.78); Replay-supported; ESS bullish; Warn: SOFT_WARN |
| 4 | `AEIS` | 2.35% | 4.714 | Yes | CCL | **89.91** | CONCERN - would exceed 8% threshold | Highest conviction tier; Strong composite (4.71); Replay-supported; Warn: CONCENTRATION_CONCERN |
| 5 | `LRCX` | 0.95% | 4.500 | Yes | HCA | **89.63** | SOFT WARN - approaches 6% threshold | High conviction anchor; Strong composite (4.50); Replay-supported; ESS bullish; Warn: SOFT_WARN |
| 6 | `SANM` | 0.67% | 4.714 | Yes | HCA | **89.12** | SOFT WARN - approaches 6% threshold | High conviction anchor; Strong composite (4.71); Replay-supported; Warn: SOFT_WARN |
| 7 | `DELL` | 1.32% | 4.500 | Yes | HCA | **88.7** | CONCERN - would exceed 8% threshold | High conviction anchor; Strong composite (4.50); Replay-supported; ESS bullish; Warn: CONCENTRATION_CONCERN |
| 8 | `VRT` | 3.62% | 4.556 | Yes | CCL | **88.27** | CONCERN - would exceed 8% threshold | Highest conviction tier; Strong composite (4.56); Replay-supported; ESS bullish; Warn: CONCENTRATION_CONCERN |
| 9 | `CVE` | 2.41% | 4.889 | Yes | CCL | **78.31** | CONCERN - would exceed 8% threshold | Highest conviction tier; Strong composite (4.89); Replay-supported; ESS bullish; Warn: CONCENTRATION_CONCERN |
| 10 | `ASML` | 0.68% | 4.722 | Yes | HCA | **76.63** | CONFLICT - OW node + position growth | High conviction anchor; Strong composite (4.72); Replay-supported; ESS bullish; Warn: MANDATE_CONFLICT |
| 11 | `TSM` | 2.29% | 4.444 | Yes | CCL | **75.94** | Clear | Highest conviction tier; Good composite (4.44); Replay-supported; ESS bullish |
| 12 | `STNG` | 0.47% | 4.714 | Yes | HCA | **74.62** | Clear | High conviction anchor; Strong composite (4.71); Replay-supported |
| 13 | `SIMO` | 0.30% | 4.571 | Yes | HCA | **74.18** | Clear | High conviction anchor; Strong composite (4.57); Replay-supported |
| 14 | `NVDA` | 3.20% | 4.111 | Yes | CCL | **71.68** | Clear | Highest conviction tier; Good composite (4.11); Replay-supported; ESS bullish |
| 15 | `AVGO` | 0.93% | 4.000 | Yes | HCA | **71.68** | Clear | High conviction anchor; Good composite (4.00); Replay-supported; ESS bullish |

### DAS Component Breakdown

| Symbol | Signal | Replay | Conv | Sizing | Momentum | Redund- | Conc- | DAS |
|---|---|---|---|---|---|---|---|---|
| `ARW` | 29.33 | 20.0 | 20.0 | 12.7 | 10.0 | 0.0 | 0.0 | **92.06** |
| `PSX` | 28.33 | 20.0 | 20.0 | 13.2 | 10.0 | 0.0 | 0.0 | **91.49** |
| `SNX` | 28.67 | 20.0 | 20.0 | 12.8 | 10.0 | 0.0 | 0.0 | **91.44** |
| `AEIS` | 28.29 | 20.0 | 25.0 | 9.1 | 7.5 | 0.0 | 0.0 | **89.91** |
| `LRCX` | 27.0 | 20.0 | 20.0 | 12.6 | 10.0 | 0.0 | 0.0 | **89.63** |
| `SANM` | 28.29 | 20.0 | 20.0 | 13.3 | 7.5 | 0.0 | 0.0 | **89.12** |
| `DELL` | 27.0 | 20.0 | 20.0 | 11.7 | 10.0 | 0.0 | 0.0 | **88.7** |
| `VRT` | 27.33 | 20.0 | 25.0 | 5.9 | 10.0 | 0.0 | 0.0 | **88.27** |
| `CVE` | 29.33 | 20.0 | 25.0 | 9.0 | 10.0 | 15.0 | 0.0 | **78.31** |
| `ASML` | 28.33 | 20.0 | 20.0 | 13.3 | 10.0 | 15.0 | 0.0 | **76.63** |
| `TSM` | 26.67 | 20.0 | 25.0 | 9.3 | 10.0 | 15.0 | 0.0 | **75.94** |
| `STNG` | 28.29 | 20.0 | 20.0 | 13.8 | 7.5 | 15.0 | 0.0 | **74.62** |
| `SIMO` | 27.43 | 20.0 | 20.0 | 14.3 | 7.5 | 15.0 | 0.0 | **74.18** |
| `NVDA` | 24.67 | 20.0 | 25.0 | 7.0 | 10.0 | 15.0 | 0.0 | **71.68** |
| `AVGO` | 24.0 | 20.0 | 20.0 | 12.7 | 10.0 | 15.0 | 0.0 | **71.68** |

**Tier summary:**
- TIER 1 (>= 75): `ARW`, `PSX`, `SNX`, `AEIS`, `LRCX`, `SANM`, `DELL`, `VRT`, `CVE`, `ASML`, `TSM`
- TIER 2 (55-74): `STNG`, `SIMO`, `NVDA`, `AVGO`

---

## Step 6 - Deployment Observations

### Capital Context

Portfolio holds 8.96% in cash ($42.6K) against a CONCENTRATED_ALPHA mandate target band of 2.0-5.0%. Deployable capital (above the 2.0% mandate floor) is **$33.1K** (6.99%).

### Conviction Universe Quality

- **19 conviction-tier holdings** (6 CCL, 13 HCA)
- Average composite score: **4.452**
- Replay-supported: **19/19**

### Top Candidates

**1. `ARW`** (DAS 92.06) - HIGH CONVICTION ANCHOR, composite 4.889, replay Yes. High conviction anchor; Strong composite (4.89); Replay-supported; ESS bullish; Warn: SOFT_WARN

**2. `PSX`** (DAS 91.49) - HIGH CONVICTION ANCHOR, composite 4.722, replay Yes. High conviction anchor; Strong composite (4.72); Replay-supported; ESS bullish; Warn: SOFT_WARN

**3. `SNX`** (DAS 91.44) - HIGH CONVICTION ANCHOR, composite 4.778, replay Yes. High conviction anchor; Strong composite (4.78); Replay-supported; ESS bullish; Warn: SOFT_WARN


### Concentration Guardrails

Full-deployment flags 4 monitored symbols (`MU`, `VRT`, `AEIS`, `DELL`) for concentration/mandate concerns.

### Key Limitations

- DAS is a relative attractiveness ranking, not an absolute sizing model.
- STI tiers derived from `build_strategic_profiles()` using live signal, replay, and composite data.
- Concentration analysis uses a single-symbol full-deployment stress test.
- No forward guidance or market timing implied.

---

*Analysis only. Not investment advice. Not a trade instruction.*
