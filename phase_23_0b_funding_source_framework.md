# Phase 23.0B — Q5: Funding Source Intelligence Framework

**Design Date:** 2026-06-03  
**Analysis Run:** PAR-20260603-AC8FD5F0  
**Question:** Should the framework identify holdings that can fund higher-conviction purchases?

---

## The Funding Source Problem

The deployment queue identifies high-conviction BUY candidates:

| Symbol | Composite | Tier |
|---|---|---|
| ARW | 4.889 | HIGH_CONVICTION_ANCHOR |
| CVE | 4.833 | CORE_CONVICTION_LEADER |
| SNX | 4.778 | HIGH_CONVICTION_ANCHOR |
| ATLC | 4.778 | HIGH_CONVICTION_ANCHOR |
| MU | 4.722 | CORE_CONVICTION_LEADER |
| PSX | 4.722 | HIGH_CONVICTION_ANCHOR |
| PRG | 4.722 | TACTICAL_GROWTH_CANDIDATE |
| STNG | 4.714 | HIGH_CONVICTION_ANCHOR |
| CBOE | 4.667 | HIGH_CONVICTION_ANCHOR |
| ASML | 4.667 | HIGH_CONVICTION_ANCHOR |

If available cash ($41,279 in SPAXX) is allocated and the operator still wants to deploy into new positions, the question becomes: **"What do I sell to fund this?"** 

The current system has no answer. The Tax-Aware Actions panel shows only bearish-signal holdings. The deployment queue shows buy targets. There is no mechanism that connects "what to sell" with "what to buy."

---

## Funding Source Framework Design

### Core Principle

A holding becomes a funding source candidate when:

> **Something better exists** (deployment candidate with higher conviction)  
> **AND the current holding has lower strategic value** relative to the intended purchase  
> **AND replacing it advances portfolio quality**

This is a conviction-trade, not a distressed-exit. Funding source candidates are not necessarily bad holdings — they are holdings that yield to better opportunities.

---

## Ranking Factors for Funding Source Priority

### Factor 1: Conviction Score (Primary)
Holdings with lower composite scores are higher-priority funding sources. Low conviction = the holding is not earning its allocation.

