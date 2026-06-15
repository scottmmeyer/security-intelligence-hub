# AI-006 Zacks Governance Assessment

**Date:** 2026-06-15

---

## Q10: Zacks Minimum Threshold Policy Options

### Current Queue State (Zacks scores)

| Symbol | Rank | ESS | Zacks | Danelfin | Composite |
|--------|------|-----|-------|---------|-----------|
| VRT | #1 | VERY_BULLISH | 4.0 | 3.5 | 4.5556 |
| ATLC | #2 | VERY_BULLISH | 4.0 | 3.0 | 4.5000 |
| DELL | #3 | VERY_BULLISH | 5.0 | 2.5 | 4.7222 |
| LRCX | #4 | VERY_BULLISH | 4.0 | 3.0 | 4.5000 |
| **PCB** | **#5** | **VERY_BULLISH** | **3.0** | **4.0** | **4.3333** |
| CAH | #6 | VERY_BULLISH | 4.0 | 2.5 | 4.4444 |
| SANM | #7 | BULLISH | 4.0 | 4.0 | 4.0000 |
| **MTZ** | **#8** | **BULLISH** | **3.0** | **4.5** | **3.7778** |
| CRS | #9 | BULLISH | 4.0 | 4.0 | 4.0000 |
| NUE | #10 | BULLISH | 5.0 | 3.5 | 4.2222 |

### Option A: Zacks >= 3 (exclude BEARISH Zacks only)

**Excluded:** NONE (all current candidates have Zacks >= 3.0)  
**Passed:** All 10  
**Effect:** No ranking change. This is de facto current behavior.

### Option B: Zacks >= 4 (exclude NEUTRAL Zacks)

**Excluded:** PCB (#5, Zacks=3.0), MTZ (#8, Zacks=3.0)  
**Passed:** VRT, ATLC, DELL, LRCX, CAH, SANM, CRS, NUE (8 candidates)  
**Revised ranking:** Unchanged for passing symbols; PCB and MTZ removed.

This is the most meaningful governance gate. PCB and MTZ both have VERY_BULLISH/BULLISH ESS but only NEUTRAL Zacks — they are ESS-momentum plays without Zacks confirmation. Danelfin is strong for both (PCB=4.0, MTZ=4.5) but Danelfin carries only 10% weight.

### Option C: Zacks >= 5 (only STRONG BUY Zacks)

**Excluded:** VRT, ATLC, LRCX, PCB, CAH, SANM, MTZ, CRS (8 excluded!)  
**Passed:** DELL (#3, Zacks=5.0), NUE (#10, Zacks=5.0) — only 2 remain  
**Effect:** Extremely restrictive. Would effectively block most deployment activity. Not recommended.

### Recommendation

**Option B (Zacks >= 4) is the most defensible governance gate** if a Zacks minimum is desired. It would exclude:
- PCB (#5): VERY_BULLISH ESS, Zacks=3.0 (NEUTRAL), Danelfin=4.0. PCB is ESS-driven with no Zacks confirmation. Excluding PCB is reasonable.
- MTZ (#8): BULLISH ESS, Zacks=3.0 (NEUTRAL), Danelfin=4.5. MTZ has strong Danelfin but weak Zacks. Excluding MTZ is debatable.

**Option A requires no implementation and has no effect on current data.** Only useful as a floor against BEARISH Zacks.

---

## Q11: ESS Bullish but Zacks Neutral or Worse

**YES — two current deployment candidates qualify:**

| Symbol | ESS | Zacks | Danelfin | Rank | Explanation |
|--------|-----|-------|---------|------|------------|
| **PCB** | VERY_BULLISH | **3.0** (NEUTRAL) | 4.0 | #5 | High ESS conviction overwhelms neutral Zacks |
| **MTZ** | BULLISH | **3.0** (NEUTRAL) | 4.5 | #8 | Danelfin and sizing lift score despite weak Zacks |

### Is This Intended Design or Governance Gap?

**Intended design** — the formula deliberately allows ESS to anchor conviction. The reasoning is documented in the `_score_from_inputs` function comments:

> "Missing signals... are excluded from both numerator and denominator rather than defaulting to 0.0, which would unfairly penalise securities"

ESS carries 55% weight. A VERY_BULLISH ESS produces a minimum composite of:
- Without Zacks: `5.0 × 0.55 / 0.55 = 5.0`
- With Zacks NEUTRAL (3.0): `(5.0×0.55 + 3.0×0.25) / 0.80 = 4.3125`

This is intentional: the system is designed to allow deployment of high-conviction ESS names even when Zacks is neutral, on the premise that StarMine ESS (as the primary institutional research signal) is the most reliable indicator at 55% weight.

### Governance Judgment

PCB (#5) and MTZ (#8) are ESS-only conviction plays. For a CONCENTRATED_ALPHA mandate, this is appropriate — the mandate accepts concentrated positions on high-conviction names. However, operators should be aware that these two names lack Zacks confirmation:

- **PCB**: Rank #5, VERY_BULLISH ESS, Zacks=3.0 → deploy with awareness of Zacks NEUTRAL
- **MTZ**: Rank #8, BULLISH ESS, Zacks=3.0 → operator review recommended; apply conservative sizing
