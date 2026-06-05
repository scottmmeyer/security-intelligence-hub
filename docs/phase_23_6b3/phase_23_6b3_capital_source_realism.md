# Phase 23.6B.3 — Capital Source Realism Assessment

**Date:** 2026-06-04  
**Analysis type:** Forensic only — no code changes

---

## 1. Full Source Classification

The 37 capital sources (1 blocked) are assessed against operator realism:

### Tier A: Sources an operator would actually act on

| Symbol | Category | Priority | Proceeds | Rationale | Realistic? |
|--------|----------|---------|---------|-----------|----------|
| KGC | SIGNAL_DETERIORATION | HIGH | $3,672 | BEARISH ESS — clear quality reason | ✅ Yes |
| FIS | SIGNAL_DETERIORATION | HIGH | $1,537 | BEARISH + strategic exit designated | ✅ Yes (but undersized — see Inv. 2) |
| XYZ | SIGNAL_DETERIORATION | HIGH | $887 | BEARISH ESS | ✅ Yes |
| PRIM | SIGNAL_DETERIORATION | MODERATE | $1,274 | BEARISH ESS | ✅ Yes |
| LMAT | TAX_AWARE_EXIT | MODERATE | $7,023 | Unrealized loss ~$7K | ✅ Yes — tax harvest makes sense |
| CIEN | TAX_AWARE_EXIT | MODERATE | $5,347 | Unrealized loss | ✅ Yes |
| HCI | TAX_AWARE_EXIT | MODERATE | $4,514 | Unrealized loss | ✅ Yes |
| AVGO | TAX_AWARE_EXIT | MODERATE | $4,184 | Unrealized loss | ✅ Yes |
| ANIP | TAX_AWARE_EXIT | MODERATE | $3,934 | Unrealized loss | ✅ Yes |
| BNDX | TAX_AWARE_EXIT | MODERATE | $3,607 | Unrealized loss | ✅ Yes |
| PRG | TAX_AWARE_EXIT | MODERATE | $3,453 | Unrealized loss | ✅ Yes |
| CBOE | TAX_AWARE_EXIT | MODERATE | $3,122 | Unrealized loss | ✅ Yes |

### Tier B: Technically valid but operationally uncertain

| Symbol | Category | Proceeds | Concern |
|--------|----------|---------|---------|
| VB | LOW_CONVICTION | $4,436 | Broad market fund — may be intentional diversifier, not a mistake |
| VOO | LOW_CONVICTION | $4,356 | Same — S&P 500 fund in a concentrated-alpha portfolio raises the question of intent |
| VO | LOW_CONVICTION | $2,165 | Mid-cap index fund — same concern |
| FXAIX | LOW_CONVICTION | $1,567 | Fidelity S&P 500 fund — likely legacy / placeholder |
| AMG | LOW_CONVICTION | $1,662 | Small ETF/fund — unclear intent |
| DODFX | OW_REDUCTION | $3,823 | Has SELL_LAST policy, no ESS signal — legitimate OW case but policy-constrained |
| SBS | OW_REDUCTION | $4,533 | BULLISH ESS + overweight — circular (also a buy target, see Inv. 1) |
| CVE | OW_REDUCTION | $3,120 | VERY_BULLISH + overweight — circular (also buy target) |
| TSM | OW_REDUCTION | $2,909 | BULLISH + overweight — circular (also buy target) |
| GTX | OW_REDUCTION | $2,263 | VERY_BULLISH + overweight — circular (also buy target) |
| ASML | OW_REDUCTION | $888 | VERY_BULLISH + overweight — circular (also buy target) |

### Tier C: Sources an operator would almost certainly NOT execute

| Symbol | Category | Proceeds | Why Unrealistic |
|--------|----------|---------|----------------|
| STNG | TAX_AWARE_EXIT | $2,247 | Bucket A (loss) but tiny position — depends on context |
| SMR | TAX_AWARE_EXIT | $1,816 | Very small position |
| FBTC | TAX_AWARE_EXIT | $1,800 | Crypto-adjacent ETF — may be intentional |
| UHS | TAX_AWARE_EXIT | $1,140 | De-minimis |
| FETH | TAX_AWARE_EXIT | $1,025 | Crypto ETF — likely intentional holding |
| YELP | TAX_AWARE_EXIT | $873 | Very small |
| VEA | OW_REDUCTION | $899 | 25% of a $3,594 position in intl fund — de minimis trade |
| NVS | OW_REDUCTION | $221 | $221 proceeds — transaction costs would consume this |
| TTNDY | OW_REDUCTION | $135 | $135 proceeds — clearly not worth executing |
| AGEN | TAX_AWARE_EXIT | $340 | De minimis |
| CMCO | TAX_AWARE_EXIT | $137 | $137 proceeds — not a real trade |
| XRP | TAX_AWARE_EXIT | $92 | $92 — below any reasonable minimum |
| FSOL | TAX_AWARE_EXIT | $81 | $81 — below any reasonable minimum |

