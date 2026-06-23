# AI-006A Final Verdict — Danelfin Semantic Mapping Audit

**Date:** 2026-06-15  
**Review Status:** COMPLETE  
**Verdict:** Display Inaccuracy Confirmed — Rankings Unaffected

---

## Required Final Answers

### Q1: What does Danelfin officially say a 5 means?

**NEUTRAL.** Danelfin's published methodology defines:
- 7–10 = Bullish (predicts above-market performance)
- **4–6 = Neutral** (AI model uncertain or balanced)
- 1–3 = Bearish (predicts below-market performance)

Raw score 5 is in the middle of the Neutral zone.

---

### Q2: How does SIH currently interpret a 5?

**BEARISH.** The normalization formula converts raw=5 to `danelfin_score = 5/2.0 = 2.5`. The `_danelfinDirection()` function in `app.js` (line 2315) returns `"BEARISH"` for `d <= 2.5`, which includes the exact boundary value 2.5.

```javascript
if (d <= 2.5) return "BEARISH";   // raw=5 → d=2.5 → BEARISH (incorrect)
```

---

### Q3: Is SIH consistent with Danelfin?

**No — for raw scores 4 and 5 only.**

| Raw | Official | SIH |
|-----|---------|-----|
| 4 | Neutral | **BEARISH** ← wrong |
| 5 | Neutral | **BEARISH** ← wrong |
| 6 | Neutral | NEUTRAL ✓ |
| 7+ | Bullish | BULLISH ✓ |
| 1–3 | Bearish | BEARISH ✓ |

The boundary should be `< 2.0` for BEARISH (raw < 4), not `<= 2.5` (raw ≤ 5).

---

### Q4: Is Signal Agreement correct?

**The agreement label is correct. The direction label for CAH's Danelfin is incorrect.**

For the 5 audit symbols:
- MTZ, NUE, SANM: Signal agreement label correct under both interpretations
- ATLC: Signal agreement label correct (both say NEUTRAL)
- **CAH:** Agreement label "STRONG ALIGNMENT" is the same under both interpretations (3/4 BULLISH either way), but the displayed Danelfin direction shows "BEARISH" when it should show "NEUTRAL"

---

### Q5: Is CAH currently being misrepresented?

**Partially — in the signal direction display only.**

The panel that shows individual signal directions for CAH displays:
- Danelfin: 5/10 Score 2.5/5 **[BEARISH]** ← incorrect
- Should display: Danelfin: 5/10 Score 2.5/5 **[NEUTRAL]**

However:
- CAH's composite score (4.444) is correct
- CAH's deployment rank (#6) is correct
- CAH's signal agreement label (STRONG ALIGNMENT) is correct
- CAH's conflict badges are correct

The misrepresentation is **cosmetic** — it appears in the signal direction detail panel only.

---

### Q6: Do governance studies need revision?

**No — SIGNAL-GOV-01 and SIGNAL-GOV-02 conclusions are both valid.**

**SIGNAL-GOV-01:** Used raw value thresholds (D2 = raw≥7, D3 = raw≥8). No semantic label dependency. CAH was correctly excluded from D2 (raw=5 < 7). All backtest conclusions stand.

**SIGNAL-GOV-02A:** Conflict classifier uses `raw ≤ 3` for bearish and `raw ≥ 7` for bullish — this is perfectly aligned with Danelfin's official neutral zone (4–6). All conflict badges are correct.

---

### Q7: Do conflict badges need revision?

**No.** The `signal_conflict_classifier.py` was already implemented with the correct thresholds:
- `_DANELFIN_BULLISH_MIN = 7.0` — raw ≥ 7 = bullish (matches official)
- `_DANELFIN_BEARISH_MAX = 3.0` — raw ≤ 3 = bearish (matches official)
- Raw 4–6 is neither bullish nor bearish (matches official Neutral zone)

**SIGNAL-GOV-02A was implemented correctly for this concern.**

---

### Q8: Do recommendation rankings change?

**No.** CW-DAS uses `danelfin_score` as a numeric value in a weighted average — not as a BULLISH/NEUTRAL/BEARISH label. `2.5 × 0.10 = 0.25` is the Danelfin contribution regardless of what we call it semantically. All composite scores and deployment ranks are unchanged.

---

### Q9: Is a code fix required?

**Yes, in one location: `_danelfinDirection()` in `ui/portfolio_alignment/app.js`.**

**Current (incorrect):**
```javascript
function _danelfinDirection(danelfinScore) {
  const d = parseFloat(danelfinScore);
  if (isNaN(d)) return "UNKNOWN";
  if (d >= 3.5) return "BULLISH";
  if (d <= 2.5) return "BEARISH";   // ← raw=5 → norm=2.5 → BEARISH (wrong)
  return "NEUTRAL";
}
```

**Corrected (aligns with official):**
```javascript
function _danelfinDirection(danelfinScore) {
  const d = parseFloat(danelfinScore);
  if (isNaN(d)) return "UNKNOWN";
  if (d >= 3.5) return "BULLISH";   // raw ≥ 7
  if (d < 2.0)  return "BEARISH";   // raw < 4 (i.e., raw ≤ 3)
  return "NEUTRAL";                  // raw 4–6 (d = 2.0 to 3.49)
}
```

**Optionally:** Adjust dislocation thresholds in `src/portfolio/dislocation.py` so raw=4 and raw=5 don't reach MODERATE_DIVERGENCE — but this is lower priority.

**Scope:** Display fix only. No composite score changes. No ranking changes. No governance changes.

---

### Q10: Is the current implementation production correct?

**Mostly yes — for decisions. No for display accuracy of raw=4 and raw=5 symbols.**

| Dimension | Production Correct? |
|-----------|-------------------|
| Composite score computation | ✅ Yes |
| Deployment queue rankings | ✅ Yes |
| Conflict badge classification | ✅ Yes |
| SIGNAL-GOV-01 studies | ✅ Yes |
| SIGNAL-GOV-02 studies | ✅ Yes |
| Signal agreement label | ✅ Yes (for all 5 audit symbols) |
| Danelfin direction display | ❌ No (raw=4 and raw=5 show BEARISH instead of NEUTRAL) |
| Dislocation tier for raw=4/5 | ⚠️ Minor (MODERATE_DIVERGENCE instead of WATCH) |

**Recommendation:** Option B — "Current implementation technically correct but UI wording misleading."  
The arithmetic core is sound. The semantic label displayed in the signal direction panel for raw=4 and raw=5 symbols is incorrect. A targeted one-function fix to `_danelfinDirection()` resolves the display issue without affecting any decision logic.

---

## Governance Log

| Date | Action | Outcome |
|------|--------|--------|
| 2026-06-15 | AI-006A audit initiated | Semantic mismatch at raw=4 and raw=5 confirmed |
| 2026-06-15 | SIGNAL-GOV-01 re-verified | All conclusions valid — no revision needed |
| 2026-06-15 | SIGNAL-GOV-02A re-verified | All conflict badges correct — no revision needed |
| 2026-06-15 | Code fix identified | One-line change to `_danelfinDirection()` threshold |
| 2026-06-15 | Composite scores verified | All rankings confirmed correct — no change needed |
