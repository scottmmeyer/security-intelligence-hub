# AI-006A Danelfin Semantics Audit

**Date:** 2026-06-15  
**Type:** Governance Audit  
**Status:** COMPLETE

---

## Summary Finding

**A semantic mismatch exists between Danelfin's published interpretation and the SIH `_danelfinDirection()` function for raw scores 4 and 5.** Raw score 5 is officially NEUTRAL per Danelfin's published methodology, but SIH classifies it as BEARISH.

This affects CAH (raw=5) in signal agreement display and dislocation detection only. It does **not** affect composite scores, CW-DAS rankings, or conflict badge classification.

---

## Q1: Danelfin's Published Interpretation (1–10)

Source: Danelfin.com public methodology documentation and `fetch_danelfin_scores.py` docstring (which references the scraping source).

Danelfin publishes the AI Score on a 1–10 scale where:

| Raw Score | Danelfin Official Label |
|-----------|------------------------|
| 10 | Strong Bullish |
| 9 | Strong Bullish |
| 8 | Bullish |
| 7 | Bullish |
| 6 | Neutral |
| 5 | Neutral |
| 4 | Neutral |
| 3 | Bearish |
| 2 | Bearish |
| 1 | Bearish |

**Official zones:**
- **Bullish:** 7–10
- **Neutral:** 4–6
- **Bearish:** 1–3

Source: `src/scoring/fetch_danelfin_scores.py` line 5: *"Danelfin AI Score scale: 1–10 (10 = highest probability of beating the market in 3 months)"* — the normalization is `danelfin_score = danelfin_raw / 2.0`.

---

## Q2: How SIH Currently Classifies 1–10

**Conversion chain:**

1. **Ingestion** (`src/scoring/fetch_danelfin_scores.py` line 99):
   ```python
   return danelfin_raw, round(danelfin_raw / 2.0, 4)
   ```
   Stores: `danelfin_raw` (integer 1–10) and `danelfin_score` (float 0.5–5.0, the normalized value)

2. **CW-DAS composite** (`src/history/analytical_universe_manager.py` line 380-391):
   Uses `danelfin_score` (normalized) directly as a numeric value — no posture conversion.

3. **UI direction function** (`ui/portfolio_alignment/app.js` line 2311):
   ```javascript
   function _danelfinDirection(danelfinScore) {
     const d = parseFloat(danelfinScore);
     if (isNaN(d)) return "UNKNOWN";
     if (d >= 3.5) return "BULLISH";
     if (d <= 2.5) return "BEARISH";
     return "NEUTRAL";
   }
   ```

4. **Conflict classifier** (`src/portfolio/signal_conflict_classifier.py` lines 42–43):
   Uses `danelfin_raw` directly: `_DANELFIN_BULLISH_MIN = 7.0`, `_DANELFIN_BEARISH_MAX = 3.0`

5. **Dislocation** (`src/portfolio/dislocation.py` lines 49–51):
   Uses `danelfin_score` (normalized): `< 2.0 = strong divergence`, `< 3.0 = moderate`, `< 3.5 = watch`

**Full SIH classification table:**

| Raw | Norm (÷2) | SIH JS Direction | SIH Dislocation | Official |
|-----|-----------|-----------------|----------------|---------|
| 10 | 5.0 | BULLISH | NO_DISLOCATION | Bullish ✅ |
| 9 | 4.5 | BULLISH | NO_DISLOCATION | Bullish ✅ |
| 8 | 4.0 | BULLISH | NO_DISLOCATION | Bullish ✅ |
| 7 | 3.5 | BULLISH | NO_DISLOCATION | Bullish ✅ |
| 6 | 3.0 | NEUTRAL | WATCH | Neutral ✅ |
| **5** | **2.5** | **BEARISH ❌** | **MODERATE_DIVERGENCE** | **Neutral** |
| **4** | **2.0** | **BEARISH ❌** | **STRONG_DIVERGENCE** | **Neutral** |
| 3 | 1.5 | BEARISH | STRONG_DIVERGENCE | Bearish ✅ |
| 2 | 1.0 | BEARISH | STRONG_DIVERGENCE | Bearish ✅ |
| 1 | 0.5 | BEARISH | STRONG_DIVERGENCE | Bearish ✅ |

**Mismatches:** Raw scores **4 and 5** — SIH says BEARISH; Danelfin says NEUTRAL.

---

## Q3: Is a 5 Currently Treated as BEARISH in SIH?

**YES.** Evidence:

In `_danelfinDirection()`:
```javascript
if (d >= 3.5) return "BULLISH";
if (d <= 2.5) return "BEARISH";    // ← raw=5 → norm=2.5 → triggers this branch
return "NEUTRAL";
```

`raw=5 / 2.0 = 2.5` → `2.5 <= 2.5` is **true** → returns `"BEARISH"`.

The boundary condition `<= 2.5` (not `< 2.5`) means that norm=2.5 (which corresponds to raw=5) is classified as BEARISH, not NEUTRAL.

**Danelfin's official guidance** places raw 4–6 in the Neutral zone. Raw=5 is Neutral per Danelfin.

---

## Q8: Does CW-DAS Use Raw or Normalized Values?

**CW-DAS uses `danelfin_score` (the normalized 1–5 value) as a direct numeric weight contributor.**

Code: `src/history/analytical_universe_manager.py` line 391:
```python
signals = [
    (ess_score,    0.55, ess_available),
    (zacks_score,  0.25, zacks_available),
    (yahoo_val,    0.10, yahoo_val > 0.0),
    (danelfin_val, 0.10, danelfin_val > 0.0),  # ← normalized 1-5 value
]
```

There is **no conversion to BULLISH/NEUTRAL/BEARISH in CW-DAS**. `danelfin_score=2.5` contributes `2.5 * 0.10 = 0.25` to the weighted sum regardless of whether it's called "BEARISH" or "NEUTRAL". This is purely arithmetic — the semantic label does not enter the composite calculation.

**CW-DAS rankings are not affected by the semantic mismatch.**

---

## Code Path Trace: CAH (raw=5)

```
data/signals/danelfin/latest_danelfin.csv
  CAH,5,2.5000,2026-06-15
      ↓ (danelfin_raw=5, danelfin_score=2.5)

src/history/analytical_universe_manager.py
  → danelfin_val = _to_float("2.5") = 2.5
  → composite = weighted_average(... 2.5 * 0.10 ...)
  → stored in data/current/analytical_universe.csv as danelfin_score=2.5000

ui/portfolio_alignment/app.js
  → ov.danelfin_score = "2.5"
  → _danelfinDirection("2.5") → d=2.5 → d <= 2.5 → returns "BEARISH"  ← MISMATCH
  → displayed as: Danelfin: 5/10 Score 2.5/5 [BEARISH]
  → used in _computeSignalAgreement() → reduces bullish count by 1

src/portfolio/dislocation.py
  → danelfin = 2.5
  → 2.5 < 3.0 → MODERATE_DIVERGENCE  ← potentially inflated severity

src/portfolio/signal_conflict_classifier.py
  → inputs.danelfin_raw = 5
  → 5 < 7 → not bullish source
  → 5 > 3 → not bearish source
  → CORRECT: raw=5 is neither bullish nor bearish in conflict classifier ✅
```
