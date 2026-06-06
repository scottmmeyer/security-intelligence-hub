# Phase 8.0B.1C Recommendation

## Assessment Classification

**APPROVED WITH ADVISORIES**

## Primary Recommendation

**Option B — Add Conviction Modifier**

A bounded fundamental conviction modifier should be added to CW-DAS in a subsequent implementation phase (ISSUE-07).

---

## Exact Component Specification

### Name
`fundamental_modifier` (not a standalone CW-DAS component — applied as a post-calculation adjustment)

### Formula

```python
def compute_fundamental_modifier(
    beat_rate: Optional[float],       # 0.0–1.0; None if insufficient data
    thesis: str,                      # INTACT | QUESTIONABLE | DETERIORATING | INSUFFICIENT_DATA
    consistency: str,                 # CONSISTENT | MIXED | CONTRADICTORY | INSUFFICIENT_DATA
    fmp_coverage: str,                # FULL | PARTIAL | NO_DATA | ETF_NOT_APPLICABLE
) -> float:
    """Returns a bounded modifier to be added to raw CW-DAS before final score.
    
    Range: −5.0 to +3.0
    No-op: returns 0.0 if insufficient data.
    """
    if fmp_coverage not in ("FULL", "PARTIAL"):
        return 0.0
    
    # Beat rate bonus/penalty (analyst-normalized execution quality)
    if beat_rate is None:
        beat_component = 0.0
    elif beat_rate >= 0.875:  # 7/8+ quarters
        beat_component = 2.0
    elif beat_rate >= 0.75:   # 6/8 quarters
        beat_component = 1.0
    elif beat_rate >= 0.625:  # 5/8 quarters
        beat_component = 0.0
    else:                     # < 5/8 quarters
        beat_component = -1.0
    
    # Thesis integrity component
    thesis_map = {
        "INTACT":        0.0,
        "QUESTIONABLE":  -0.5,
        "DETERIORATING": -3.0,
        "INSUFFICIENT_DATA": 0.0,
    }
    thesis_component = thesis_map.get(thesis, 0.0)
    
    # Fundamental consistency component
    consistency_map = {
        "CONSISTENT":   1.0,
        "MIXED":        0.0,
        "CONTRADICTORY": -1.5,
        "DATA_ANOMALY": -2.0,
        "INSUFFICIENT_DATA": 0.0,
    }
    consistency_component = consistency_map.get(consistency, 0.0)
    
    raw = beat_component + thesis_component + consistency_component
    return max(-5.0, min(3.0, round(raw, 2)))
```

### Application Point
Applied AFTER computing `CwDasBreakdown` raw score, BEFORE final capping at 0:

```python
raw_with_fundamental = raw + fundamental_modifier
score = round(max(0.0, raw_with_fundamental), 2)
```

### Weight Range
- Maximum bonus: **+3.0 points** (3% of max 103)
- Maximum penalty: **−5.0 points** (4.9% of max 103)
- Net max spread: **8 points**

---

## Expected Impact on Top-25

| Symbol | Current | Modifier | New | Rank Change |
|--------|---------|---------|-----|-------------|
| DELL | 99.3 | +3.0 | 102.3 | #1 → #1 |
| VRT | 94.7 | +3.0 | 97.7 | #2 → #2 |
| ARW | 93.8 | +3.0 | 96.8 | #3 → #3 |
| **PSX** | 93.4 | **−4.0** | **89.4** | **#4 → ~#11** |
| ATLC | 91.7 | +3.0 | 94.7 | #6 → #4 |
| LRCX | 91.5 | +3.0 | 94.5 | #7 → #5 |
| AVT | 91.9 | +0.5 | 92.4 | #5 → #6 |

The most material change is PSX dropping from #4 to ~#11 due to DETERIORATING thesis (−3.0) and low beat rate (71% → −1.0). This is the correct outcome — PSX has negative revenue growth and a weak fundamental profile at a moment when ESS consensus remains bullish (lag effect).

---

## Advisories

**Advisory 1: Beat rate sector calibration**  
Sectors with structurally low analyst accuracy (solar, biotech) should not receive beat_rate < 0.625 penalties. Apply modifier only when coverage = FULL. Consider a sector exclusion list for `beat_component = 0.0` override.

**Advisory 2: Historical validation prerequisite**  
Before implementing, validate that the modifier would have improved ranking quality in at least 6 historical portfolio analysis runs. The SIH replay system may be able to provide this. Phase 8.0B.1C-IMPL should include a backtest against prior runs.

**Advisory 3: Transparency requirement**  
The `fundamental_modifier` value must be added to `CwDasBreakdown` and displayed in the score breakdown grid. Operators must be able to see the modifier and its components. "Why SIH Likes It" should reference it.

**Advisory 4: Governance gate**  
This recommendation requires a separate implementation issue (ISSUE-07) with its own acceptance criteria, regression testing, and certification. DO NOT IMPLEMENT in this assessment phase.

---

## Final Answers

**Q1: Should fundamentals influence CW-DAS?**  
**YES — via a bounded conviction modifier**

**Q2: If yes, where?**  
Applied after the existing 7-component raw score, before final capping. Displayed as `fundamental_modifier` in the breakdown.

**Q3: By how much?**  
±0–5 points (max +3 bonus, max −5 penalty), bounded. ~3–5% of the practical score range.

**Q4: Does this strengthen or weaken CII?**  
**Strengthens CII.** Directly operationalizes "validates consensus against business fundamentals." Makes the validation layer actionable rather than decorative.

**Q5: What is the recommended next implementation issue?**  
**ISSUE-07: Fundamental Conviction Modifier — CW-DAS Enhancement**
