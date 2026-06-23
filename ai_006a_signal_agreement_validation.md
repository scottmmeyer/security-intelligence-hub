# AI-006A Signal Agreement Validation

**Date:** 2026-06-15  
**Source data:** data/current/analytical_universe.csv, data/signals/*, data/signals/fmp/latest/

---

## Signal Agreement: Current SIH vs Official Danelfin Semantics

### Methodology

Signal agreement is computed in `_computeSignalAgreement()` in `ui/portfolio_alignment/app.js`.

Each of four signals (ESS, Zacks, Yahoo, Danelfin) is converted to a direction (BULLISH / NEUTRAL / BEARISH / UNKNOWN). "Agreement score" = count of BULLISH directions / count of available signals.

**Direction conversion functions:**
- ESS: direct text mapping (VERY_BULLISH/BULLISH → BULLISH, NEUTRAL → NEUTRAL, BEARISH/VERY_BEARISH → BEARISH)
- Zacks: `_zacksDirection()` — score ≥4 = BULLISH, ≤2 = BEARISH, else NEUTRAL
- Yahoo: `_yahooDirection()` — based on FMP `consensus_label` (BUY → BULLISH, HOLD → NEUTRAL, SELL → BEARISH)
- Danelfin: `_danelfinDirection()` — normalized ≥3.5 = BULLISH, ≤2.5 = **BEARISH**, else NEUTRAL

---

## Symbol-Level Signal Agreement Table

| Symbol | ESS | Zacks score | Zacks dir | Dan raw | Dan norm | SIH Dan dir | Official Dan dir | Yahoo ABR | Yahoo dir | SIH: Bullish/Total | SIH label | Official: Bullish/Total | Official label |
|--------|-----|------------|-----------|---------|---------|------------|-----------------|-----------|-----------|-------------------|-----------|------------------------|---------------|
| **CAH** | VERY_BULLISH | 4.0 | BULLISH | **5/10** | 2.5/5 | **BEARISH** | **NEUTRAL** | 1.47 (BUY) | BULLISH | **3/4** STRONG | → | **3/4** STRONG | = same |
| ATLC | VERY_BULLISH | 4.0 | BULLISH | 6/10 | 3.0/5 | NEUTRAL | NEUTRAL | no ABR | UNKNOWN | 2/3 MIXED | = | 2/3 MIXED | = same |
| MTZ | BULLISH | 3.0 | NEUTRAL | 9/10 | 4.5/5 | BULLISH | BULLISH | 1.25 (BUY) | BULLISH | 3/4 STRONG | = | 3/4 STRONG | = same |
| NUE | BULLISH | 5.0 | BULLISH | 7/10 | 3.5/5 | BULLISH | BULLISH | 1.76 (BUY) | BULLISH | 4/4 FULL | = | 4/4 FULL | = same |
| SANM | BULLISH | 4.0 | BULLISH | 8/10 | 4.0/5 | BULLISH | BULLISH | 2.50 (BUY) | BULLISH | 4/4 FULL | = | 4/4 FULL | = same |

**Legend:**  
- "STRONG" = STRONG ALIGNMENT (≥3 of 4 BULLISH)  
- "FULL" = FULL ALIGNMENT (4/4 BULLISH)  
- "MIXED" = 2 of available BULLISH

---

## Q4: Is Signal Agreement Correct?

**For 4 of 5 symbols: YES.** MTZ, NUE, SANM, ATLC produce the same agreement label under both SIH and official semantics.

**For CAH: THE LABEL IS THE SAME BUT THE REASONING IS WRONG.**

CAH currently shows STRONG ALIGNMENT (3/4 BULLISH) because:
- ESS = BULLISH
- Zacks = BULLISH  
- Yahoo = BULLISH
- Danelfin = **BEARISH** (SIH) — reduces bullish count but 3/4 still → STRONG ALIGNMENT

Under official semantics:
- Danelfin = **NEUTRAL** — still counted as non-BULLISH but not BEARISH
- Result: 3/4 BULLISH → still STRONG ALIGNMENT

**The agreement LABEL is identical in both cases.** However, the **displayed Danelfin direction** in the signal detail panel shows "BEARISH" for CAH when it should show "NEUTRAL."

---

## Q5: Would CAH Be Classified Differently If Danelfin 5 Were Neutral?

**The agreement label would NOT change** (STRONG ALIGNMENT in both cases).

However the following would change:

| Aspect | Current (SIH) | Corrected (Official) |
|--------|--------------|---------------------|
| Danelfin direction displayed | **BEARISH** | **NEUTRAL** |
| Agreement label | STRONG ALIGNMENT (3/4) | STRONG ALIGNMENT (3/4) |
| ESS override flag triggered? | No (ESS=BULLISH, majority=BULLISH) | No |
| Conflict badge: `CONFLICTING_SIGNAL`? | Not triggered (conflict_classifier uses raw=5 → neither bullish nor bearish) | Same — not triggered |
| Dislocation severity | **MODERATE_DIVERGENCE** | Would be WATCH or lower |

**Bottom line:** The STRONG ALIGNMENT label is correct. The displayed "BEARISH" direction for Danelfin on CAH is a UI inaccuracy that affects the explanation text, not the aggregate decision.

---

## Q6: Would SIGNAL-GOV-01 Conclusions Change?

**No.** SIGNAL-GOV-01 studied Danelfin threshold policies (D0-D3) using `danelfin_raw` values directly. The policy definitions were:
- D2 (Dan≥7): passes if `danelfin_raw >= 7`
- D3 (Dan≥8): passes if `danelfin_raw >= 8`

These are raw value comparisons — they do not involve the BULLISH/NEUTRAL/BEARISH semantic conversion. CAH (raw=5) was always below the D2/D3 thresholds regardless of whether 5 is called Neutral or Bearish.

**SIGNAL-GOV-01 study:** D2 achieved 100% win rate with 10 records. This finding was based on the raw score gate (≥7), not on semantic labeling. The gate aligns with the official Danelfin methodology (7+ = Bullish). The conclusions are **unchanged**.

---

## Q7: Would SIGNAL-GOV-02 Conflict Badges Change?

**No.** The `signal_conflict_classifier.py` uses `danelfin_raw` directly with these constants:
```python
_DANELFIN_BULLISH_MIN = 7.0   # raw ≥ 7 = bullish source
_DANELFIN_BEARISH_MAX = 3.0   # raw ≤ 3 = bearish source
```

These thresholds are **already aligned with Danelfin's official semantics** (7+ = bullish, ≤3 = bearish, 4–6 = neither).

For CAH (raw=5): conflict_classifier correctly treats it as neither bullish nor bearish — matching the official Neutral zone. No badge changes.

**SIGNAL-GOV-02A conflict badges are correct.**
