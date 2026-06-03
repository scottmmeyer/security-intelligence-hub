# Signal Confidence Model Design
**Phase 7.6C — Signal Authority and Confidence Framework**
**Run Reference:** PAR-20260601-9CFD7C63
**Version:** 1.0 (Design Specification — Not Yet Implemented)
**Date:** 2026-06-01

---

## Purpose

The Signal Confidence Score (SCS) is a proposed per-symbol, per-run metric that quantifies how confident the system should be in its composite signal direction for a given holding. The SCS supplements the existing UCF labels and conflict flags by providing a continuous confidence measure that can be used for position sizing calibration and deployment priority adjustment.

This document specifies the design. The SCS is **not yet implemented** in the production codebase.

---

## Design Rationale

The current system treats all composite_score values with equal confidence. A composite of 4.5 based on VERY_BULLISH ESS + Zacks=5.0 + Danelfin=5.0 (full three-signal agreement, same-day freshness) is scored identically to a composite of 4.5 based on VERY_BULLISH ESS alone with Zacks and Danelfin missing. The SCS distinguishes these cases.

---

## Formula

```
SCS(symbol) = (
    (freshness_score   × 0.20) +
    (coverage_score    × 0.15) +
    (agreement_score   × 0.35) +
    (replay_depth_score × 0.20) +
    (valuation_score   × 0.10)
) × 100
```

Total range: 0–100

---

## Component Specifications

### 1. Freshness Score (weight: 0.20)

Measures how current the composite signal inputs are.

```
freshness_score = min(1.0, max(0.0,
    (ess_days_stale == 0) × 1.0 ×  0.60 +   # ESS freshness (60% of component)
    max(0.0, 1.0 - zacks_days_stale / 14) × 0.25 +  # Zacks (25%)
    max(0.0, 1.0 - danelfin_days_stale / 30) × 0.15  # Danelfin (15%)
))
```

**Reference values (PAR-20260601-9CFD7C63):**
- ESS: 0 days stale → ESS sub-score = 1.0
- Zacks: ~2 days stale → sub-score = 1 - 2/14 = 0.857
- Danelfin: ~2 days stale → sub-score = 1 - 2/30 = 0.933
- Composite freshness_score ≈ 0.60 × 1.0 + 0.25 × 0.857 + 0.15 × 0.933 = 0.953

---

### 2. Coverage Score (weight: 0.15)

Measures whether all expected signals are present for a given symbol.

```
coverage_score = (
    ess_present × 0.55 +
    zacks_present × 0.30 +
    danelfin_present × 0.15
)
```

Where `signal_present = 1.0 if signal value is non-null, 0.0 otherwise`.

**Reference values:**
- All three signals present: coverage_score = 1.0 (most portfolio holdings)
- ESS missing: coverage_score = 0.45 (severe)
- Danelfin missing (e.g., SANM): coverage_score = 0.85

---

### 3. Agreement Score (weight: 0.35)

Measures directional consensus across available signals. This is the highest-weighted component because signal agreement is the strongest indicator of confidence.

**Direction collapse:**
- ESS: VERY_BULLISH/BULLISH → BULLISH; BEARISH/VERY_BEARISH → BEARISH; NEUTRAL → NEUTRAL
- Zacks: ≥4.0 → BULLISH; ≤2.0 → BEARISH; else NEUTRAL
- Danelfin: ≥4.0 → BULLISH; ≤2.0 → BEARISH; else NEUTRAL
- Yahoo ABR: ≤2.0 → BULLISH; ≥3.5 → BEARISH; else NEUTRAL

**Agreement scoring:**
```
known_signals = [d for d in [ess_dir, zacks_dir, danelfin_dir, yahoo_dir] if d != 'N/A']
majority_dir = mode(known_signals)  # Most common direction
agreeing = count(d for d in known_signals if d == majority_dir)
total_known = len(known_signals)
agreement_score = agreeing / total_known  # 0.0 to 1.0
```

**Reference examples:**
| Symbol | Directions | Agreeing | Agreement Score |
|---|---|---|---|
| ARW | BULL, BULL, BULL, N/A | 3/3 | 1.000 |
| VRT | BULL, BULL, BULL, BULL | 4/4 | 1.000 |
| AEIS | BEAR, BULL, BULL, BULL | 3/4 | 0.750 |
| TSM | BULL, NEUT, BULL, BULL | 3/4 | 0.750 |
| KGC | BEAR, NEUT, BULL, BULL | 2/4 | 0.500 |
| PRIM | BEAR, BEAR, BULL, BULL | 2/4 | 0.500 |

---

### 4. Replay Depth Score (weight: 0.20)

Measures the quality of replay evidence for this holding.

