# Signal Governance — Current Portfolio Analysis

**Date:** 2026-06-15  
**Source:** Active deployment queue (10 symbols)

---

## Current Queue — Full Policy Matrix

| Rank | Symbol | ESS | Zacks | Danelfin | Z2(≥4) | Z3(≥5) | D2(≥7) | D3(≥8) | C1(Z4+D7) | C2(Z4orD7) | C3(Z5+D7) | C4(Z4+D8) |
|------|--------|-----|-------|---------|--------|--------|--------|--------|-----------|------------|-----------|-----------|
| #1 | VRT | VERY_BULLISH | 4.0 | 7 | PASS | FAIL | PASS | FAIL | PASS | PASS | FAIL | FAIL |
| #2 | ATLC | VERY_BULLISH | 4.0 | 6 | PASS | FAIL | FAIL | FAIL | FAIL | PASS | FAIL | FAIL |
| #3 | DELL | VERY_BULLISH | 5.0 | 5 | PASS | PASS | FAIL | FAIL | FAIL | PASS | FAIL | FAIL |
| #4 | LRCX | VERY_BULLISH | 4.0 | 6 | PASS | FAIL | FAIL | FAIL | FAIL | PASS | FAIL | FAIL |
| #5 | PCB | VERY_BULLISH | 3.0 | 7 | **FAIL** | **FAIL** | PASS | FAIL | FAIL | PASS | FAIL | FAIL |
| #6 | CAH | VERY_BULLISH | 4.0 | 5 | PASS | FAIL | FAIL | FAIL | FAIL | PASS | FAIL | FAIL |
| #7 | SANM | BULLISH | 4.0 | 8 | PASS | FAIL | PASS | PASS | PASS | PASS | FAIL | PASS |
| #8 | MTZ | BULLISH | 3.0 | 9 | **FAIL** | **FAIL** | PASS | PASS | FAIL | PASS | FAIL | FAIL |
| #9 | CRS | BULLISH | 4.0 | 8 | PASS | FAIL | PASS | PASS | PASS | PASS | FAIL | PASS |
| #10 | NUE | BULLISH | 5.0 | 7 | PASS | PASS | PASS | FAIL | PASS | PASS | PASS | FAIL |

---

## Symbols Affected by Each Policy

| Policy | Pass Count | Fail Count | Excluded Symbols |
|--------|-----------|-----------|-----------------|
| Z2 (Zacks≥4) | 8/10 | 2/10 | PCB (#5), MTZ (#8) |
| Z3 (Zacks≥5) | 2/10 | 8/10 | VRT, ATLC, LRCX, PCB, CAH, SANM, MTZ, CRS |
| D2 (Dan≥7) | 6/10 | 4/10 | ATLC (#2), DELL (#3), LRCX (#4), CAH (#6) |
| D3 (Dan≥8) | 3/10 | 7/10 | VRT, ATLC, DELL, LRCX, PCB, CAH, NUE |
| C1 (Z≥4 AND D≥7) | 4/10 | 6/10 | ATLC, DELL, LRCX, PCB, CAH, MTZ |
| C2 (Z≥4 OR D≥7) | 10/10 | 0/10 | none |
| C3 (Z≥5 AND D≥7) | 1/10 | 9/10 | VRT, ATLC, DELL, LRCX, PCB, CAH, SANM, MTZ, CRS |
| C4 (Z≥4 AND D≥8) | 2/10 | 8/10 | VRT, ATLC, DELL, LRCX, PCB, CAH, MTZ, NUE |

---

## Symbol Risk Profile Analysis

### SANM (#7) and CRS (#9) — Highest Dual-Signal Quality
- Both have Zacks≥4 AND Danelfin≥8
- Pass all reasonable policies (Z2, D2, D3, C1, C2, C4)
- Represent the ideal dual-confirmation profile

### NUE (#10) — Strong Zacks, Solid Danelfin
- Zacks=5.0 (STRONG BUY), Danelfin=7.0
- Passes Z2, Z3, D2, C1, C2, C3
- Fails only D3 (≥8), C4 (≥8)

### VRT (#1) — Best Historical Attribution
- Zacks=4.0, Danelfin=7.0
- VRT has 3 WINNER records in attribution history (17.40%, 8.80%, 4.47%)
- Passes Z2, D2, C1, C2
- Fails Z3 (needs Zacks=5), D3, C3, C4

### PCB (#5) — Zacks NEUTRAL, Danelfin Confirms
- Zacks=3.0 (NEUTRAL) — fails Z2, Z3, C1, C3, C4
- Danelfin=7.0 — passes D2, C2
- Historical backtest: PCB returned +12.03% as WINNER
- **Advisory: Zacks NEUTRAL offset by strong Danelfin. C2 (OR gate) allows through.**

### MTZ (#8) — Zacks NEUTRAL, Very Strong Danelfin
- Zacks=3.0 (NEUTRAL) — fails Z2, Z3, C1, C3, C4
- Danelfin=9.0 — highest in queue
- No direct historical attribution record for MTZ
- **Advisory: Strong Danelfin counterbalances Zacks NEUTRAL. C2 allows through.**

### CAH (#6) — Weaker Dual Signal
- Zacks=4.0, Danelfin=5.0
- Fails D2, D3, C1, C3, C4
- Historical: 2× WINNER but lower returns (10.93%, 4.26%) — consistent with mixed signal quality
- Passes Z2, C2

### DELL (#3) — Strong Zacks, Weak Danelfin
- Zacks=5.0 (STRONG BUY), Danelfin=5.0
- Fails D2, D3, C1, C3, C4
- Historical: 1 WINNER (+6.49%), 1 NEUTRAL (−0.12%)
- **The only symbol with a non-winner historical record**

---

## Recommended Advisory Flags for Current Queue

Under advisory (non-enforced) governance, the following symbols warrant operator attention:

| Symbol | Alert | Reason |
|--------|-------|--------|
| PCB | `ZACKS_NEUTRAL` | Zacks=3.0; Danelfin=7 partially offsets |
| MTZ | `ZACKS_NEUTRAL` | Zacks=3.0; Danelfin=9 is strong override |
| DELL | `DANELFIN_BELOW_TARGET` | Danelfin=5; Zacks=5 partially offsets |
| CAH | `DANELFIN_BELOW_TARGET` | Danelfin=5; Zacks=4 partially offsets |
| ATLC | `DANELFIN_WATCH` | Danelfin=6; borderline |
| LRCX | `DANELFIN_WATCH` | Danelfin=6; borderline |
