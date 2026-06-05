# Phase 23.6B.1 — Deployment Target Analysis

**Date:** 2026-06-04  
**PAR Run:** PAR-20260604-A47BD0AF / B01C0C82  

---

## Q3: CRA Capital Pool — Full Reconciliation

### Gross Pool (38 non-blocked, non-deferred sources)

| Symbol | Category | Proceeds | Tax | Priority | Notes |
|--------|----------|----------|-----|----------|-------|
| KGC | SIGNAL_DETERIORATION | $3,671.68 | C | HIGH | |
| FIS | SIGNAL_DETERIORATION | $1,536.62 | A | HIGH | Partial position, 50% sizing |
| XYZ | SIGNAL_DETERIORATION | $886.75 | A | HIGH | |
| **SPAXX** | **LOW_CONVICTION** | **$11,012.35** | None | MODERATE | ⚠ DEFECT: cash equivalent |
| LMAT | TAX_AWARE_EXIT | $7,023.37 | A | MODERATE | |
| CIEN | TAX_AWARE_EXIT | $5,346.60 | A | MODERATE | |
| HCI | TAX_AWARE_EXIT | $4,514.40 | A | MODERATE | |
| VB | LOW_CONVICTION | $4,435.80 | C | MODERATE | |
| VOO | LOW_CONVICTION | $4,355.75 | C | MODERATE | |
| AVGO | TAX_AWARE_EXIT | $4,184.05 | A | MODERATE | |
| ANIP | TAX_AWARE_EXIT | $3,934.00 | A | MODERATE | |
| BNDX | TAX_AWARE_EXIT | $3,606.72 | A | MODERATE | |
| PRG | TAX_AWARE_EXIT | $3,453.00 | A | MODERATE | |
| CBOE | TAX_AWARE_EXIT | $3,122.46 | A | MODERATE | |
| STNG | TAX_AWARE_EXIT | $2,247.00 | A | MODERATE | |
| SMR | TAX_AWARE_EXIT | $1,815.75 | A | MODERATE | |
| FBTC | TAX_AWARE_EXIT | $1,799.51 | A | MODERATE | |
| PRIM | SIGNAL_DETERIORATION | $1,274.30 | C | MODERATE | |
| UHS | TAX_AWARE_EXIT | $1,140.08 | A | MODERATE | |
| FETH | TAX_AWARE_EXIT | $1,024.56 | A | MODERATE | |
| YELP | TAX_AWARE_EXIT | $873.20 | A | MODERATE | |
| AGEN | TAX_AWARE_EXIT | $339.50 | A | MODERATE | |
| CMCO | TAX_AWARE_EXIT | $137.10 | A | MODERATE | |
| XRP | TAX_AWARE_EXIT | $91.87 | A | MODERATE | |
| FSOL | TAX_AWARE_EXIT | $81.45 | A | MODERATE | |
| SBS | OVERWEIGHT_REDUCTION | $4,533.28 | C | LOW | |
| DODFX | OVERWEIGHT_REDUCTION | $3,823.36 | C | LOW | SELL_LAST policy visible |
| CVE | OVERWEIGHT_REDUCTION | $3,119.85 | C | LOW | |
| TSM | OVERWEIGHT_REDUCTION | $2,908.99 | C | LOW | |
| **PENDING ACTIVITY** | **LOW_CONVICTION** | **$2,551.15** | None | LOW | ⚠ DEFECT: settlement row |
| GTX | OVERWEIGHT_REDUCTION | $2,263.20 | C | LOW | |
| VO | LOW_CONVICTION | $2,164.99 | C | LOW | |
| AMG | LOW_CONVICTION | $1,662.05 | C | LOW | |
| FXAIX | LOW_CONVICTION | $1,567.30 | C | LOW | |
| VEA | OVERWEIGHT_REDUCTION | $898.57 | C | LOW | |
| ASML | OVERWEIGHT_REDUCTION | $887.84 | C | LOW | |
| NVS | OVERWEIGHT_REDUCTION | $221.46 | C | LOW | |
| TTNDY | OVERWEIGHT_REDUCTION | $134.70 | C | LOW | |
| **TOTAL** | | **$98,644.61** | | | |

### Verified Pool Math

```
Pool sum = $98,644.61  ✓  (matches CRA API total_capital_pool exactly)
```

### Known Defects in Pool Composition

**Defect 1: SPAXX ($11,012.35)**
- SPAXX is `is_cash_equivalent=True`, `operational_state=CASH_EQUIVALENT`
- Should be excluded from all sell candidate categories
- The capital_source_builder does not check `is_cash_equivalent` before categorizing
- **Impact:** Pool is overstated by $11,012 (11.2% of pool)

**Defect 2: PENDING ACTIVITY ($2,551.15)**
- `operational_state=ACTIVE_POSITION` with positive market value ($10,204.59)
- This is a settlement placeholder row, not a tradeable position
- The capital_source_builder treats it as a real holding and generates a sell candidate
- **Impact:** Pool is overstated by $2,551 (2.6% of pool)

**Corrected pool (excluding defects):** $98,644 − $11,012 − $2,551 = **$85,081**

