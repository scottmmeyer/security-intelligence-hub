# Phase 23.6B.2 — Live Validation Results

**Date:** 2026-06-04  
**PAR Run:** PAR-20260604-B01C0C82 (same source file as A47BD0AF)  
**Portfolio MV:** $479,086.31  

---

## Validation Checklist

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Snapshot remains current | ✅ PASS | `Portfolio_Positions_Jun-04-2026 (4).csv` — post-transaction |
| 2 | SPAXX absent from CRA sources | ✅ PASS | Not in sources list (pool: $85,081 vs old $98,644) |
| 3 | PENDING ACTIVITY absent from CRA sources | ✅ PASS | Pattern exclusion confirmed absent |
| 4 | Corrected capital pool reconciles | ✅ PASS | $85,081 = $98,644 − $11,012 − $2,551 ✓ |
| 5 | CRA target count > 2 | ✅ PASS | 31 deployment targets (was 2) |
| 6 | DELL projected weight < WARN | ✅ PASS | 4.49% (was ~11.8%) |
| 7 | VRT projected weight < WARN | ✅ PASS | 5.39% (was ~14.4%) |
| 8 | ARW, PSX, AVT, ATLC, LRCX, CAH, PCB, SNX receive allocations | ✅ PASS | All 8 in top-10 targets |
| 9 | CW-DAS ordering preserved | ✅ PASS | Ranks 1→32 in order |
| 10 | No scoring models changed | ✅ PASS | 943 tests pass, 0 failures |

---

## Corrected Capital Pool Composition

```
Total: $85,081.11  (source_count: 38)
  Removed:   SPAXX         ($11,012.35) — is_cash_equivalent=True
  Removed:   PENDING ACTIVITY ($2,551.15) — settlement artifact pattern

Pool breakdown by category:
  SIGNAL_DETERIORATION   →  URGENT/HIGH (TSLA blocked, KGC/FIS/XYZ active)
  TAX_AWARE_EXIT         →  MODERATE (LMAT, CIEN, HCI, AVGO, ANIP, BNDX, PRG, CBOE...)
  LOW_CONVICTION         →  MODERATE/LOW (VB, VOO, VO, AMG, FXAIX...)
  OVERWEIGHT_REDUCTION   →  LOW (SBS, DODFX, CVE, TSM, GTX, VEA, ASML...)
```

---

## Corrected Deployment Output

```
#1  DELL  CCL  DAS=99.32  $14,256  1.5% → 4.49%   ✓ under 6%
#2  VRT   CCL  DAS=94.74  $5,718   4.2% → 5.39%   ✓ under 6%
#3  ARW   HCA  DAS=93.73  $1,575   1.2% → 1.53%   ✓
#4  PSX   HCA  DAS=93.38  $1,655   0.9% → 1.31%   ✓
#5  AVT   HCA  DAS=91.87  $1,610   1.1% → 1.43%   ✓
#6  ATLC  HCA  DAS=91.74  $1,661   0.9% → 1.29%   ✓
#7  LRCX  HCA  DAS=91.48  $1,596   1.1% → 1.47%   ✓
#8  CAH   HCA  DAS=91.43  $1,584   1.2% → 1.51%   ✓
#9  PCB   HCA  DAS=90.66  $1,642   1.0% → 1.35%   ✓
#10 SNX   HCA  DAS=89.91  $1,620   1.1% → 1.41%   ✓
... (21 additional targets)
Max projected weight: 5.39% (VRT) — under 6% WARN threshold ✓
```

---

## Test Results

```
PYTHONPATH=. .venv/bin/python3 -m pytest tests/test_cra_phase_23_6a.py
78 passed in 0.20s

PYTHONPATH=. .venv/bin/python3 -m pytest -q
943 passed, 1 skipped, 0 failed (38.78s)
```

Zero regressions.
