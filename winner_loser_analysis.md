# Winner / Loser Analysis — PSS Integration
**Phase 7.5T — Pure Signal Capital Allocation Audit**
**Run:** PAR-20260601-9CFD7C63 | **Date:** June 1, 2026

---

## Overview

This report identifies which symbols gain or lose capital as Pure Signal Score (PSS) weight increases from 0% (Model A) to 50% (Model D). All delta amounts are computed against the Model A (baseline CW-DAS) allocation.

Total capital pool: $33,141.36

---

## Biggest Winners — Model D vs Model A (Largest Allocation Gain)

Symbols receiving significantly more capital as signal weight increases:

| Rank | Symbol | PSR | CW-DAS Rank | Model A Alloc | Model D Alloc | Delta $ | Delta Rank |
|------|--------|-----|------------|--------------|--------------|---------|-----------|
| 1 | **ATLC** | 3 | 4 | $1,437.27 | $8,810.94 | **+$7,373.67** | +3 positions |
| 2 | **AVT** | 2 | 7 | $1,070.79 | $2,046.75 | **+$975.96** | +5 positions |
| 3 | **PCB** | 1 | 12 | $805.66 | $1,659.80 | **+$854.14** | +9 positions |
| 4 | **CAH** | 4 | 9 | $939.22 | $1,437.27 | **+$498.05** | +5 positions |
| 5 | **ALNT** | 6 | 16 | $680.04 | $939.22 | **+$259.18** | +7 positions |
| 6 | **MTZ** | 7 | 17 | $658.99 | $884.12 | **+$225.13** | +7 positions |
| 7 | **CRS** | 9 | 18 | $639.34 | $805.66 | **+$166.32** | +6 positions |
| 8 | **FSLR** | 10 | 21 | $587.15 | $702.74 | **+$115.59** | +6 positions |
| 9 | **CBOE** | 5 | 6 | $1,168.63 | $1,283.89 | **+$115.26** | +1 position |
| 10 | **CIEN** | 8 | 13 | $768.26 | $997.50 | **+$229.24** | +5 positions |
| 11 | **HALO** | 13 | 23 | $558.28 | $658.99 | **+$100.71** | +6 positions |

**Winner profile:** All 11 winners have PSR ≤ 13 (strong signal quality). All hold STRONG (261-day) replay evidence except ARW (PSR=11, 4-day replay). Winners are distributed across multiple market cap tiers (micro, small, mid) and multiple sectors.

---

## Biggest Losers — Model D vs Model A (Largest Allocation Loss)

Symbols receiving significantly less capital as signal weight increases:

| Rank | Symbol | PSR | CW-DAS Rank | Model A Alloc | Model D Alloc | Delta $ | Delta Rank |
|------|--------|-----|------------|--------------|--------------|---------|-----------|
| 1 | **VRT** | 14 | 1 | $8,810.94 | $1,070.79 | **-$7,740.15** | -6 positions |
| 2 | **SNX** | 18 | 3 | $1,659.80 | $841.77 | **-$818.03** | -8 positions |
| 3 | **PSX** | 27 | 5 | $1,283.89 | $768.26 | **-$515.63** | -8 positions |
| 4 | **ARW** | 11 | 2 | $2,046.75 | $1,168.63 | **-$878.12** | -4 positions |
| 5 | **SANM** | 35 | 11 | $841.77 | $532.65 | **-$309.12** | -14 positions |
| 6 | **LRCX** | 19 | 8 | $997.50 | $736.53 | **-$260.97** | -6 positions |
| 7 | **DELL** | 29 | 10 | $884.12 | $620.59 | **-$263.53** | -9 positions |
| 8 | **NUE** | 21 | 14 | $736.53 | $639.34 | **-$97.19** | -4 positions |
| 9 | **GFF** | 22 | 15 | $702.74 | $587.15 | **-$115.59** | -6 positions |

**Loser profile:** Most losers have PSR > 14 (weak signal quality). All 7 high-loss symbols hold THIN (4-day) replay evidence. ARW is the notable exception: PSR=11 (moderate signal quality) with 4-day replay — its losses are replay-depth driven, not signal-quality driven.

---

## Analysis by Mechanism

### Group 1: Signal-quality losers (PSR > 20, THIN replay)
SNX (PSR=18), PSX (PSR=27), SANM (PSR=35), LRCX (PSR=19), DELL (PSR=29): These stocks are currently elevated by framework mechanics (HCA conviction tier, flat replay bonus) despite having below-average pure signal quality. PSS integration correctly identifies them as marginal.

### Group 2: Path-dependency loser (CCL tier)
VRT (PSR=14): VRT has a genuine but not top-tier signal profile. Its loss is overwhelmingly driven by the CCL tier effect: when PSS weight reaches 40%+, the 24-point PSS gap between ATLC (norm_pss=91.24) and VRT (norm_pss=66.99) exceeds VRT's CW-DAS floor advantage. VRT's allocation loss ($-7,740) represents the unmixing of the CCL capital concentration.