---

## Q4: Target Allocation Forensic

### Inputs to Allocation Algorithm

```
total_pool = $98,644.61
portfolio_mv = $479,086.31
proportional_cap = total_pool × 50% = $49,322.31
minimum_lot_size = $500
```

### Allocation Trace — Step by Step

**Candidate #1: DELL**
```
headroom_pct = 74.8%
headroom_usd = 74.8% × $479,086 = $358,357
suggested = min($358,357, $98,644, $49,322) = $49,322
remaining = $98,644 − $49,322 = $49,322
```

**Candidate #2: VRT**
```
headroom_pct = 30.0%
headroom_usd = 30.0% × $479,086 = $143,726
suggested = min($143,726, $49,322, $49,322) = $49,322
remaining = $49,322 − $49,322 = $0.00
```

**All subsequent candidates:** `remaining ($0) < minimum_lot_size ($500)` → allocation stops

### Why Only 2 Targets

The 50% proportional cap guarantees that **no pool, regardless of size, produces more than 2 allocations** when the top-2 candidates each have headroom > 50% of the pool. With DELL and VRT both having massive headroom, the algorithm terminates at exactly 2 allocations every time.

This is a structural consequence of the proportional cap constant, not a data problem or queue problem.

---

## Q5: Why ARW, PSX, AVT, ATLC, LRCX, CAH, SNX, PCB Are Excluded

**Answer: These candidates are all eligible but the pool is exhausted before reaching them.**

| # | Symbol | DAS | Headroom | Eligible? | Allocation | Reason Excluded |
|---|--------|-----|----------|-----------|-----------|----------------|
| 3 | ARW | 93.73 | 79.9% | Yes | $0 | Pool exhausted |
| 4 | PSX | 93.38 | 84.0% | Yes | $0 | Pool exhausted |
| 5 | AVT | 91.87 | 81.7% | Yes | $0 | Pool exhausted |
| 6 | ATLC | 91.74 | 84.3% | Yes | $0 | Pool exhausted |
| 7 | LRCX | 91.48 | 81.0% | Yes | $0 | Pool exhausted |
| 8 | CAH | 91.43 | 80.4% | Yes | $0 | Pool exhausted |
| 9 | PCB | 90.66 | 83.3% | Yes | $0 | Pool exhausted |
| 10 | SNX | 89.91 | 82.2% | Yes | $0 | Pool exhausted |

**Classification: Implementation defect — the 50% proportional cap is too aggressive for multi-candidate deployment.**

---

## Q6: Deployment Engine Comparison ($98,644 scenario)

### CRA Current Algorithm (50% proportional cap)

| # | Symbol | DAS | Allocation | % of Pool |
|---|--------|-----|-----------|---------|
| 1 | DELL | 99.32 | $49,322 | 50.0% |
| 2 | VRT | 94.74 | $49,322 | 50.0% |
| **Total** | | | **$98,644** | 2 positions |

**Projected post-rotation weights:**
- DELL: 1.5% → ~11.8% (DANGER — well above 6% WARN threshold)
- VRT: 4.2% → ~14.4% (DANGER — well above 6% WARN threshold)

### Existing Deployment Plan (tiered, headroom-proportional)

| Tier | Candidates | Pool Share | Positions |
|------|-----------|-----------|---------|
| T1 (CCL) | DELL, VRT, GTX, CVE | $49,322 | 4 |
| T2 (HCA-top) | ARW, PSX, AVT, ATLC, LRCX, CAH, PCB, SNX, NUE, CRS, SANM, ALNT, MTZ | $29,593 | 13 |
| T3 (HCA-rest) | ANGO, FSLR, UHS, STLD, HALO, AGEN, AEIS, ASML | $19,729 | 14 |
| **Total** | | **$98,644** | **31 positions** |

Sample T1 allocations: DELL $16,047 / VRT $6,436 / GTX $14,696 / CVE $12,143

### CRA with 20% Cap (scenario)

| # | Symbol | DAS | Allocation |
|---|--------|-----|-----------|
| 1 | DELL | 99.32 | $19,729 |
| 2 | VRT | 94.74 | $19,729 |
| 3 | ARW | 93.73 | $19,729 |
| 4 | PSX | 93.38 | $19,729 |
| 5 | AVT | 91.87 | $19,729 |
| **Total** | | | **$98,644** / 5 positions |

### Algorithm Comparison Verdict

| Dimension | CRA (current) | Deployment Plan | CRA (20% cap) |
|-----------|--------------|----------------|--------------|
| Method | Sequential + 50% cap | Tiered proportional | Sequential + 20% cap |
| Positions | 2 | 31 | 5 |
| Largest single alloc | $49,322 (50%) | $16,047 (16%) | $19,729 (20%) |
| CW-DAS rank respected | ✅ | Partially (tier-driven) | ✅ |
| Concentration outcome | Extreme concentration | Over-diversified | Moderate |
| Consistent with philosophy | No | Partially | Closer |

**The CRA allocation methodology is NOT reusing the tier allocation logic.** It is a sequential sequential-with-cap algorithm that produces dramatically different and operationally problematic outcomes.
