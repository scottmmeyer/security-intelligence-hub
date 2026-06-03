# Fundamental Momentum Score (FMS): Design Specification
**Phase 8.0A | Q5: How should SIH quantify fundamental momentum alongside signal scores?**

Generated: 2026-06-02 | Status: DESIGN ONLY — DO NOT IMPLEMENT

---

## Purpose

The Fundamental Momentum Score (FMS) is a proposed composite score (0–100) measuring the quality and direction of a company's business performance as evidenced by financial data. It is designed to **complement** the existing SIH composite signal score — not replace it.

**Design Goals:**
1. Capture accelerating business performance, not just static metrics
2. Be automatable via a paid data API (FMP, Finnhub, or LSEG extension)
3. Be interpretable to an operator — no black-box scoring
4. Distinguish between growth momentum (VRT-type) and recovery momentum (ARW-type)
5. Penalize signals where fundamentals are deteriorating (PSX FCF collapse)

**Non-Goals for This Phase:**
- Do NOT assign FMS scores to production universe
- Do NOT integrate into CW-DAS or UCF
- Do NOT change any SIH signal scoring logic

---

## FMS Component Design

### Component 1: Revenue Momentum Score (RMS)
**Weight: 25 points (0–25)**

Measures whether revenue growth is accelerating, stable, or decelerating.

**Inputs required:**
- Revenue for past 4 fiscal years (or TTM)
- Forward revenue estimate (FY+1)

**Scoring Logic:**
```
Base rate = trailing 12-month revenue growth YoY (%)

Acceleration bonus = (TTM growth - prior year growth)
  +5 pts if acceleration > 5 percentage points
  +3 pts if acceleration 2–5 percentage points
   0 pts if flat ±2 percentage points
  -3 pts if deceleration 2–5 percentage points
  -5 pts if deceleration > 5 percentage points

Forward uplift = (FY+1E revenue growth vs TTM growth)
  +2 pts if FY+1E growth > TTM growth (analysts expect acceleration)
   0 pts if flat ±3%
  -2 pts if FY+1E growth < TTM growth (analysts expect deceleration)

Absolute growth bands:
  >30% growth  → 15–20 base pts
  20–30%       → 12–15 base pts
  10–20%       → 8–12 base pts
  5–10%        → 4–8 base pts
  0–5%         → 2–4 base pts
  Negative     → 0–2 base pts

RMS = base + acceleration bonus + forward uplift (capped 0–25)
```

**Calibration examples:**
- VRT: Base ~15 (29% TTM), acceleration +5 (29%→35% FY2026E), forward +2 → **RMS ~22/25**
- SNX: Base ~9 (10.4%), stable +0, flat +0 → **RMS ~9/25**
- PSX: Base ~0 (negative TTM), deceleration -3, forward +2 (recovery) → **RMS ~3/25**
- ARW: Base ~12 (20.5% TTM), acceleration +3 (20%→26% FY2026E), forward -2 (FY2027E +4.7%) → **RMS ~13/25**

---

### Component 2: EPS Momentum Score (EMS)
**Weight: 20 points (0–20)**

Measures EPS growth trajectory including forward estimates.

**Inputs required:**
- EPS (diluted) for past 4 years
- Forward EPS estimate (FY+1, FY+2)
- 3-year forward EPS CAGR (if available)

**Scoring Logic:**
```
TTM EPS Growth bands:
  >100%     → 16–20 pts
  50–100%   → 12–16 pts
  25–50%    → 8–12 pts
  10–25%    → 4–8 pts
  0–10%     → 2–4 pts
  Negative  → 0–2 pts

Sustainability adjustment:
  +2 pts if FY+2E EPS growth > 20% (sustained multi-year)
  +1 pt if FY+2E EPS growth 10–20%
   0 pts if FY+2E EPS growth 0–10%
  -2 pts if FY+2E EPS growth < 0 (normalization expected)

Revision direction (if available):
  +2 pts if estimate revised upward in past 30 days
  -2 pts if estimate revised downward in past 30 days

EMS = base + sustainability + revision (capped 0–20)
```

**Calibration examples:**
- VRT: Base 16 (131% TTM), +2 (FY2027E +40%), +2 (recent upgrades) → **EMS ~20/20**
- ARW: Base 14 (93% TTM), -2 (FY2027E +2.9%), +1 (BofA upgrade May 2026) → **EMS ~13/20**
- ATLC: Base 16 (73% TTM), +2 (FY2027E +37%), 0 → **EMS ~18/20**
- PSX: Base 2 (-6% TTM), +2 (FY2026E recovery), -2 (FY2027E decline) → **EMS ~4/20**
- SNX: Base 10 (50% TTM), +1 (FY2027E +10%), 0 → **EMS ~11/20**

