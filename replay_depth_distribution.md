# Replay Depth Distribution
**Phase 7.6D — Replay Authority Calibration Audit**
**Run Reference:** PAR-20260601-9CFD7C63
**Date:** 2026-06-01

---

## Classification Schema

| Tier | Coverage Days | Meaning |
|---|---|---|
| STRONG | ≥ 180 days | Substantial historical window; at minimum half-year forward performance validated |
| MODERATE | 30–179 days | Partial quarter/seasonal evidence |
| THIN | 1–29 days | Near-term snapshot only; less than one month of evidence |
| BUCKET_ONLY | 0 (replay_supported via bucket assignment only) | Sector/cap-bucket replay passed; symbol not individually selected in any basket |
| NONE | 0, replay_supported = False | No replay evidence; not in any validated bucket |

---

## Deployment Queue Distribution (CW-DAS Ranked Holdings, n=42)

### STRONG (≥ 180 days) — 38 holdings

All STRONG holdings have exactly **365 days** of evidence (2025-05-14 to 2026-05-14).

| Metric | Value |
|---|---|
| Count | 38 |
| Avg CW-DAS score | 87.94 |
| Avg UCF score | 86.28 |
| Avg deployment rank | 19.0 |
| Rank range | 1–42 |
| Min/max CW-DAS | 65.65 / 95.50 |

Holdings (by rank): VRT(1), ARW(2), SNX(3), ATLC(4), PSX(5), CBOE(6), AVT(7), LRCX(8), CAH(9), DELL(10), PCB(12), CIEN(13), NUE(14), GFF(15), ALNT(16), MTZ(17), CRS(18), CMCO(19), ANGO(20), FSLR(21), UHS(22), HALO(23), BSVN(24), STLD(25), AGEN(26), YELP(27), UTHR(29), DVN(28), ANIP(30), AZZ(31), CVE(32), TSM(33), MU(35), ASML(36), STNG(37), AVGO(39), NVDA(41), MSFT(40)

---

### MODERATE (30–179 days) — 0 holdings

**No holdings exist in the MODERATE tier.** The replay system generates either full 365-day historical windows or very short recent windows (6-day). There is no intermediate window in the current run. The distribution is bimodal: 365-day or 6-day.

---

### THIN (<30 days) — 1 holding

| Metric | Value |
|---|---|
| Count | 1 |
| Symbol | SANM |
| Coverage days | 6 (2026-05-20 to 2026-05-26) |
| Replay type | CURRENT_RECOMMENDATION |
| Avg CW-DAS score | 90.78 |
| UCF score | 89.53 |
| Deployment rank | 11 |
| UCF label | HIGH_CONVICTION_ANCHOR |

**Key observation:** SANM appears at rank 11 in the deployment queue — higher than 31 of 42 ranked holdings — despite having only 6 days of replay evidence. SANM's position is supported by strong ESS+Zacks+Danelfin signals (composite_score high) and the full 20-point binary replay bonus. In the current binary system, its 6-day replay evidence is treated identically to the 365-day evidence of VRT (rank 1).

A second THIN-evidence holding, **AEIS** (also 6 days, CURRENT_RECOMMENDATION replay), has replay_supported=True in UCF but is not ranked in the CW-DAS deployment queue (UCF label: DEPLOYMENT_CANDIDATE with COMPOSITE_ESS_DIVERGE flag).

---

### BUCKET_ONLY (replay_supported via bucket assignment, no basket appearance) — 3 holdings

These holdings have `replay_supported = True` in UCF but do not appear in any replay basket's `selected_symbols` list. They receive the replay bonus because their sector/cap bucket passed the replay validation, but they were not individually selected among the top-N symbols in that basket.

| Symbol | CW-DAS Score | Rank | UCF Label |
|---|---|---|---|
| GTX | 80.47 | 34 | HIGH_CONVICTION_ANCHOR |
| SIMO | 75.53 | 38 | HIGH_CONVICTION_ANCHOR |
| SBS | 65.65 | 42 | HIGH_CONVICTION_ANCHOR |

**Key observation:** These holdings receive the full 20-pt replay bonus based on their bucket qualifying, not on their individual performance within the basket. Their replay evidence is structural (bucket-level) rather than individual-selection evidence.

---

### NONE (replay_supported = False) — Active deployment-relevant holdings

Holdings with replay_supported = False are generally in TACTICAL_GROWTH, TRIM_WATCH, or MAINTAIN labels and not in the primary deployment queue. Examples: PLTR, KGC, PRIM, MKSI, HCI, LMAT, JBL, IVZ, FHI, MCB, PRG, AMG.

---

## Bimodal Evidence Distribution — Key Finding

```
Evidence Distribution (CW-DAS ranked holdings)

 40 |████████████████████████████████████████  ← 38 holdings at 365 days
    |
 30 |
    |
 20 |
    |
 10 |
    |
  0 |
  1 |█  ← SANM (6 days)
    |
    ├────────────────────────────────────────────────
    0    30   60   90  120  150  180  210  240  270  300  330  365
                        Coverage Days
```

The distribution is sharply bimodal: **365 days or 6 days**. There is no continuous spectrum of evidence depth. This means the practical choice in any depth-aware model is not a gradient calibration — it is a binary decision between "full year validated" and "very recent short-window only."

---

## Portfolio Value by Tier

Portfolio holdings in deployment queue by tier (PAR-20260601-9CFD7C63, $33,141.34 total capital):

| Tier | Holdings | % of Ranked Queue |
|---|---|---|
| STRONG (365 days) | 38 | 90.5% |
| THIN (6 days) | 1 (SANM) | 2.4% |
| BUCKET_ONLY | 3 (GTX, SIMO, SBS) | 7.1% |
| MODERATE | 0 | 0% |

The vast majority of deployed capital targets STRONG-evidence holdings. SANM represents the only case where THIN evidence materially affects a top-20 deployment priority.