### Group 3: Replay-depth losers with decent signals (THIN, PSR ~11)
ARW (PSR=11, 4-day): ARW has moderate signal quality (above median), but its thin replay evidence means it slightly under-performs in a PSS framework. Its loss is much smaller than the signal-quality losers.

---

## Trajectory by Model

### ATLC (biggest winner)

| Model | Rank | Alloc | Change |
|-------|------|-------|--------|
| A | 4 | $1,437.27 | baseline |
| B | 2 | $2,046.75 | +$609 |
| C | **1** | **$8,810.94** | +$7,374 |
| D | **1** | **$8,810.94** | unchanged |

ATLC's ascent is non-linear: a modest +2 in Model B, then a step-change to rank 1 in Model C. It holds rank 1 in both Models C and D, suggesting stability once PSS weight clears ~30%.

### PCB (third-largest winner)

| Model | Rank | Alloc | Change |
|-------|------|-------|--------|
| A | 12 | $805.66 | baseline |
| B | 7 | $1,070.79 | +$265 |
| C | 3 | $1,659.80 | +$854 |
| D | 3 | $1,659.80 | unchanged |

PCB (highest pure signal score in the universe) makes consistent gains across all models. Each 20% increment in PSS weight moves it up by ~4–5 ranks. It reaches rank 3 in both C and D — it appears to stabilize there because it cannot overcome ATLC's also-strong blend score.

### VRT (largest loser)

| Model | Rank | Alloc | Change |
|-------|------|-------|--------|
| A | 1 | $8,810.94 | baseline |
| B | 1 | $8,810.94 | unchanged |
| C | 6 | $1,168.63 | -$7,642 |
| D | 7 | $1,070.79 | -$7,740 |

VRT's allocation is binary: it either holds rank 1 (and its full CCL-level capital of $8,810) or it doesn't. The cliff between Model B and C is dramatic. There is no smooth degradation — VRT loses nearly $7,700 of its deployment at the B→C threshold.

### SANM (most-inflated stock, model-D trajectory)

| Model | Rank | Alloc | Change |
|-------|------|-------|--------|
| A | 11 | $841.77 | baseline |
| B | 14 | $736.53 | -$105 |
| C | 21 | $587.15 | -$255 |
| D | 25 | $532.65 | -$309 |

SANM consistently loses ground at every PSS increment. Its PSR=35 (lowest signal quality among top-15 deployed stocks) makes it the most penalized stock in the universe as signal quality gains weight. In Model D, it receives only $533 — less than 63% of its Model A allocation.

---

## Concentration Change

### Capital Concentration (Herfindahl-Hirschman Index proxy)

Each model deploys $33,141 across up to 31 positions. The distribution shape:

| Model | Top-1 share | Top-3 share | Top-5 share | HHI-proxy (sum of squared alloc%) |
|-------|------------|------------|------------|----------------------------------|
| A | 26.6% | 51.4% | 46.0%* | 8.73% |
| B | 26.6% | 38.2%† | 46.0%* | 8.27% |
| C | 26.6% | 36.5%‡ | 46.0%* | 8.19% |
| D | 26.6% | 36.5%‡ | 46.0%* | 8.19% |

\* Top-5 dollar total is invariant (same 5 allocation tiers redistributed)
† Model B top 3: VRT+ATLC+ARW = 8810+2047+1660 = $12,517
‡ Models C/D top 3: ATLC+AVT+PCB = 8810+2047+1660 = $12,517

**Concentration at the top-3 level:** Models C and D are marginally less concentrated than Model A because the top-3 is split across three HCA stocks rather than one CCL stock and two HCA stocks. The $8,810 CCL bucket still exists; it just goes to ATLC instead of VRT.

**Effective diversification impact:** Modest. The allocation curve was designed for a CCL structure (one super-dominant rank-1 slot). PSS integration doesn't change the curve, only which symbol fills which slot.

---

## Replay Evidence Quality Change

As winners tend to have STRONG replay evidence and losers tend to have THIN evidence:

| Model | Avg replay days (top-10 deployed) | THIN-replay $ | STRONG-replay $ |
|-------|----------------------------------|--------------|----------------|
| A | 133 days | $19,531 (58.9%) | $13,610 (41.1%) |
| B | 199 days | $14,116 (42.6%) | $19,025 (57.4%) |
| C | 256 days | $5,305 (16.0%) | $27,836 (84.0%) |
| D | 257 days | $5,407 (16.3%) | $27,734 (83.7%) |

PSS integration dramatically improves replay evidence quality across deployed capital. Model C nearly eliminates thin-replay capital from the top-10 deployment allocation. Model B is roughly balanced.