---

### Component 3: Estimate Revision Score (ERS)
**Weight: 20 points (0–20)**

Measures the direction and volume of recent analyst estimate changes.

**Inputs required:**
- Count of upward vs downward EPS revisions in past 30 days
- Count of upward vs downward EPS revisions in past 90 days
- Whether price target was raised or lowered in past 30 days

**Scoring Logic:**
```
30-day revision ratio = (ups - downs) / (ups + downs)  [-1.0 to +1.0]
  Ratio > 0.8   → 9–10 pts
  Ratio 0.5–0.8 → 7–9 pts
  Ratio 0.2–0.5 → 5–7 pts
  Ratio -0.2 to 0.2 → 3–5 pts (mixed/neutral)
  Ratio -0.5 to -0.2 → 1–3 pts
  Ratio < -0.5  → 0–1 pts

90-day confirmation bonus:
  +2 pts if 90-day ratio also > 0.5 (sustained revisions up)
  -2 pts if 90-day ratio also < -0.3 (sustained revisions down)

PT raise bonus:
  +2 pts if avg analyst PT raised in past 30 days
  -2 pts if avg analyst PT lowered in past 30 days

Note: Zacks Rank is a direct proxy for this component. Where Zacks Rank = 1 (Strong Buy), 
ERS should receive a strong score. Zacks Rank 1 = top 5% of revision momentum.

ERS = base + 90-day + PT (capped 0–20)
```

**Note**: This component is the primary reason Zacks Rank already partially captures FMI. The ERS makes the revision signal **explicit** and auditable rather than embedded in a proprietary black-box rank.

---

### Component 4: Earnings Quality Score (EQS)
**Weight: 15 points (0–15)**

Measures the quality of reported earnings via FCF conversion and margin health.

**Inputs required:**
- FCF / Net Income ratio (cash conversion)
- FCF margin trend (expanding vs contracting)
- Gross margin trend

**Scoring Logic:**
```
FCF/Net Income ratio:
  > 1.2 (FCF exceeds net income)   → 5–6 pts
  0.8–1.2                          → 4–5 pts
  0.5–0.8                          → 2–4 pts
  < 0.5 (weak cash conversion)     → 0–2 pts
  Negative FCF                     → 0 pts

FCF Margin trend (YoY):
  +3 pts if expanding > 3 percentage points
  +1 pt if expanding 1–3 percentage points
   0 pts if flat ±1 percentage point
  -2 pts if contracting > 3 percentage points

Gross Margin trend (YoY):
  +3 pts if expanding > 1 percentage point
   0 pts if flat ±0.5 percentage point
  -2 pts if contracting > 1 percentage point

EQS = FCF conversion + FCF trend + Gross margin (capped 0–15)
```

**Calibration examples:**
- VRT: FCF/NI ~1.46 → 6pts, FCF margin expanding → +3pts, Gross expanding → +3pts → **EQS ~15/15** (near max)
- PSX: FCF $119M on $4.1B net income → FCF/NI = 0.03 → 0pts, FCF contracting sharply → -2pts → **EQS ~1/15**
- ATLC: FCF $790M on NI $125M → FCF/NI >> 1 due to accrual differences (financial services nuance) → **EQS ~12/15** (with financial services adjustment)

---

### Component 5: Valuation Reasonableness Score (VRS)
**Weight: 10 points (0–10)**

Measures whether current valuation is supported by growth (PEG-based assessment).

**Inputs required:**
- Forward PE (FY+1E)
- 3-year EPS CAGR estimate
- EV/EBITDA (optional supplement)

**Scoring Logic:**
```
PEG = Forward PE / EPS Growth Rate (3-year forward CAGR)

PEG bands:
  PEG < 0.5              → 9–10 pts (deeply undervalued vs growth)
  PEG 0.5–1.0            → 7–9 pts (attractive)
  PEG 1.0–1.5            → 5–7 pts (fair to slightly expensive)
  PEG 1.5–2.5            → 3–5 pts (premium, must execute)
  PEG > 2.5              → 0–2 pts (expensive vs growth)
  No/negative earnings   → 2 pts (neutral — no penalty for early-stage)

VRS = PEG band score (capped 0–10)
```