---

## 2. Are Low-Conviction Names Being Mixed with Intentional Holdings?

**Yes — significantly.** The capital source list mixes several distinct operator contexts without distinction:

**Context 1: Active exits** — KGC, FIS (operator is actively managing these out)  
**Context 2: Tax harvesting** — LMAT, CIEN, HCI, AVGO, ANIP, BNDX, PRG, CBOE (loss positions worth harvesting)  
**Context 3: Passive/legacy index funds** — VB, VOO, VO, FXAIX, BNDX (may be intentional diversifiers)  
**Context 4: Tiny de minimis positions** — TTNDY ($135), NVS ($221), CMCO ($137), XRP ($92), FSOL ($81) (nuisance holdings, not rotation capital)  
**Context 5: Circular positions** — CVE, GTX, TSM, ASML, SBS (also buy targets)

These are presented uniformly as a flat list. An operator looking at 37 sources has no signal about which are genuinely actionable vs noise.

---

## 3. Does Ranking Align with Portfolio Management Behavior?

**Partially.** The priority sort (URGENT → HIGH → MODERATE → LOW) is reasonable but incomplete:

**What the ranking gets right:**
- TSLA (URGENT, blocked) is prominently at the top
- Signal deterioration (KGC, FIS) at HIGH is appropriate
- Tax harvest candidates (LMAT, CIEN) at MODERATE is appropriate

**What the ranking gets wrong:**
- TSLA's $14,266 blocked source dominates visually even though it cannot execute
- De minimis sources ($81–$221) appear in the same list at LOW priority with no minimum size filter
- Strategic exit context (FIS) is buried under 25% sizing when it should be the first actionable item after TSLA

---

## 4. Candidates That Should Be Demoted, Promoted, or Separated

### Should be PROMOTED:
| Symbol | Current | Should Be | Reason |
|--------|---------|-----------|--------|
| FIS | HIGH, 25% sizing | HIGH, 100% sizing | Operator-designated full exit |

### Should be DEMOTED or SUPPRESSED:
| Symbol | Current | Should Be | Reason |
|--------|---------|-----------|--------|
| XRP | MODERATE $92 | Suppressed | Below minimum execution threshold |
| FSOL | MODERATE $81 | Suppressed | Below minimum execution threshold |
| CMCO | MODERATE $137 | Suppressed | Below minimum execution threshold |
| NVS | LOW $221 | Suppressed | Below minimum execution threshold |
| TTNDY | LOW $135 | Suppressed | Below minimum execution threshold |
| CVE, GTX, TSM, ASML, SBS | LOW | ⚠ Conflict flagged | Also deployment targets |

### Should be SEPARATED into different operator workflows:
| Group | Members | Suggested Workflow |
|-------|---------|-------------------|
| Index/ETF funds (potential legacy) | VB, VOO, VO, FXAIX, BNDX | "Portfolio Cleanup" workflow, not rotation |
| Crypto/thematic | FBTC, FETH, XRP, FSOL | Separate thematic review workflow |
| De minimis (<$500 proceeds) | XRP, FSOL, CMCO, TTNDY, NVS, AGEN | Minimum lot filter |

---

## 5. Summary

| Assessment Dimension | Finding |
|---------------------|---------|
| Sources an operator would actually execute | ~12–15 of 37 (33–40%) |
| Circular sources (sell + buy) | 5 of 37 (13.5%) |
| De minimis sources (<$500 proceeds) | 6 of 37 (16%) |
| Index fund / legacy candidates | 4–5 of 37 (11–14%) |
| Correctly prioritized actionable sources | ✅ LMAT, CIEN, HCI, KGC, FIS |
| Most impactful missing improvement | Minimum proceeds filter ($500+) |
| Second most impactful | Strategic exit full-sizing |
| Third most impactful | Circular conflict detection |