**Current implementation (binary):**
```
replay_depth_score = 1.0 if replay_supported == True else 0.0
```

**Future enhanced implementation (when per-symbol replay counts become available):**
```
replay_depth_score = min(1.0, replay_appearance_count / 12)
# 12 = one appearance per month over the 365-day window; 12+ = full confidence
```

**Reference values (PAR-20260601-9CFD7C63):** All deployment queue holdings have replay_supported=True → replay_depth_score = 1.0 for all. TRIM_WATCH and TACTICAL_GROWTH holdings vary.

---

### 5. Valuation Score (weight: 0.10)

Measures directional alignment between signal direction and analyst price target upside (Yahoo ABR upside_pct).

```
if yahoo_upside_pct is null:
    valuation_score = 0.5  # Neutral (no data)
elif direction == 'BULLISH' and yahoo_upside_pct > +10%:
    valuation_score = 1.0  # Signal and valuation agree
elif direction == 'BEARISH' and yahoo_upside_pct < -10%:
    valuation_score = 1.0  # Signal and valuation agree
elif direction == 'BULLISH' and yahoo_upside_pct < -10%:
    valuation_score = 0.0  # Overvalued per analysts despite bullish signal
elif direction == 'BEARISH' and yahoo_upside_pct > +10%:
    valuation_score = 0.0  # Undervalued per analysts despite bearish signal
else:
    valuation_score = 0.5  # Ambiguous
```

**Reference examples:**
| Symbol | Direction | Yahoo Upside | Valuation Score |
|---|---|---|---|
| ATLC | BULLISH | +30.3% | 1.0 |
| CAH | BULLISH | +22.6% | 1.0 |
| CIEN | BULLISH | -20.1% | 0.0 (conflict) |
| DELL | BULLISH | -17.4% | 0.0 (conflict) |
| VRT | BULLISH | +13.4% | 1.0 |
| TSLA | BEARISH | -1.3% | 0.5 (ambiguous) |

---

## Sample SCS Calculations (PAR-20260601-9CFD7C63)

Using reference values above, approximate SCS:

| Symbol | Fresh | Coverage | Agreement | Replay | Valuation | SCS |
|---|---|---|---|---|---|---|
| ARW | 0.953 | 1.0 | 1.00 | 1.0 | 1.0 | **95.3** |
| VRT | 0.953 | 1.0 | 1.00 | 1.0 | 1.0 | **95.3** |
| ATLC | 0.953 | 1.0 | 1.00 | 1.0 | 1.0 | **95.3** |
| CIEN | 0.953 | 1.0 | 1.00 | 1.0 | 0.0 | **88.3** (valuation risk) |
| DELL | 0.953 | 1.0 | 1.00 | 1.0 | 0.0 | **88.3** (valuation risk) |
| TSM | 0.953 | 1.0 | 0.75 | 1.0 | 1.0 | **88.0** |
| AEIS | 0.953 | 1.0 | 0.75 | 1.0 | 1.0 | **88.0** (note: ESS disagrees with majority) |
| KGC | 0.953 | 1.0 | 0.50 | 0.0 | 1.0 | **54.3** |
| PRIM | 0.953 | 1.0 | 0.50 | 0.0 | 1.0 | **54.3** |

**Note:** AEIS scores 88.0 in SCS because SCS measures majority-signal confidence, not ESS authority. Operators should cross-reference SCS with conflict flags: AEIS has high SCS (majority bullish) BUT has `COMPOSITE_ESS_DIVERGE` flag — the combination means high confidence that non-ESS signals are bullish, but the dominant signal disagrees.

---

## Integration with CW-DAS (Proposed)

The SCS is not intended to replace CW-DAS but to provide a confidence overlay:

```
deployment_confidence = SCS(symbol) / 100
adjusted_allocation = base_allocation × (0.70 + 0.30 × deployment_confidence)
```

This would reduce allocation by up to 30% for low-confidence signals (SCS=0 → 70% of base; SCS=100 → 100% of base). Implementation requires system change.

---

## Limitations

1. **Agreement score uses unweighted majority** — ESS's 61.1% composite weight is not reflected in the agreement_score. AEIS gets agreement_score=0.75 despite ESS (the dominant signal) being the dissenter. Operators should not interpret high SCS as overriding ESS authority.

2. **Yahoo ABR 10-day staleness** — valuation_score uses stale analyst data; during volatile periods this can be misleading.

3. **Replay depth is binary in v1** — full replay confidence model requires per-symbol appearance counts not yet surfaced in the pipeline.

4. **SCS is directionally agnostic** — it measures confidence in the majority direction, which may be bullish or bearish. High SCS on a BEARISH majority is high confidence to trim/avoid, not to buy.
