# Operator Fundamental Overlay Design
**Phase 8.0A.1 | UI/UX Design Specification for Fundamental Intelligence Layer**
**Generated:** 2026-06-02

---

## 1. Design Philosophy

This specification defines **informational-only** UI overlay elements for surfacing fundamental momentum intelligence to operators. These elements:

- **DO NOT modify SIH composite scores** or signal weights
- **DO NOT change signal rankings** or priority orderings
- **DO** provide operators with additional fundamental context at the point of decision
- **DO** flag potential divergences that warrant additional scrutiny
- **DO** quantify archetype quality differences within the same signal tier

**Core principle**: Operators retain full authority. FMI is advisory intelligence, not scoring input.

---

## 2. Proposed Overlay Elements

### Element 1: FMS Score Badge

**Display**: Numeric badge (0-100) with color coding
**Location**: Security detail page, portfolio view secondary column
**Color scheme**:
- 70–100: Green (A_ACCELERATING_COMPOUNDER quality)
- 50–69: Blue (B_RECOVERY_STORY / strong)
- 35–49: Yellow (C_STEADY_EXECUTOR / moderate)
- 20–34: Orange (D_CYCLICAL_REBOUND / declining)
- 0–19: Red (E/F — sentiment or divergence)
- N/A: Gray (G_INSUFFICIENT_DATA — shown as "No FMS Data")

**Example display**:
```
VRT    [FMS: 89 ●] A_ACCELERATING_COMPOUNDER
FIX    [FMS: 85 ●] A_ACCELERATING_COMPOUNDER
PSX    [FMS: 24 ●] ⚠ FUNDAMENTAL_DIVERGENCE
LYB    [FMS: 15 ●] ⚠ FUNDAMENTAL_DIVERGENCE
SHBI   [FMS: No Data] Community bank — insufficient
```

**Tooltip on hover**: Shows sub-component breakdown (RMS/EMS/ERS/EQS/VRS/GTS) with brief explanation of the primary driver of the score.

---

### Element 2: Revenue Acceleration Indicator

**Display**: Icon + text label
**Values**:
- `▲▲ ACCELERATING` (≥20% growth with YoY acceleration)
- `▲ GROWING` (5-20% growth)
- `→ STABLE` (-5% to +5%)
- `▼ DECLINING` (<-5%)
- `▼▼ DECLINING FAST` (<-15%)

**Data requirement**: Last 2-3 fiscal years of revenue data
**Example**:
```
VRT:  ▲▲ ACCELERATING (+29% TTM, +28% FY2025)
FIX:  ▲▲ ACCELERATING (+38% TTM, consecutive 5yr)
PSX:  ▼ DECLINING (-2.4% TTM, 3-year declining trend)
LYB:  ▼▼ DECLINING FAST (-9.4% TTM, -41% from peak)
```

---

### Element 3: EPS Trajectory

**Display**: Icon + text
**Values**:
- `▲▲ ACCELERATING` (EPS growth >50%, trend improving)
- `▲ RECOVERING` (EPS growth >20%, recovering from trough)
- `→ STABLE` (EPS growth ±20%)
- `▼ COMPRESSING` (EPS declining <-20%)
- `⊘ LOSS` (EPS negative or near-zero)

**Example**:
```
MU:    ▲▲ ACCELERATING (+416% TTM; from -$5.34 to $21.53)
ARW:   ▲ RECOVERING (+93% TTM; still 36% below prior peak)
DINO:  ▲ RECOVERING ($14.28 peak → $0.91 trough → $6.65 TTM)
CHRD:  ⊘ LOSS (EPS negative TTM)
```

---

### Element 4: FCF Quality Rating

**Display**: Text label
**Values**:
- `STRONG FCF` (FCF margin ≥15%, growing)
- `ADEQUATE FCF` (FCF margin 5-15%, stable or growing)
- `WEAK FCF` (FCF margin 1-5% or declining)
- `MINIMAL FCF` (FCF margin <1% or near-zero)
- `NEGATIVE FCF` (FCF < 0)

**Example**:
```
VRT:  STRONG FCF (21.0% margin, +$387M YoY growth)
ATLC: STRONG FCF (34.3% margin)
DVA:  ADEQUATE FCF (~12% margin, stable)
PSX:  MINIMAL FCF (0.09% margin — ⚠ flag)
LYB:  WEAK FCF (3.2% margin, declining)
```

---

### Element 5: Gross Margin Trend

**Display**: Text label + 3-year trend arrow
**Values**:
- `EXPANDING ▲` (gross margin improving YoY for 2+ years)
- `STABLE →` (gross margin ±2pp)
- `COMPRESSING ▼` (gross margin declining YoY for 2+ years)

**Example**:
```
VRT:  EXPANDING ▲ (28.4% → 37.2%; +8.8pp in 4 years)
FIX:  EXPANDING ▲ (consistent improvement)
TXN:  COMPRESSING ▼ (68% peak → 57.3% TTM; -10.7pp)
LYB:  COMPRESSING ▼ (22% peak → 9.2% TTM; -12.8pp)
```

---

### Element 6: Analyst Coverage Depth

**Display**: `[N analysts | CONSENSUS: direction]`
**Purpose**: Flag thin-coverage situations where SIH signals may have asymmetric advantage

**Coverage categories**:
- Deep: ≥15 analysts
- Moderate: 7-14 analysts
- Thin: 4-6 analysts (yellow flag — SIH advantage amplified)
- Very Thin: ≤3 analysts (orange flag)

