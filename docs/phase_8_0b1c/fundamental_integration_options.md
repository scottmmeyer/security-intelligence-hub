# Fundamental Integration Options — Phase 8.0B.1C

## Model A — Validation Only (Current State)

**Description:** Fundamentals are displayed in the Fundamental Snapshot panel but have zero scoring impact.

**What exists today:**
- Thesis Integrity (INTACT / QUESTIONABLE / DETERIORATING)
- Fundamental Consistency (CONSISTENT / MIXED / CONTRADICTORY)
- Dislocation Detection (POTENTIAL / HIGH CONVICTION)

**Advantages:**
- Zero risk to existing ranking quality
- Fully reversible
- No new calibration required
- Philosophically conservative

**Risks:**
- Leaves PSX at #4 with DETERIORATING fundamentals and no signal to the operator through scoring
- Does not operationalize the "validates consensus against business fundamentals" language in the CII philosophy
- Dislocation and thesis integrity labels are present but invisible unless cards are expanded

**Alignment with CII:** Compliant but incomplete. The philosophy says CII "validates against fundamentals" — validation-only satisfies the letter but not the spirit.

**Verdict: Insufficient for the long-term but correct for now.** The display layer is valuable. Moving to Model B is the natural next step.

---

## Model B — Conviction Modifier (Recommended)

**Description:** Fundamentals apply a bounded ±0–5 point adjustment to the CW-DAS raw score before final ranking. The modifier cannot flip a CCL below an HCA.

### Proposed Formula

```
fundamental_modifier = beat_bonus + thesis_penalty + consistency_bonus

beat_bonus:
  beat_rate >= 0.875 (7/8+ quarters): +2.0
  beat_rate >= 0.75 (6/8 quarters):   +1.0
  beat_rate >= 0.625 (5/8 quarters):   0
  beat_rate <  0.625:                 −1.0
  insufficient data:                    0

thesis_penalty:
  INTACT:        0
  QUESTIONABLE: −0.5
  DETERIORATING: −3.0
  INSUFFICIENT:  0

consistency_bonus:
  CONSISTENT:     +1.0
  MIXED:           0
  CONTRADICTORY:  −1.5
  INSUFFICIENT:   0

Max bonus: +3.0
Max penalty: −4.5
```

**Cap:** `fundamental_modifier = max(-5.0, min(3.0, fundamental_modifier))`

**Guard:** If modifier would cause a CCL to rank below any HCA, clip at CCL_minimum + 0.1

### Model B: Impact on Current Top 25

| Symbol | Current | Modifier | New Score | Change |
|--------|---------|---------|-----------|--------|
| DELL | 99.3 | +2.0 (beat 86%) + 0 + 1.0 = +3.0 → capped | 102.3 | +3.0 |
| VRT | 94.7 | +2.0 (beat 100%) + 0 + 1.0 = +3.0 → capped | 97.7 | +3.0 |
| ARW | 93.8 | +2.0 (beat 100%) + 0 + 1.0 = +3.0 | 96.8 | +3.0 |
| **PSX** | 93.4 | +1.0 (beat 71%→−1.0) + (−3.0) + 0 = **−4.0** | **89.4** | **−4.0** |
| AVT | 91.9 | −1.0 (beat 86% → +1.0) + (−0.5) + 0 = +0.5 | 92.4 | +0.5 |
| ATLC | 91.7 | +2.0 + 0 + 1.0 = +3.0 | 94.7 | +3.0 |
| LRCX | 91.5 | +2.0 + 0 + 1.0 = +3.0 | 94.5 | +3.0 |
| **CAH** | 91.4 | +2.0 (beat 100%) + (−0.5) + 0 = +1.5 | **92.9** | +1.5 |
| PCB | 90.6 | +1.0 + 0 + 1.0 = +2.0 | 92.6 | +2.0 |

**Net rank changes with Model B:**
- PSX drops from #4 to ~#11 (DETERIORATING penalty is the most significant change)
- LRCX rises from #7 to ~#3 (INTACT + CONSISTENT + 100% beat)
- ATLC rises from #6 to ~#4
- Most other positions shift ≤1–2 places

**Advantages:**
- Directly operationalizes "validates consensus against business fundamentals"
- PSX correction is the most compelling use case — DETERIORATING fundamentals at #4 is a problem
- Beat rate is the cleanest signal and analyst-consensus-normalized
- Bounded ± limits prevent fundamental instability from dominating
- Fully explainable: the modifier is shown in the "Why SIH Likes It" bullet list

**Risks:**
- FSLR with 43% beat rate would be penalized despite valid fundamental reasons for low beat rate
- Requires ongoing calibration as FMP data changes
- Adds complexity to CW-DAS formula

**Mitigation for FSLR-type cases:** Apply modifier only when `fmp_coverage = FULL`. QUESTIONABLE securities with historically unreliable beat rate patterns (solar, biotech) need sector-aware calibration. Consider a sector exclusion list for beat_rate penalty.

---

## Model C — Full Fundamental Scoring Component

**Description:** Add a dedicated `fundamental_c` component to CW-DAS (0–10 range), replacing part of another component.

```
CW-DAS_new = Signal(0-30) + Replay(0-20) + Conviction(0-35) + Sizing(0-8) 
             + Momentum(0-7) + Fundamental(0-10)
             − penalties
```

**Advantages:**
- Makes fundamentals a first-class scoring citizen
- Explicitly models the full thesis integrity range

**Risks:**
- Reduces Momentum weight (7 from 10) — creates a calibration discontinuity
- Introduces a third layer (consensus + momentum + fundamentals) where conviction tier already handles the signal quality aspect
- Moves CII materially toward multi-factor investing
- Requires full regression/validation against historical outcomes

**Alignment:** MODERATE — this begins to look like a fundamental factor model layered on top of consensus, which diverges from the CII philosophy.

**Verdict: NOT recommended at this stage.** Premature given limited historical validation data.

---

## Summary Comparison

| Dimension | Model A | Model B | Model C |
|-----------|---------|---------|---------|
| Philosophy alignment | Full | Strong | Moderate |
| Operator value | Low (already displayed) | High | High |
| Implementation risk | None | Low | Medium |
| Ranking stability | Full | High | Moderate |
| PSX correction | No | Yes (−4.0) | Yes |
| FSLR risk | None | Low (mitigatable) | Low |
| Historical validation needed | No | Minimal | Yes |

**Recommendation: Model B — Conviction Modifier**
