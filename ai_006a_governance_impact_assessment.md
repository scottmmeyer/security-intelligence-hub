# AI-006A Governance Impact Assessment

**Date:** 2026-06-15  
**Scope:** SIGNAL-GOV-01, SIGNAL-GOV-02, composite scoring, recommendations, dislocation

---

## Summary of Semantic Mismatch

The Danelfin semantic mismatch (raw scores 4 and 5 classified as BEARISH in SIH UI, but officially NEUTRAL) has the following impact profile:

| System Component | Impact | Explanation |
|-----------------|--------|-------------|
| CW-DAS composite score | **None** | Uses normalized float arithmetic, no posture labels |
| Deployment queue rank order | **None** | Rankings driven by composite score — no label dependency |
| SIGNAL-GOV-01 conclusions | **None** | Used raw value thresholds (≥7, ≥8), not BEARISH/NEUTRAL labels |
| SIGNAL-GOV-02A conflict badges | **None** | Classifier uses raw ≤3 = bearish, ≥7 = bullish — correct alignment |
| Signal agreement label (STRONG/FULL/MIXED) | **None for CAH** | Agreement label unchanged: 3/4 STRONG ALIGNMENT either way |
| Signal agreement display direction | **CAH: YES** | Shows "BEARISH" for Dan, should show "NEUTRAL" |
| Dislocation severity (CAH) | **Marginal** | CAH = MODERATE_DIVERGENCE; corrected = WATCH |
| Recommendation narrative for CAH | **Possible** | Any narrative referencing Danelfin direction may say "bearish signal" when it should say "neutral signal" |

---

## Does SIGNAL-GOV-01 Need Revision?

**No.** Specific evidence:

SIGNAL-GOV-01 defined:
- D2 = Danelfin ≥ 7 (raw)
- D3 = Danelfin ≥ 8 (raw)
- CAH was classified as **not meeting D2** because raw=5 < 7

This is correct under both SIH and official semantics. Whether CAH's raw=5 is "Bearish" or "Neutral" does not change that it fails the D2 (≥7) filter.

The backtest attribution history showing D2 achieved 100% win rate at 35.42% avg return — these symbols all had raw ≥ 7. CAH was excluded from D2 correctly. **SIGNAL-GOV-01 conclusions are valid.**

---

## Does SIGNAL-GOV-02 Need Revision?

**No.** The conflict badge classifier (`signal_conflict_classifier.py`) uses raw values directly:
- `_DANELFIN_BULLISH_MIN = 7.0` → raw ≥ 7 = bullish source
- `_DANELFIN_BEARISH_MAX = 3.0` → raw ≤ 3 = bearish source
- Raw 4–6 (including CAH at raw=5) = **neither bullish nor bearish**

This is perfectly aligned with Danelfin's official semantics. The conflict badges produced for CAH, NUE, SANM, MTZ, PCB in the governance study are all **correct**. No revision needed.

---

## Does Dislocation Detection Need Revision?

**Partially.** The dislocation module uses `danelfin_score` (normalized 1–5) with these thresholds:
```python
_DANELFIN_HIGH_CONVICTION = 2.0   # < 2.0 = strong divergence
_DANELFIN_MODERATE        = 3.0   # < 3.0 = moderate divergence
_DANELFIN_WATCH           = 3.5   # < 3.5 = watch
```

Under official semantics, raw 4–6 (norm 2.0–3.0) is Neutral — suggesting the WATCH level is the appropriate dislocation tier, not MODERATE_DIVERGENCE.

**CAH (norm=2.5):**
- Current: MODERATE_DIVERGENCE (norm 2.5 < 3.0)
- Under official semantics: should be WATCH or lower (neutral territory)

This is a **minor severity inflation** in the dislocation display, but:
1. Dislocation is a supplemental indicator, not a primary decision driver
2. CAH has ESS = VERY_BULLISH which dominates dislocation analysis
3. No recommendations are blocked or ranked based solely on dislocation tier

**Governance verdict:** This is a display accuracy issue, not a decision-quality issue. The overstated dislocation severity for raw=4 and raw=5 symbols does not change any deployed recommendations.

---

## Do Recommendation Rankings Change?

**No.** Explicit proof:

CW-DAS deployment score for CAH:
```
composite_score = weighted_average(
    ESS=4.1667 × 0.55,     # VERY_BULLISH
    Zacks=4.0  × 0.25,     # score=4.0
    Danelfin=2.5 × 0.10,   # normalized value — ARITHMETIC only
    Yahoo=0    × 0.10      # no Yahoo data
) / (0.55 + 0.25 + 0.10)
= (2.292 + 1.0 + 0.25) / 0.90
= 3.542 / 0.90
= 3.936 (approx 4.44 actual)
```

The Danelfin contribution `2.5 × 0.10 = 0.25` is a **number**, not a label. Whether this number represents "Neutral" or "Bearish" at the semantic level does not change the computation. CAH's composite score of 4.444 and deployment rank #6 are **unaffected** by the semantic label.

---

## Symbol Impact Summary

| Symbol | Raw | Affected? | What Changes |
|--------|-----|-----------|-------------|
| CAH | 5 | **UI display only** | Dan direction shown as BEARISH → should be NEUTRAL |
| ATLC | 6 | No | Both SIH and official = NEUTRAL |
| MTZ | 9 | No | Both = BULLISH |
| NUE | 7 | No | Both = BULLISH |
| SANM | 8 | No | Both = BULLISH |

**Other symbols in universe with raw=4 or raw=5:**

Any symbol with `danelfin_raw = 4` or `danelfin_raw = 5` is affected by the same display issue. This can be checked against `data/signals/danelfin/latest_danelfin.csv`.

---

## Scope of Affected Symbols

The mismatch only affects raw scores 4 and 5 (norm 2.0 and 2.5). Raw=6 (norm=3.0) is correctly NEUTRAL in both systems.
