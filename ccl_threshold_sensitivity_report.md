# CCL Threshold Sensitivity Report — Phase 7.5R
**Run:** PAR-20260529-BAF83F16 | **Date:** 2026-05-31  
**Question:** Does the 1.5% CCL promotion threshold drive deployment concentration?

---

## 1. Executive Summary

**Finding: The CCL threshold is a secondary driver of concentration. The planner multiplier is the primary driver.**

- Changing the threshold from 1.50% → 1.00% reduces Top-1 concentration by only **6.1 percentage points** (26.6% → 20.5%)
- The same multiplier change tested in Phase 7.5Q reduces Top-1 by **12.1 percentage points** (26.6% → 14.5%)
- The threshold change produces **zero improvement** in signal alignment (r(composite, alloc) moves by −0.007 — worse, not better)
- The multiplier change produces **+0.22 improvement** in signal alignment

**Critical paradox:** Lowering the threshold does not reduce concentration — it transfers it. Under a 1.0% threshold, DELL (1.32% weight, composite 4.44) replaces VRT as the dominant receiver. CAH (1.06% weight, composite 4.50) becomes the top-ranked candidate and receives 20.5% of capital. The system is still concentrated; only the recipient changed.

---

## 2. Current CCL Holdings (Scenario C — 1.50% Threshold)

There are currently **5 CCL holdings**, not 1:

| Symbol | Weight% | Composite | Trim Score | CW-DAS | Queue Rank | Deployed |
|--------|---------|-----------|------------|--------|------------|---------|
| VRT | 3.60% | 4.5556 | 1.62 | 95.53 | 1 | $8,822 |
| CVE | 2.47% | 4.8333 | 12.61 | 83.71 | 32 | $0 (blocked) |
| TSM | 2.33% | 4.4444 | 12.55 | 81.56 | 33 | $0 (blocked) |
| GTX | 1.94% | 4.1667 | 12.37 | 80.41 | 34 | $0 (blocked) |
| MU | 6.14% | 4.7222 | 2.76 | 77.77 | 36 | $0 (above WARN) |

Note: CVE, TSM, GTX, MU hold CCL tier status but receive no deployment capital. Their CW-DAS scores are low enough (due to concentration/OW-node penalties) that they rank 32–36. The entire CCL deployment premium in this run flows exclusively through VRT.

---

## 3. CCL-Eligibility Analysis

CCL gate conditions: signal=BULLISH AND replay=True AND composite ≥ 4.0 AND trim_score < 30.0 AND weight ≥ threshold

**Holdings that satisfy base criteria (all except weight threshold):**

| Symbol | Weight% | Composite | Trim | Eligible for CCL if threshold ≤ |
|--------|---------|-----------|------|----------------------------------|
| MU | 6.14% | 4.72 | 2.76 | 1.0% (already CCL, blocked) |
| VRT | 3.60% | 4.56 | 1.62 | 1.0% |
| CVE | 2.47% | 4.83 | 12.61 | 1.0% |
| TSM | 2.33% | 4.44 | 12.55 | 1.0% |
| GTX | 1.94% | 4.17 | 12.37 | 1.0% |
| DELL | 1.32% | 4.44 | 0.59 | **1.25%** ← new at B |
| CIEN | 1.17% | 4.28 | 0.53 | **1.00%** ← new at A |
| CAH | 1.06% | 4.50 | 0.48 | **1.00%** ← new at A |

Holdings that **cannot** qualify under any threshold (base criteria fail):
- NVDA (3.20%): composite = 3.83 < 4.0
- SBS (3.83%): composite = 3.71 < 4.0
- LRCX, PCB, AVT, ARW, ATLC, SNX, PSX, CBOE: weight < 1.00% (would need threshold ≤ weight)

---

## 4. Scenario Results

### Summary Table

| Scenario | Threshold | CCL Count | CCL Symbols | Top-1% | Top-5% | Top-10% | r(comp,alloc) | r(wt,alloc) |
|----------|-----------|-----------|-------------|--------|--------|---------|---------------|-------------|
| A | 1.00% | 8 | CAH,CIEN,CVE,DELL,GTX,MU,TSM,VRT | 20.5% | 59.4% | 71.0% | 0.4014 | 0.5083 |
| B | 1.25% | 6 | CVE,DELL,GTX,MU,TSM,VRT | 24.0% | 52.3% | 65.8% | 0.3847 | 0.6462 |
| **C (current)** | **1.50%** | **5** | **CVE,GTX,MU,TSM,VRT** | **26.6%** | **46.0%** | **61.3%** | **0.4080** | **0.8721** |
| D | 2.00% | 4 | CVE,MU,TSM,VRT | 26.6% | 46.0% | 61.3% | 0.4080 | 0.8721 |

### Critical Observations

**Scenario D = Scenario C.** Raising the threshold to 2.00% demotes GTX (1.94%) but produces zero change in any output metric. VRT (3.60%), CVE (2.47%), TSM (2.33%), MU (6.14%) all remain CCL. GTX was already blocked (OW node / low headroom), so its tier change is completely invisible in the deployment output.