**Calibration examples:**
- VRT: Forward PE 47.4 / EPS CAGR 46% → PEG 1.03 → **VRS ~6/10**
- ARW: Forward PE 12.4 / EPS CAGR ~30% (est.) → PEG 0.41 → **VRS ~10/10** (deeply undervalued vs growth)
- ATLC: Forward PE 8.64 / EPS CAGR ~40% → PEG 0.22 → **VRS ~10/10**
- PSX: Forward PE 10.53 / EPS CAGR ~0% (declining FY2027) → PEG N/A → **VRS ~4/10**
- SNX: Forward PE 16.06 / EPS CAGR 20%est → PEG 0.80 → **VRS ~8/10**

---

### Component 6: Guidance Trend Score (GTS)
**Weight: 10 points (0–10)**

Measures company-issued guidance direction (upward, in-line, or lowered).

**Inputs required:**
- Most recent earnings guidance: raised, maintained, lowered
- Earnings beat/miss rate (trailing 4 quarters)

**Scoring Logic:**
```
Guidance direction:
  Raised guidance         → 6–8 pts
  Maintained guidance     → 4–6 pts
  Lowered guidance        → 0–3 pts
  No guidance provided    → 4 pts (neutral)

Beat rate adjustment (trailing 4Q):
  4/4 beats     → +2 pts
  3/4 beats     → +1 pt
  2/4 beats     →  0 pts
  ≤1/4 beats    → -2 pts

GTS = guidance + beat rate (capped 0–10)
```

**Note**: Guidance trend is the hardest component to automate. Requires either:
- Manual operator input at earnings time
- NLP parsing of 8-K earnings releases (complex but feasible)
- A data provider with structured guidance tracking (FMP has this)

For initial deployment, GTS can default to **5/10 (neutral)** until a guidance tracking source is integrated.

---

## Full FMS Score Assembly

**FMS (0–100) = RMS (25) + EMS (20) + ERS (20) + EQS (15) + VRS (10) + GTS (10)**

### Theoretical Scores for Operator Symbols

| Symbol | RMS/25 | EMS/20 | ERS/20 | EQS/15 | VRS/10 | GTS/10 | FMS/100 |
|--------|--------|--------|--------|--------|--------|--------|---------|
| VRT | 22 | 20 | 18 | 15 | 6 | 8 | **89** |
| ARW | 13 | 13 | 14 | 8 | 10 | 6 | **64** |
| SNX | 9 | 11 | 12 | 10 | 8 | 7 | **57** |
| ATLC | 18 | 18 | 16 | 12 | 10 | 7 | **81** |
| PSX | 3 | 4 | 8 | 1 | 4 | 4 | **24** |

*Note: These are analytical estimates based on Phase 8.0A research data, not computed from a scoring engine.*

### FMS Interpretation Bands

| FMS Range | Interpretation | Suggested Action |
|-----------|---------------|-----------------|
| 80–100 | Strong fundamental momentum — fundamentals confirming signals | Confidence booster for signal leaders |
| 60–79 | Solid fundamentals — generally positive but some caution areas | Neutral — no score adjustment |
| 40–59 | Mixed fundamentals — signals merit scrutiny | Flag for operator review |
| 20–39 | Weak fundamentals — signals may be running ahead of business | Caution flag |
| 0–19 | Deteriorating fundamentals — signals at high divergence risk | Override warning |

---

## Data Requirements Summary

| Component | Source | Cadence | Cost |
|-----------|--------|---------|------|
| RMS | FMP or Yahoo Finance | Quarterly update | $19+/mo or free |
| EMS | FMP or Yahoo Finance | Quarterly update | $19+/mo or free |
| ERS | FMP Premium or Finnhub | Daily/weekly | $29+/mo |
| EQS | SEC EDGAR XBRL or FMP | Quarterly update | Free–$19/mo |
| VRS | FMP or Yahoo Finance (calculated) | Daily price × quarterly EPS | $19+/mo or free |
| GTS | FMP or manual operator input | Quarterly at earnings | $19+/mo |

**Minimum viable FMS (ERS defaults neutral): ~$0–19/month**
**Full FMS with revision tracking: ~$19–29/month (FMP or Finnhub combination)**

---

## Integration Roadmap

| Phase | FMS Role | Trigger |
|-------|----------|---------|
| **Phase 8.0A (Now)** | Theoretical design only | Complete — this document |
| **Phase 8.0B** | Operator display overlay | FMP API integration; cover top 200 signals by composite score |
| **Phase 8.0C** | UCF weighting factor (10–15% weight) | When FMS covers 80%+ of analytical universe with daily updates |
| **Phase 8.0D** | CW-DAS factor (advanced) | After 6+ months of FMS validation vs signal performance |