**Example**:
```
ARW:  [4 analysts | CONSENSUS: Hold] ⚠ Thin coverage — signal advantage amplified
ATLC: [6 analysts | CONSENSUS: Strong Buy] ⚠ Thin coverage
VRT:  [22 analysts | CONSENSUS: Strong Buy] Deep coverage
MU:   [30 analysts | CONSENSUS: Buy] Deep coverage
```

---

### Element 7: PEG Ratio

**Display**: Numeric with interpretation
**Values**:
- < 0.5: `EXCEPTIONAL VALUE` (growth not priced in)
- 0.5-1.0: `ATTRACTIVE` (reasonable growth pricing)
- 1.0-2.0: `FAIR VALUE` (growth priced in)
- 2.0-3.0: `PREMIUM` (paying up for quality/growth)
- > 3.0: `HIGH PREMIUM` (requires execution to justify)

**Example**:
```
ATLC: PEG 0.14 → EXCEPTIONAL VALUE (PE 8.6x on +61% EPS growth)
FIX:  PEG 0.32 → ATTRACTIVE (PE 35x on ~100% EPS growth)
VRT:  PEG 0.62 → ATTRACTIVE (PE 47x on ~75% EPS growth)
MU:   PEG 0.22 → ATTRACTIVE (PE 15x on +416% EPS growth — cycle caution)
LYB:  PEG N/A → N/A (negative EPS)
```

---

### Element 8: Archetype Classification Badge

**Display**: Color-coded badge
**Archetypes**:
```
[A] ACCELERATING COMPOUNDER  → Dark green background, white text
[B] RECOVERY STORY           → Blue background, white text
[C] STEADY EXECUTOR          → Gray background, white text
[D] CYCLICAL REBOUND         → Orange background, white text
[E] SENTIMENT DRIVEN         → Yellow background, dark text
[F] FUNDAMENTAL DIVERGENCE   → Red background, white text
[G] INSUFFICIENT DATA        → Light gray, italic text
```

**Badge placement**: Near the symbol ticker on detail pages and export reports

---

### Element 9: Fundamental Momentum Alert (F_FUNDAMENTAL_DIVERGENCE)

**Trigger condition**: ESS = VERY_BULLISH or BULLISH AND FMS ≤ 30

**Display**: Red banner/flag
```
⚠ FUNDAMENTAL DIVERGENCE ALERT
Signals are bullish but FMS = 24 (F_FUNDAMENTAL_DIVERGENCE)
Revenue declining: -2.4% TTM
FCF margin critical: 0.09% TTM (from 5.25% FY2022)
Review fundamentals before position sizing.
[View FMS Detail] [Dismiss]
```

**Key design principle**: Alert is advisory only. It does NOT block any action or change any score. Operator can dismiss it.

**Alert population in top 100**: 6 symbols (PSX, LYB, CHRD, DINO, VLO, MPC at varying severity)

---

### Element 10: FMS Trend Indicator (Phase 8.0B future feature)

**Not available in Phase 8.0A.1** — requires monthly FMS tracking to compute trend
**Future design**: `FMS: 45 → 52 → 58 ▲ IMPROVING` or `FMS: 65 → 55 → 48 ▼ DECLINING`

**Purpose**: Most valuable overlay for early detection — a falling FMS on a high-signal symbol is the strongest early warning of a future divergence

---

## 3. Data Requirements Summary

| Element | Data Source | Refresh Frequency | Phase |
|---------|------------|------------------|-------|
| FMS Score | FMP API (Phase 8.0B) | Quarterly | 8.0B |
| Revenue Acceleration | FMP API | Quarterly | 8.0B |
| EPS Trajectory | FMP API | Quarterly | 8.0B |
| FCF Quality | FMP API | Quarterly | 8.0B |
| Gross Margin Trend | FMP API | Quarterly | 8.0B |
| Analyst Coverage | FMP API or manual | Monthly | Now (manual) |
| PEG Ratio | FMP API | Weekly | 8.0B |
| Archetype Badge | Derived from FMS | Quarterly | 8.0B |
| Divergence Alert | Derived from FMS + ESS | Real-time (signal trigger) | 8.0B |
| FMS Trend | Requires historical FMS | Monthly | 8.1 |

---

## 4. Implementation Priority (Phased)

### Phase 8.0A.1 (Current — Manual, Top 30 Symbols)
- Elements 1, 8, 9 manually populated for 28 characterized symbols
- Display as static annotations in export reports
- No UI integration — analysis layer only

### Phase 8.0B (FMP API — Full Coverage)
- Elements 1–9 automated for all symbols with FMP coverage
- Estimated 80-90% of the 2,586-symbol universe
- FMS computed programmatically
- UI badges/indicators integrated into operator dashboard

### Phase 8.1 (Trend Tracking)
- Element 10: FMS Trend with 3-month and 6-month trend lines
- Historical FMS database built up over Phase 8.0B tracking period
- Statistical validation of FMS predictive power begins

---

## 5. Design Principles Summary

1. **No score contamination**: FMI overlays never modify signal scores or rankings
2. **Operator authority preserved**: All FMI elements are dismissible and advisory
3. **Transparency**: Every FMS score must be explainable (sub-component breakdown available on drill-down)
4. **Data honesty**: G_INSUFFICIENT_DATA displayed as such — no imputed scores
5. **Alert calibration**: Divergence alerts are rare by design (6/100 in this study) — not alert fatigue
6. **Incremental not disruptive**: FMI adds a layer; it doesn't replace the proven SIH signal system