**Scenario B (1.25%) is worse than C on Top-1%.** Promoting DELL to CCL pushes DELL to rank 1 (score jumps from 90.91 → 97.91). DELL then receives $7,973 (24.0% of pool), which is MORE concentrated than VRT's current $8,822 (26.6%) — the distribution remains highly concentrated but now in a different name.

**Scenario A (1.00%) reduces Top-1% but concentrates Top-5%.** CAH becomes rank 1 (composite 4.50 → CCL score 98.59) and receives $6,806 (20.5%). But Top-5% actually INCREASES to 59.4% vs 46.0% current — the capital is more broadly concentrated across multiple CCL recipients.

---

## 5. Promotions and Demotions by Scenario

### Scenario A (1.00%) — Promoted: CAH, CIEN, DELL

| Symbol | Weight | Why Promoted | New Rank | New Alloc | Change from C |
|--------|--------|--------------|----------|-----------|---------------|
| CAH | 1.06% | weight ≥ 1.00%, comp=4.50, trim=0.48 | **1** (up from 9) | $6,806 | +$5,866 |
| DELL | 1.32% | weight ≥ 1.00%, comp=4.44, trim=0.59 | **3** (up from 10) | $4,779 | +$3,894 |
| CIEN | 1.17% | weight ≥ 1.00%, comp=4.28, trim=0.53 | **6** (up from 13) | $3,870 | +$3,101 |
| **VRT** | 3.60% | still CCL, but rank drops | **4** (down from 1) | $3,297 | −$5,525 |

Note: VRT loses rank 1 when CAH and DELL enter with higher CW-DAS scores (+7 conviction pts elevates CAH to 98.59). VRT actually receives *less* capital under a lower threshold.

### Scenario B (1.25%) — Promoted: DELL only

| Symbol | Weight | Change from C | New Rank | New Alloc |
|--------|--------|---------------|----------|-----------|
| DELL | 1.32% | Promoted | **1** (up from 10) | $7,973 (+$7,088) |
| VRT | 3.60% | Still CCL | **2** (down from 1) | $5,501 (−$3,321) |

### Scenario D (2.00%) — Demoted: GTX

| Symbol | Change | Effect |
|--------|--------|--------|
| GTX | Demoted | Zero effect — GTX was already blocked from deployment |

---

## 6. Focus Symbol Analysis

### Capital Allocation by Scenario

| Symbol | Weight% | A_100 Tier | A_100 Alloc | B_125 Tier | B_125 Alloc | C_150 Tier | C_150 Alloc | D_200 Tier | D_200 Alloc |
|--------|---------|-----------|------------|-----------|------------|-----------|------------|-----------|------------|
| ARW | 0.92% | HCA | $968 | HCA | $1,475 | HCA | $2,048 | HCA | $2,048 |
| ATLC | 0.89% | HCA | $813 | HCA | $1,135 | HCA | $1,439 | HCA | $1,439 |
| SNX | 0.86% | HCA | $879 | HCA | $1,269 | HCA | $1,662 | HCA | $1,662 |
| AVT | 0.93% | HCA | $670 | HCA | $884 | HCA | $1,072 | HCA | $1,072 |
| **CAH** | **1.06%** | **CCL** | **$6,806** | HCA | $786 | HCA | $940 | HCA | $940 |
| **CIEN** | **1.17%** | **CCL** | **$3,870** | HCA | $678 | HCA | $769 | HCA | $769 |
| **DELL** | **1.32%** | **CCL** | **$4,779** | **CCL** | **$7,973** | HCA | $885 | HCA | $885 |
| PSX | 0.75% | HCA | $759 | HCA | $1,034 | HCA | $1,285 | HCA | $1,285 |
| **VRT** | **3.60%** | **CCL** | **$3,297** | **CCL** | **$5,501** | **CCL** | **$8,822** | **CCL** | **$8,822** |

### Key Patterns

**ARW, ATLC, SNX, AVT, PSX:** Never qualify for CCL under any scenario (weights < 1.00%). Their allocations decrease as threshold lowers — more CCL candidates compete for the pool, reducing HCA allocations.

**CAH and CIEN (A_100 only):** Receive large allocations under A_100 ($6,806 and $3,870) but are displaced when threshold rises. Neither crosses the 1.25% threshold.

**DELL:** Crosses the 1.25% threshold and becomes rank 1 under B_125, receiving $7,973. This is the "DELL problem" — a new concentration risk.

**VRT:** Counter-intuitively receives MORE capital as the threshold rises. As fewer CCL promotees share the pool, VRT's planner weight dominates.

---

## 7. Deployment Rank Sensitivity

VRT's rank under each scenario:

| Scenario | VRT Rank | Top Candidate | Top Candidate Alloc |
|----------|----------|---------------|---------------------|
| A_100 | **4** | CAH ($6,806) | 20.5% |
| B_125 | **2** | DELL ($7,973) | 24.0% |
| C_150 | **1** | VRT ($8,822) | 26.6% |
| D_200 | **1** | VRT ($8,822) | 26.6% |

Lowering the threshold transfers the top-ranked CCL position to whichever recently-promoted holding has the highest composite score. Since CAH (composite=4.50) > VRT (composite=4.56 — actually VRT scores higher, but CAH gets 98.59 vs VRT 95.53 due to better sizing headroom), CAH jumps above VRT.
