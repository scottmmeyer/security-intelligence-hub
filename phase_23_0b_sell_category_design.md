# Phase 23.0B — Q2: Multi-Dimensional Sell Category Design

**Design Date:** 2026-06-03  
**Analysis Run:** PAR-20260603-AC8FD5F0  
**Scope:** Replace single bearish-detection mechanism with 7-category action framework

---

## Design Principle

The new framework does not start from "what signals are bearish?" It starts from: **"what portfolio actions are warranted right now?"** The operator reviews a prioritized action pipeline and decides what to act on. Signal deterioration is one input — not the organizing principle.

**Tax context is a ranking modifier within categories, not a category generator.** (See Q6.)

---

## Category Taxonomy

### Category 1: Signal Deterioration
**Trigger:** ESS individual equity signal = BEARISH or VERY_BEARISH, OR `opportunity_flag = "TRIM"`  
**Logic:** Security-specific intelligence signals reduced confidence in the holding. This is a signal-first recommendation.  
**Priority tier:** HIGH (BEARISH/TRIM), MODERATE (declining trend)  
**Data required:** `signal_direction`, `opportunity_flag`, `composite_score`  
**Current behavior:** This is the only category the current framework implements (imperfectly — reads wrong field for `opportunity_flag`)

**Example holdings (run PAR-20260603-AC8FD5F0):**
- TSLA: `signal_direction = BEARISH` → Cat 1 candidate
- PRIM: `signal_direction = BEARISH` → Cat 1 candidate

---

### Category 2: Strategic Exit
**Trigger:** Operator-designated exit candidate — former employer stock, legacy positions, inherited holdings, or any holding with explicit operator intent to reduce regardless of signal quality  
**Logic:** Operator knowledge supersedes signal. A NEUTRAL or even BULLISH holding may still be a strategic exit candidate (concentration risk, psychological bias, employer equity, estate positions).  
**Priority tier:** HIGH (operator-explicit designation), MODERATE (known but undesignated)  
**Data required:** Operator-curated flag or note (new field in state)  
**Current behavior:** Not implemented at all

**Example holdings (run PAR-20260603-AC8FD5F0):**
- FIS: Former employer stock, -38.1% unrealized loss, no intent to buy more → Cat 2 candidate (highest priority)

---

### Category 3: Allocation Reduction
**Trigger:** Holding resides in an allocation node flagged as REDUCE_OVERWEIGHT in the current recommendation set, AND the holding is a reduction lever for that node  
**Logic:** Portfolio construction analysis generates `REDUCE_OVERWEIGHT` recommendations for specific nodes. Each overweight node maps to constituent holdings. Those holdings become action candidates — regardless of their individual signal quality.  
**Priority tier:** Inherits severity of the allocation node (MODERATE > LOW)  
**Data required:** `alignment.csv` overweight nodes + holding-to-node mapping  
**Current behavior:** `REDUCE_OVERWEIGHT` recommendations exist in `recommendations.json` but do not generate any sell candidates in the tax actions UI

**Overweight nodes in current run:**

| Node | Actual | Target | Drift | Severity | Reduction Candidates |
|---|---|---|---|---|---|
| EQUITIES.INTERNATIONAL | 18.63% | 12.0% | +6.63% | MODERATE | DODFX, VXUS, VEA, FIGFX (and international individual equities) |
| EQUITIES.INTERNATIONAL.LARGE | 8.10% | 4.0% | +4.10% | MODERATE | DODFX (largest international large), VXUS, VEA |
| EQUITIES.US.MEGA.HYPER_MEGA | 9.88% | 6.3% | +3.58% | MODERATE | TSLA, NVDA |
| EQUITIES.US.SMALL | ~6.7% | ~3.5% | +3.19% | LOW | PRIM, other small-caps |
| EQUITIES.US.MICRO | ~3.2% | ~1.0% | +2.17% | LOW | Micro-cap holdings |
| EQUITIES.US.MEGA.ULTRA_MEGA | ~4.2% | ~2.5% | +1.72% | LOW | VOO, FXAIX (contribute to MEGA tier) |

**Example holdings (current run):**
- DODFX: `is_overweight_vs_target = true`, INTERNATIONAL.LARGE overweight → Cat 3 candidate (MODERATE)
- VXUS: INTERNATIONAL overweight → Cat 3 candidate (MODERATE)
- VEA: INTERNATIONAL overweight → Cat 3 candidate (MODERATE)
- FIGFX: INTERNATIONAL overweight → Cat 3 candidate (MODERATE)
- TSLA: HYPER_MEGA overweight (AND Cat 1 bearish signal — dual classification)

---

### Category 4: Funding Source
**Trigger:** Holding is a candidate to fund deployment of a higher-conviction BUY candidate, where the holding itself has lower conviction, is replaceable, or is positionally redundant  
**Logic:** When deployment intelligence identifies buy candidates (ARW, CVE, SNX, ATLC, MU, PSX, PRG, etc.) and available cash is insufficient, existing holdings should be ranked by "should this make way for something better?" Low-conviction holdings in non-overweight positions, WATCH/HOLD signals, and holdings with no strategic anchor purpose are candidates.  
**Priority tier:** Driven by the conviction gap between the sale candidate and the intended buy  
**Data required:** Deployment queue, conviction cards, buy candidate list  
**Current behavior:** Not implemented at all

