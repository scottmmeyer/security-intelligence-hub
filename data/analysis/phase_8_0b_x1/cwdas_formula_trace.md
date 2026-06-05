# CW-DAS Formula Trace — Phase 8.0B.X.4

## Formula

```
CW-DAS = Signal(0–30) + Replay(0–20) + Conviction(0–35) + Sizing(0–8) + Momentum(0–10)
         − Redundancy_Penalty(0–15) − Concentration_Penalty(0–20)

Max theoretical: 103.0
Practical max: ~100.0 (full signal + CCL conviction + replay + momentum, no penalties)
```

**Source:** `src/portfolio/deployment_queue.py` → `compute_cw_das()`

---

## Component Trace

### 1. Signal (0–30)
```
signal_c = min(composite_score / 5.0 × 30.0, 30.0)
```
- **Input:** `composite_score` (0.0–5.0) — weighted blend of ESS + Zacks + Danelfin
- **Weight:** 30% of pre-penalty max
- **Drift sensitivity:** NONE — reads signal quality only, not portfolio allocation

### 2. Replay (0–20)
```
replay_c = 20.0 if replay_supported else 0.0
```
- **Input:** `replay_supported` (boolean) — whether the symbol appeared in a Replay top-N selection
- **Weight:** Binary gate, 20% of max
- **Drift sensitivity:** NONE

### 3. Conviction (0–35)
```
conviction_c = 35.0  if tier == "CORE_CONVICTION_LEADER"
             = 28.0  if tier == "HIGH_CONVICTION_ANCHOR"
             = 10.0  otherwise
```
- **Input:** `narrative_tier` from STI (HoldingStrategicProfile)
- **Weight:** 34% of max (CCL) / 27% (HCA)
- **Drift sensitivity:** NONE — tier is determined by composite signal quality, not portfolio allocation

### 4. Sizing (0–8)
```
headroom = max(0.0, 1.0 − pct / WARN_POSITION_PCT)   # WARN_POSITION_PCT = 6.0
sizing_c = 8.0 × headroom
```
- **Input:** `pct` — current position weight as % of total portfolio
- **Weight:** 7.8% of max at 0% position; 0 at ≥6%
- **Drift sensitivity:** PARTIAL — reflects the individual position's weight vs. its personal size cap (6%). Does NOT compare position to node-level allocation target. A 2% position in US.SMALL is treated identically regardless of whether US.SMALL is 5% OW or 5% UW.

### 5. Momentum (0–10)
```
both ESS and signal BULLISH     → 10.0
one BULLISH, one not            → 7.5
ESS neutral (empty/NEUTRAL)     → 4.0
any BEARISH present             → 0.0
```
- **Input:** `ess_text`, `signal_direction`
- **Weight:** 9.7% of max
- **Drift sensitivity:** NONE

### 6. Redundancy Penalty (0–15)
```
redundancy_pen = 15.0 if in_ow_node else 0.0
```
Where `in_ow_node = True` iff:
- The holding's allocation node (`EQUITIES.{geography}.{market_cap_bucket}`) is contained in or contains a node that has `drift_direction == "OVERWEIGHT"` AND `severity in ("HIGH", "MODERATE")`

- **Input:** `alignment_results` (AllocationAlignmentResult list) — derived from portfolio vs. strategic target comparison
- **Weight:** Binary flat-15 deduction
- **Drift sensitivity:** YES — but only at HIGH/MODERATE severity threshold

### 7. Concentration Penalty (0–20)
```
conc_pen = 0.0                          if pct ≤ 6.0%
         = min((pct − 6.0) × 4.0, 20.0)  if pct > 6.0%
```
- **Input:** `pct` — individual position weight
- **Drift sensitivity:** NONE — guards against single-position concentration, not node-level drift

---

## Eligibility Gates (Pre-Score)

Before scoring, candidates must pass ALL of:
- `signal_direction == "BULLISH"`
- `replay_supported == True`
- `strategic_classification == "HIGH_CONVICTION_RETAIN"`
- `narrative_tier in {CCL, HCA}`
- `is_cash_equivalent == False`
- `security_type NOT in {ETF, FUND, MUTUAL_FUND}`

---

## Allocation Drift Handling: Summary

| Drift Type | Handling in CW-DAS | Threshold |
|------------|-------------------|-----------|
| Node OVERWEIGHT (HIGH/MODERATE) | −15 redundancy penalty | Severity ≥ MODERATE |
| Node OVERWEIGHT (LOW) | **NO penalty applied** | Below threshold |
| Node UNDERWEIGHT | **No bonus applied** | Not modeled |
| Individual position size vs. node target | **Not modeled** | N/A |
| Drift magnitude (e.g., +3.3% vs +5.3%) | **Not modeled** | Binary: MODERATE or not |

The redundancy penalty is a **binary gate** triggered by severity classification, not by drift magnitude.
A +3.0% LOW OW node receives identical treatment (no penalty) as a 0% ON_TARGET node.
A +5.26% MODERATE node receives the same flat −15 as a +8% HIGH node.