**Thresholds:**
- Composite < 3.0: Weak anchor → high funding source priority
- Composite 3.0–4.0: Moderate anchor → moderate priority
- Composite > 4.0: Strong anchor → low/no funding priority (these are the targets you're buying more of)
- UNKNOWN signal (no composite score): Can be a funding source based on other factors

### Factor 2: Replay Support
Holdings with poor replay alignment (`replay_supported = false`) have not demonstrated historical replay performance. They are lower-conviction from a replay-validated return standpoint.

### Factor 3: Signal Quality
- NEUTRAL/UNKNOWN: Not constructive → funding priority elevated
- BEARISH: Already Category 1 exit candidate — funding source secondary classification
- BULLISH: Should not be used as funding source unless overweight (allocation conflict)

### Factor 4: Allocation Context
- Holding in OVERWEIGHT node: Reduction is already called for → funding source designation aligns with rebalancing
- Holding in UNDERWEIGHT node: Do NOT use as funding source — would worsen allocation underweight
- Holding in balanced/neutral node: Depends on other factors

### Factor 5: Tax Impact
- Unrealized loss: Best funding source (harvest loss + fund purchase = double benefit)
- Unrealized gain within capacity window: Good funding source (gain absorbed by loss carryforward)
- Unrealized gain beyond capacity: Tax cost offsets some of the funding advantage — rank lower
- Near LT threshold: Consider Cat 7 (deferral) before using as funding source

---

## Current Run: Funding Source Candidates

### Priority 1: FIS — Best Available Funding Source
| Factor | Value | Assessment |
|---|---|---|
| Signal | NEUTRAL | Not constructive |
| Conviction | No high composite score | No anchor rationale |
| Replay | Not supported | No replay validation |
| Allocation | No underweight dependency | Free to exit |
| Tax | −$14,344 loss | Best possible — harvest loss AND free capital |
| Strategic | Former employer stock | Category 2 exit aligned |

**FIS is the optimal funding source for new purchases:** exiting FIS realizes a $14,344 loss (which improves gain capacity), frees $23,287 of capital, and has no strategic cost because FIS is not a portfolio anchor.

### Priority 2: DODFX — Allocation-Aligned Funding Source
| Factor | Value | Assessment |
|---|---|---|
| Signal | UNKNOWN | No ESS signal for mutual fund |
| Conviction | No composite | No individual anchor |
| Replay | No replay data | No validation |
| Allocation | INTERNATIONAL overweight +6.63% | Reduction called for |
| Tax | +$2,751 gain | Within $24,730 capacity window |
| Strategic | Broad international exposure, replaceable | No unique value |

**DODFX is the preferred international overweight reduction AND a good funding source.** Selling DODFX reduces the international overweight AND generates $15,310 of capital with a modest tax-shielded gain.

### Priority 3: VXUS, VEA — Secondary International Reduction
Same logic as DODFX, smaller positions. Selling VXUS ($3,976) and VEA ($3,611) together contributes ~$7,587 of capital while both reducing international overweight and realizing gains within capacity.

### Priority 4: VOO / FXAIX — Capital Efficiency Play
| Factor | Value | Assessment |
|---|---|---|
| Signal | UNKNOWN | No ESS signal for index funds |
| Conviction | No composite | Passive vehicle |
| Allocation | MEGA tier (LOW overweight) | Mild alignment |
| Tax | +$3,765 / +$1,302 | Both within capacity |
| Strategic | Passive broad exposure | Can be replaced by high-conviction names |

**Case for using VOO/FXAIX as funding sources:** A dollar in VOO buys passive S&P 500 exposure. A dollar in ARW, SNX, or ATLC buys high-conviction active selection with conviction scores of 4.778–4.889. If the operator is confident in the high-conviction names, replacing passive index exposure with active positions increases expected alpha.

**Case against:** VOO/FXAIX are diversification vehicles. Selling them concentrates the portfolio further into active names, increasing idiosyncratic risk. The operator must decide whether the conviction trade-off is warranted.

---

## Holdings NOT Suitable as Funding Sources

These holdings should be excluded from funding source consideration:

| Symbol | Composite | Tier | Reason |
|---|---|---|---|
| ARW | 4.889 | HIGH_CONVICTION_ANCHOR | Top conviction — buy more, not sell |
| CVE | 4.833 | CORE_CONVICTION_LEADER | Top conviction — retain |
| SNX | 4.778 | HIGH_CONVICTION_ANCHOR | Top conviction — retain |
| ATLC | 4.778 | HIGH_CONVICTION_ANCHOR | Top conviction — retain |
| MU | 4.722 | CORE_CONVICTION_LEADER | Top conviction — retain |
| PSX | 4.722 | HIGH_CONVICTION_ANCHOR | Top conviction — retain |
| ASML | 4.667 | HIGH_CONVICTION_ANCHOR | International equity — retain, high conviction |
| TSM | 4.444 | CORE_CONVICTION_LEADER | International equity — retain |
| NVDA | BULLISH | HYPER_MEGA | Strong signal — not a funding source |

**Funding source selection should specifically exclude conviction anchors.** This is a critical guardrail: the system should surface which holdings can be replaced, not which ones should be protected.

---

## Funding Source Display Format

When the operator triggers "Fund Purchase of [SYMBOL]," the system should show:

```
FUNDING SOURCE CANDIDATES for [SYMBOL] purchase of $[amount]
───────────────────────────────────────────────────────────
Priority  Symbol   Current MV   Available   Signal    Tax Impact       Why
1         FIS      $23,287      $23,287     NEUTRAL   −$14,344 loss    Strategic exit + loss harvest
2         DODFX    $15,310      $15,310     UNKNOWN   +$2,751 gain     Overweight reduction (INTERNATIONAL +6.6%)
3         VXUS     $3,976       $3,976      UNKNOWN   +$869 gain       Overweight reduction (INTERNATIONAL)
4         VEA      $3,611       $3,611      UNKNOWN   +$596 gain       Overweight reduction (INTERNATIONAL)
5         VOO      $17,453      partial     UNKNOWN   +$3,765 gain     Index fund → active replacement
```

---

## Answer: Should Funding Source Intelligence Be Added?

**Yes.** This is a gap that directly impacts how the operator acts on deployment recommendations. The deployment queue identifies *what* to buy. Without funding source intelligence, the operator must manually determine *what to sell* to fund the purchase.

Funding source intelligence closes the loop between:
- **What to buy** (deployment queue / conviction cards)
- **What to sell** (funding source candidates)

The framework should surface Category 4 (Funding Source) candidates whenever:
1. The deployment queue has active buy candidates beyond available cash, OR
2. The operator explicitly requests "how do I fund [symbol]?"

**No new analytical computation is needed.** Composite scores, signal directions, allocation nodes, and overweight flags are already computed. The funding source ranking is a straightforward sort over existing data fields.

**Guardrail requirement:** High-conviction holdings (conviction tier = HIGH_CONVICTION_ANCHOR, CORE_CONVICTION_LEADER) must be excluded from automatic funding source suggestions. The system should never suggest selling ARW to buy ARW.
