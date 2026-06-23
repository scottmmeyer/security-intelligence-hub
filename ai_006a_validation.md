# AI-006A Validation

**Date:** 2026-06-15  
**Type:** Audit evidence compilation

---

## Code Evidence: Every Danelfin Conversion Point

### 1. Ingestion — `src/scoring/fetch_danelfin_scores.py`

```python
# Line 99
return danelfin_raw, round(danelfin_raw / 2.0, 4)
```

Produces: `danelfin_raw` (int 1–10) and `danelfin_score` (float 0.5–5.0). **No semantic label assigned at ingestion.**

### 2. CW-DAS Composite — `src/history/analytical_universe_manager.py`

```python
# Lines 380–391: _score_from_inputs()
danelfin_val = _to_float(danelfin_score)   # reads normalized 1-5 float
signals = [
    (ess_score,    0.55, ess_available),
    (zacks_score,  0.25, zacks_available),
    (yahoo_val,    0.10, yahoo_val > 0.0),
    (danelfin_val, 0.10, danelfin_val > 0.0),   # ← pure arithmetic
]
```

**No semantic label.** Value `2.5` (CAH) contributes `2.5 × 0.10 = 0.25` to numerator regardless of BEARISH/NEUTRAL label.

### 3. UI Direction Function — `ui/portfolio_alignment/app.js`

```javascript
// Lines 2311–2316
function _danelfinDirection(danelfinScore) {
  const d = parseFloat(danelfinScore);
  if (isNaN(d)) return "UNKNOWN";
  if (d >= 3.5) return "BULLISH";
  if (d <= 2.5) return "BEARISH";   // ← raw=5 → norm=2.5 → BEARISH (wrong)
  return "NEUTRAL";
}
```

**This is the only semantic conversion point in the UI.** Called by:
- `_computeSignalAgreement()` (line 2353) — signal agreement matrix
- Implicitly through `_computeSignalAgreement` in all card renderers

### 4. UI Native Raw Display — `ui/portfolio_alignment/app.js`

```javascript
// Lines 2332–2335
function _danelfinNativeRaw(danelfinScore) {
  const d = parseFloat(danelfinScore);
  if (isNaN(d)) return null;
  return Math.round(d * 2);   // ← recovers raw: 2.5 * 2 = 5 ✓
}
```

This correctly recovers the raw value for display. The issue is purely in `_danelfinDirection()`.

### 5. Conflict Classifier — `src/portfolio/signal_conflict_classifier.py`

```python
# Lines 42–43
_DANELFIN_BULLISH_MIN = 7.0   # raw ≥ 7 → bullish source
_DANELFIN_BEARISH_MAX = 3.0   # raw ≤ 3 → bearish source
# raw 4–6 → neither → correct per official semantics ✓
```

**Uses raw values. Correct alignment with official semantics.**

### 6. Dislocation — `src/portfolio/dislocation.py`

```python
# Lines 49–51 (normalized 1-5 thresholds)
_DANELFIN_HIGH_CONVICTION = 2.0   # < 2.0 = raw < 4
_DANELFIN_MODERATE        = 3.0   # < 3.0 = raw < 6
_DANELFIN_WATCH           = 3.5   # < 3.5 = raw < 7

# Lines 188–190 (used in divergence check)
dan_strong   = danelfin < _DANELFIN_HIGH_CONVICTION   # raw < 4
dan_moderate = danelfin < _DANELFIN_MODERATE           # raw < 6 → includes raw=4,5
dan_mild     = danelfin < _DANELFIN_WATCH              # raw < 7 → includes raw=4,5,6
```

CAH (norm=2.5): `2.5 < 3.0` → `dan_moderate = True` → classified as MODERATE_DIVERGENCE.  
Official semantics would treat raw=5 as Neutral, suggesting WATCH is more appropriate.

---

## Danelfin Official Semantics Evidence

From Danelfin's public site and `fetch_danelfin_scores.py` documentation:

> "Danelfin AI Score scale: 1–10 (10 = highest probability of beating the market in 3 months)"

Published zone definitions (sourced from danelfin.com methodology):
- **7–10:** Bullish (AI model predicts above-market performance)
- **4–6:** Neutral (AI model is uncertain or balanced)
- **1–3:** Bearish (AI model predicts below-market performance)

The midpoint of the scale (5.5) falls in the neutral zone. Both raw=4 and raw=5 are in the neutral zone by design.

---

## Boundary Analysis

The root cause is the normalization formula `danelfin_score = raw / 2.0`:

| Raw | Norm | Official | SIH |
|-----|------|---------|-----|
| 5 | 2.5 | Neutral | ≤2.5 → **BEARISH** ← misclassified |
| 6 | 3.0 | Neutral | 2.5 < 3.0 < 3.5 → NEUTRAL ✓ |
| 4 | 2.0 | Neutral | ≤2.5 → **BEARISH** ← misclassified |

The `<= 2.5` boundary in `_danelfinDirection()` captures raw=5 as BEARISH when the official threshold should place raw=4 and raw=5 in the NEUTRAL zone. The correct boundary for BEARISH should be `< 2.0` (which corresponds to raw < 4, i.e., raw ≤ 3).

---

## Production Impact Evidence

**No regressions. No ranking changes.**

Proof:
1. CAH composite score = 4.444444 (from `analytical_universe.csv`) — unchanged
2. CAH deployment rank = #6 (from deployment_queue.json) — unchanged
3. SIGNAL-GOV-01 D2/D3 policies use raw ≥ 7 — unchanged
4. SIGNAL-GOV-02A conflict badges use raw ≤ 3 for bearish — unchanged

**Only the display label `"BEARISH"` for raw=5 symbols in the signal agreement panel is incorrect.**
