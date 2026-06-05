# Phase 23.4A — Q4: Prioritization Framework
**DESIGN ONLY — NO IMPLEMENTATION**
**Generated:** 2026-06-04
**Baseline:** PAR-20260604-8DB0393D | 853 tests | 0 failures | 1 skip

---

## 1. The Prioritization Problem

When 25+ EXECUTABLE, BULLISH candidates exist in the deployment queue (as is typical in a 32-entry queue with strong market conviction), the NBA framework must present only top 3–5 to the operator. The question is: **which ranking criterion should govern selection?**

This document evaluates six candidate ranking criteria, selects the optimal composite, and specifies tie-break behavior.

---

## 2. Candidate Ranking Criteria

### 2.1 Criterion A: `deployment_score` (CW-DAS)

**What it is:** Composite score from CW-DAS (0–100). Formula:
```
Signal(0-30) + Replay(0-20) + Conviction(35/28/10) + Sizing(0-8) + Momentum(0-10)
- Redundancy_Pen(0-15) - Conc_Pen(0-20)
```

**Pros:**
- Already computed, fully ranked in `deployment_queue.json`
- Multi-dimensional: integrates signal, replay, conviction, sizing, momentum, concentration
- The purpose of CW-DAS is exactly to answer "which candidate should I deploy capital into next?"
- No additional computation required

**Cons:**
- May rank highly-concentrated positions below less-concentrated ones due to `Conc_Pen`
- Does not directly account for mandate alignment or headroom

**Assessment:** STRONG CANDIDATE. This is the purpose-built ranking signal.

---

### 2.2 Criterion B: Narrative Tier (CCL > HCA > WATCH > REDUCE)

**What it is:** UCF narrative tier assignment. CCL = highest conviction, HCA = strong conviction.

