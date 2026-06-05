# Phase 23.0B — Q4: Overweight Rebalancing Pipeline Design

**Design Date:** 2026-06-03  
**Analysis Run:** PAR-20260603-AC8FD5F0  
**Question:** Should overweight allocations automatically generate sell candidates?

---

## Current State: Overweight Nodes Generate Recommendations but No Action Candidates

The `recommendations.json` for run PAR-20260603-AC8FD5F0 contains three `REDUCE_OVERWEIGHT` recommendations:

1. **EQUITIES.INTERNATIONAL** — actual 18.63% vs target 12.0%, drift +6.63% (MODERATE)
2. **EQUITIES.INTERNATIONAL.LARGE** — actual 8.10% vs target 4.0%, drift +4.10% (MODERATE)
3. **EQUITIES.US.MEGA.HYPER_MEGA** — actual 9.88% vs target 6.3%, drift +3.58% (MODERATE)

These recommendations are narrative guidance. They do NOT currently surface any specific holding as a sell or reduce candidate in the Tax-Aware Actions panel.

---

## Why Overweight Allocations Should Generate Sell Candidates

Portfolio construction analysis has already done the analytical work: it has identified which nodes are overweight, measured the magnitude, and classified severity. The missing step is translating node-level analysis into holding-level action candidates.

**The operator cannot act on "reduce EQUITIES.INTERNATIONAL."** They can only act on specific holdings. The pipeline from overweight node → constituent holdings → prioritized action candidates is the missing link.

**Key principle:** Allocation drift generates a Category 3 candidate regardless of signal quality. A holding in an overweight node is a potential reduction lever — even if the holding itself has BULLISH signal, UNKNOWN signal, or no signal at all.

---

## Overweight Node → Constituent Holding Mapping

### Node: EQUITIES.INTERNATIONAL (MODERATE, +6.63%)

**Reduction target:** 6.63 percentage points = approximately $32,055 at $483,800 portfolio total  
**Practical reduction: reduce to target 12%** → eliminate ~$32,055 from international exposure