**Ranking factors for funding source priority:**
1. Low composite score (< 3.5 = weak anchor)
2. Poor replay alignment (`replay_supported = false`)
3. Signal = NEUTRAL or UNKNOWN (not bearish, but not earning its place)
4. Allocation node = NOT underweight (don't drain from underweight nodes)
5. Unrealized loss preferred (loss + swap = tax-efficient)

---

### Category 5: Loss Harvest
**Trigger:** Holding has negative unrealized return (market value < cost basis) AND operator has available gain capacity OR wants to bank losses for future capacity  
**Logic:** Holding has declined in value. This may be tactical (harvest now) or strategic (holds regardless). The key is the loss itself generates action intelligence independent of signal quality. Signal direction may be NEUTRAL or even still BULLISH (company still viable, but purchased at too-high a price).  
**Priority tier:** HIGH (large loss + strategic exit), MODERATE (meaningful loss + NEUTRAL/UNKNOWN signal)  
**Data required:** `cost_basis`, `market_value` per holding (not currently in overlay — must be read from `holdings.csv` or holdings snapshot)  
**Current behavior:** Not implemented; framework cannot detect losses because cost_basis is not in overlay

**Example holdings (current run):**
- FIS: cost=$37,631.72, MV=$23,287.42, loss=**−$14,344.30 (−38.1%)** → highest-priority loss harvest in the portfolio
- No other holdings in current run have confirmed unrealized losses based on available data

---

### Category 6: Gain Harvest
**Trigger:** Holding has positive unrealized return AND operator has available gain capacity to absorb realized gain tax-free (net_realized_ytd is negative, absorbing gains up to capacity)  
**Logic:** Within available gain capacity ($24,730 in current state), realized gains are absorbed by prior losses — effectively tax-free. This creates an opportunity window to reposition holdings with unrealized gains without tax cost. Not signal-driven: a BULLISH holding with a gain can still be rotated tax-efficiently.  
**Priority tier:** MODERATE (within capacity window)  
**Tax context:** Constrained by available capacity; gains beyond capacity incur tax  
**Data required:** `cost_basis`, `market_value`, tax state  
**Current behavior:** Bucket E partially addresses this concept but never fires (cost_basis not in overlay)

**Available gain capacity (current state):** $24,730

**Holdings with gains absorbable within current capacity:**
| Symbol | Unrealized Gain | Absorbable? |
|---|---|---|
| TSLA | +$3,631 | Yes (within $24,730) |
| PRIM | +$7 | Yes |
| DODFX | +$2,751 | Yes |
| VOO | +$3,765 | Yes |
| FXAIX | +$1,302 | Yes |
| VXUS | +$869 | Yes |
| VEA | +$596 | Yes |
| FIGFX | +$151 | Yes |

---

### Category 7: Long-Term Deferral
**Trigger:** Holding is a sell candidate on signal, allocation, or strategic grounds but has a short-term holding period (< 12 months) — deferring the sale improves tax treatment from short-term to long-term rates  
**Logic:** If a holding would be in Category 1, 2, 3, or 5, but was purchased recently enough that gains are short-term, the tax cost of selling now vs. waiting for 12-month LT threshold may be materially different. This is NOT "don't sell" — it is "if the urgency isn't high, wait for better tax treatment."  
**Priority tier:** LOW (informational / timing advisory)  
**Data required:** `holding_days`, `unrealizedGL`, `cost_basis` (none currently in overlay)  
**Current behavior:** Bucket B partially addresses this concept but never fires (no holding_days data)

---

## Category Priority Matrix

| Category | Default Priority | Increases When | Decreases When |
|---|---|---|---|
| 1: Signal Deterioration | HIGH | VERY_BEARISH signal, TRIM flag | Signal stabilizing |
| 2: Strategic Exit | HIGH | Operator-explicit, former employer | Operator removes flag |
| 3: Allocation Reduction | MODERATE | Node drift > 5%, MODERATE severity | Drift shrinking |
| 4: Funding Source | MODERATE | High-conviction buy candidate available | No active buy targets |
| 5: Loss Harvest | HIGH | Large loss + available capacity | Loss small, no capacity |
| 6: Gain Harvest | MODERATE | Within available capacity window | Capacity exhausted |
| 7: Long-Term Deferral | LOW | Days to LT threshold < 30 | Already long-term |

---

## Bearing on Current Framework

The 7-category taxonomy is additive to the current bearish detection:

| Current Mechanism | New Taxonomy Mapping | Coverage Gap Closed? |
|---|---|---|
| `signal === "BEARISH"` | → Category 1 (Signal Deterioration) | Partially — Bucket A remains |
| `opportunity_flag === "TRIM"` (broken) | → Category 1 + fix field mapping | Yes — fix field name |
| Nothing | → Category 2 (Strategic Exit) | New |
| `REDUCE_OVERWEIGHT` recs (unused) | → Category 3 (Allocation Reduction) | New |
| Nothing | → Category 4 (Funding Source) | New |
| Bucket D (never fires) | → Category 5 (Loss Harvest) | Requires cost basis data |
| Bucket E (never fires) | → Category 6 (Gain Harvest) | Requires cost basis data |
| Bucket B (never fires) | → Category 7 (Deferral) | Requires holding_days |

**Signal detection should remain Category 1 — it should not be removed.** It is one of seven inputs, not the primary organizing principle.