**Pros:**
- Directly reflects portfolio conviction model
- Human-readable hierarchy
- Stable (doesn't fluctuate on intraday signals)

**Cons:**
- Ordinal, not continuous — many candidates share the same tier (e.g., all 28 HCA entries)
- Cannot differentiate within tier
- Does not capture momentum, sizing opportunity, or headroom

**Assessment:** USEFUL AS TIE-BREAK ONLY. Not sufficient as primary ranking.

---

### 2.3 Criterion C: ESS Score (Composite Signal Strength)

**What it is:** ESS composite score (1.0–5.0), sourced from `ess_score_text` or `composite_score` in `security_overlays.csv`. VERY_BULLISH ≈ 4.5+.

**Pros:**
- Direct signal strength indicator
- Captures recent multi-source agreement

**Cons:**
- ESS is already embedded in CW-DAS `Signal` component (0–30)
- Redundant if CW-DAS is primary
- Some deployment queue entries have missing ESS (ETF entries, early-cycle securities)

**Assessment:** ALREADY CAPTURED IN CW-DAS. Not needed as separate criterion.

---

### 2.4 Criterion D: UCF Conviction Score (0–100)

**What it is:** UCF raw conviction score per security (`ucf_verdicts.json`).

**Pros:**
- Captures long-term conviction independent of short-term signals
- Already computed, stable

**Cons:**
- UCF conviction is already a major component of CW-DAS (`Conviction` component = 35/28/10 points)
- Double-counting with CW-DAS
- `ucf_verdicts.json` not currently loaded by `app.js` — adding it is a data loading change

**Assessment:** REDUNDANT WITH CW-DAS. UCF rank used as secondary tie-break only if available.

---

### 2.5 Criterion E: Headroom (% available before concentration trigger)

**What it is:** Percent of portfolio available to add before hitting concentration limit. Available in `deployment_queue.json` `notes` field as "X% headroom."

**Pros:**
- Directly actionable — tells operator "how much can I add?"
- Prevents recommending an alternative that is itself concentration-constrained

**Cons:**
- Currently embedded in the `notes` string (not a structured field)
- Requires parsing: `notes.match(/(\d+)% headroom/)` — fragile
- Does not differentiate signal quality — high headroom ≠ high conviction

**Assessment:** USEFUL AS FILTER, not as primary ranking. Exclude candidates with 0% headroom. Beyond that, CW-DAS is more informative than headroom alone.

---

### 2.6 Criterion F: Composite Score (Custom Weighted Formula)

**What it is:** A custom NBA-specific composite: `w1*deployment_score + w2*headroom + w3*narrative_tier_weight`

**Pros:**
- Can be tuned for NBA-specific priorities
- More nuanced than single-criterion ranking

**Cons:**
- Introduces new opaque scoring weights requiring calibration and documentation
- Violates the "presentation layer only" constraint in spirit — introducing a new scoring formula is functionally a scoring change
- Hard to explain to operator why rank N in NBA differs from rank N in deployment queue
- Maintenance burden for weights

**Assessment:** REJECTED. Violates spirit of "no new scoring." The NBA presentation layer must not create a shadow scoring system that contradicts the deployment queue.

---

## 3. Recommended Prioritization Model

### 3.1 Decision

**Primary: `deployment_score` (CW-DAS rank order)**

This is the correct answer. CW-DAS exists precisely to answer "which security should receive capital next?" The NBA framework should not second-guess it. An operator seeing NBA alternatives should see the same ranking as they would in the deployment queue — because that IS the deployment queue, filtered to executable alternatives.

The ranking is:
```
rank_nba = rank_cw_das  (for eligible candidates)
```

### 3.2 Eligibility Pre-Filters (Applied Before Ranking)

```
INCLUDE IF:
  ✓ execution_state == "EXECUTABLE"
  ✓ signal_direction == "BULLISH"  (for ACCUMULATE actions)
  ✓ narrative_tier in {CCL, HCA}   (for MANDATE_BLOCKED / ETF_GATE_FAILED)
  ✓ headroom > 0%                  (exclude fully-saturated positions)

EXCLUDE IF:
  ✗ execution_state == "BLOCKED_BY_POLICY"
  ✗ signal_direction == "BEARISH"
  ✗ headroom == 0% (at concentration limit)
```

### 3.3 Tie-Break Rules (When `deployment_score` is Equal)

Ties are rare given CW-DAS produces continuous scores, but the following deterministic chain applies:

```
1. narrative_tier rank (CCL=1 > HCA=2 > WATCH=3 > REDUCE=4)
2. ucf_rank (lower integer = higher conviction)
3. Alphabetical by symbol (deterministic, auditable)
```

### 3.4 Maximum Results

- **Default top-N: 5**
- **Minimum meaningful result: 1** (show at least one alternative if any exists)
- **When fewer than 5 eligible candidates:** show all eligible ones (e.g., 3)
- **Rationale for 5:** Sufficient for operator comparison without overwhelming the panel. Deployment queue typically has 25–32 entries; top 5 represents ≥15% of the queue.

---

## 4. Priority Levels

The `action_priority` field communicates urgency:

| Priority | Condition | Operator Guidance |
|---|---|---|
| `HIGH` | MANDATE_BLOCKED — capital cannot deploy, opportunity exists | "Act now — alternatives available" |
| `MEDIUM` | ETF_GATE_FAILED or WORSENS_OVERWEIGHT — better path available | "Consider alternative — direct route exists" |
| `LOW` | SELL_LAST — policy deferred, not urgent | "Noted — deferred to policy exit phase" |
| `INFORMATIONAL` | DO_NOT_SELL — no action possible | "Monitor only — policy blocks all action" |
| `NONE` | No blocker identified | (no NBA panel rendered) |

---

## 5. Selection Logic vs. Scoring Constraint

The core constraint is: **"NOT alter optimizer scoring, NOT alter CW-DAS"**

The NBA prioritization model satisfies this because:
1. It reads `deployment_score` as a **read-only input** — it does not recompute it
2. It applies eligibility filters, not score adjustments
3. It presents a subset of the existing queue in the same order — no reranking
4. The operator sees the same symbols in the same CW-DAS order they would see in the queue

There is **no shadow scoring** and **no new score computation**. The NBA framework is a filtered window into CW-DAS output.

---

## 6. What NOT to Do

| Anti-Pattern | Reason to Avoid |
|---|---|
| Custom composite score (w1*ESS + w2*ucf + ...) | Introduces shadow scoring inconsistent with CW-DAS |
| Prioritize by headroom as primary | Headroom ≠ conviction; rewards less-deployed positions regardless of quality |
| Prioritize by ESS alone | ESS already captured in CW-DAS signal component — double-counting |
| Show all 32 queue entries | Overwhelming — operator needs scannable top-N, not a full queue reprint |
| Show only 1 candidate | Insufficient for comparison; operator needs to see at minimum 3 |

---

## 7. Summary

| Decision | Choice | Rationale |
|---|---|---|
| Primary ranking | `deployment_score` (CW-DAS rank) | Purpose-built for "next best capital deployment" |
| Secondary ranking | `narrative_tier` → `ucf_rank` → symbol | Deterministic tie-breaks |
| Pre-filter: execution state | Executable only | Policy-blocked alternatives not surfaced as actionable |
| Pre-filter: signal direction | BULLISH only (for ACCUMULATE) | Non-bullish not alternatives to accumulate action |
| Pre-filter: headroom | Exclude 0% headroom | Concentration-saturated positions not viable |
| Maximum results | 5 | Scannable without overwhelming |
| Custom composite | REJECTED | Violates presentation-layer-only constraint |

**Status: Q4 COMPLETE — PRIORITIZATION FRAMEWORK DESIGN CERTIFIED**