| Symbol | MV | Cost | Unrealized | % of Port | Signal | Reduction Leverage |
|---|---|---|---|---|---|---|
| DODFX | $15,310 | $12,558 | +$2,751 | 3.16% | UNKNOWN | High — largest international position, mutual fund, easily reduced |
| VXUS | $3,976 | $3,107 | +$869 | 0.82% | UNKNOWN | Moderate — ETF, easily sold |
| VEA | $3,611 | $3,015 | +$596 | 0.75% | UNKNOWN | Moderate — ETF, easily sold |
| FIGFX | $1,219 | $1,068 | +$151 | 0.25% | UNKNOWN | Low — small position, lower impact |
| ASML | ~$4,800 | — | — | ~1.0% | BULLISH | Preserve — HIGH conviction anchor |
| TSM | ~$2,500 | — | — | ~0.5% | BULLISH | Preserve — conviction leader |
| TTNDY, NVS, SBS, CVE (partial int'l) | Various | — | — | ~4.0% | BULLISH | Preserve — high-conviction |

**Recommended reduction candidates from EQUITIES.INTERNATIONAL (Cat 3):**
- **DODFX** (priority: HIGH) — largest position, UNKNOWN signal, mutual fund, +$2,751 gain within capacity
- **VXUS** (priority: MODERATE) — ETF, UNKNOWN signal, +$869 gain
- **VEA** (priority: MODERATE) — ETF, UNKNOWN signal, +$596 gain
- **FIGFX** (priority: LOW) — small position, limited drift reduction leverage

**Do NOT reduce:** ASML, TSM, CVE, NVS, TTNDY — individual high-conviction equities with BULLISH signals; international overweight should be corrected via funds/ETFs, not individual names.

---

### Node: EQUITIES.INTERNATIONAL.LARGE (MODERATE, +4.10%)

**Overlaps with EQUITIES.INTERNATIONAL above.** DODFX, VXUS, VEA are the primary large-cap international vehicles. This sub-node overweight is largely addressable by the same actions as the parent node.

**Priority inheritance:** Same as EQUITIES.INTERNATIONAL — MODERATE severity drives MODERATE priority for constituent candidates. The sub-node specificity confirms that the overweight is concentrated in large-cap international vehicles, not small/mid.

---

### Node: EQUITIES.US.MEGA.HYPER_MEGA (MODERATE, +3.58%)

**Reduction target:** 3.58 percentage points = approximately $17,320

| Symbol | MV | Cost | Unrealized | Signal | Notes |
|---|---|---|---|---|---|
| TSLA | $14,330 | $10,699 | +$3,631 | BEARISH | ALREADY Cat 1 candidate; dual classification (Cat 1 + Cat 3) |
| NVDA | ~$13,000 | — | — | BULLISH | HIGH conviction — do not reduce to correct allocation |

**Analysis:** The HYPER_MEGA overweight is primarily driven by TSLA and NVDA combined. NVDA has BULLISH signal and is a high-conviction hold. TSLA has BEARISH signal and is already a Cat 1 candidate. Reducing TSLA addresses both the signal deterioration AND the allocation overweight simultaneously — this is the preferred path.

**Recommended reduction candidates from EQUITIES.US.MEGA.HYPER_MEGA (Cat 3):**
- **TSLA** (priority: HIGH) — bearish signal AND allocation overweight — dual Cat 1/Cat 3 candidate

**Do NOT reduce:** NVDA — high-conviction bullish signal; forcing NVDA reduction to correct HYPER_MEGA overweight would be counterproductive to portfolio quality goals.

---

## Priority Algorithm for Category 3 Candidates

When building the Category 3 candidate list from overweight nodes, rank by:

1. **Node severity** (MODERATE = priority MODERATE, LOW = priority LOW)
2. **Holding's contribution to the drift** (larger % of portfolio = higher leverage)
3. **Signal quality** (UNKNOWN/NEUTRAL = preferred reduction candidates; BULLISH = reduce only if no better option)
4. **Tax context** (loss positions preferred; gains within capacity next; unshielded short-term gains last)

**Applied to current run:**

| Rank | Symbol | Category | Node | Drift | Reason |
|---|---|---|---|---|---|
| 1 | TSLA | Cat 1 + Cat 3 | HYPER_MEGA | +3.58% | BEARISH signal + overweight — dual priority |
| 2 | FIS | Cat 2 + Cat 5 | N/A | N/A | Strategic exit + loss harvest — not allocation-driven |
| 3 | DODFX | Cat 3 | INTERNATIONAL | +6.63% | Largest UNKNOWN-signal international position |
| 4 | VXUS | Cat 3 | INTERNATIONAL | +6.63% | ETF, UNKNOWN signal |
| 5 | VEA | Cat 3 | INTERNATIONAL | +6.63% | ETF, UNKNOWN signal |
| 6 | FIGFX | Cat 3 | INTERNATIONAL | +6.63% | Small position, lower leverage |

---

## Lower-Severity Overweight Nodes

Three additional overweight nodes exist with LOW severity:

| Node | Drift | Severity | Notes |
|---|---|---|---|
| EQUITIES.US.SMALL | +3.19% | LOW | PRIM is small-cap; BEARISH signal → already Cat 1. Lower urgency for Cat 3 only action |
| EQUITIES.US.MICRO | +2.17% | LOW | Micro-cap holdings; LOW severity, informational only |
| EQUITIES.US.MEGA.ULTRA_MEGA | +1.72% | LOW | VOO/FXAIX area; LOW severity. Possible Cat 3 but low urgency |

LOW severity overweight nodes should appear in the UI as informational — visible but not elevated to action priority.

---

## Answer: Should Overweight Allocations Generate Sell Candidates?

**Yes, automatically for MODERATE and HIGH severity nodes.**

The analytical work is already done in `recommendations.json`. The gap is the translation pipeline from node-level recommendation to holding-level action candidate. That pipeline should be:

```
REDUCE_OVERWEIGHT recommendation 
  → identify constituent holdings in overweight node
  → exclude high-conviction BULLISH holdings with no allocation redundancy
  → rank remaining holdings by drift contribution + signal quality + tax context
  → surface as Category 3 candidates in action pipeline
```

LOW severity nodes can be surfaced as advisory (informational priority) without blocking the higher-severity items.

**No new analytical work is needed.** The overweight node identification, severity classification, and constituent membership are already computed. Phase 23.0B (and its implementation phase) needs only to read from `recommendations.json` and map node names to holding symbols using the existing allocation data.
