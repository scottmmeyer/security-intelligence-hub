# ETF-CONVICTION-01: ETF Conviction Trace

**Date:** 2026-06-10  
**PAR:** PAR-20260610-DCF0E31F  
**Scope:** Classification trace for VOO, FXAIX, VB, VO, VEA, VWO, BND, BNDX, DODFX, FIGFX, FMCSX, FCPGX, FBTC, FETH, FSOL

---

## Part 1 — Classification Trace: All ETF/Fund Vehicles

### Overlay State (from security_overlays.csv)

| Symbol | Opp. Flag | ESS | Signal Direction | Replay | Score | Portfolio % | Execution State |
|---|---|---|---|---|---|---|---|
| VB | HOLD | — | UNKNOWN | False | — | 3.77% | EXECUTABLE |
| VOO | HOLD | — | UNKNOWN | False | — | 3.65% | EXECUTABLE |
| DODFX | HOLD | — | UNKNOWN | False | — | 3.22% | EXECUTABLE |
| VO | HOLD | — | UNKNOWN | False | — | 1.84% | EXECUTABLE |
| FXAIX | HOLD | — | UNKNOWN | False | — | 1.33% | EXECUTABLE |
| BNDX | HOLD | — | UNKNOWN | False | — | 0.78% | EXECUTABLE |
| VEA | HOLD | — | UNKNOWN | False | — | 0.75% | EXECUTABLE |
| BND | HOLD | — | UNKNOWN | False | — | 0.71% | EXECUTABLE |
| VWO | HOLD | — | UNKNOWN | False | — | 0.63% | EXECUTABLE |
| FBTC | HOLD | — | UNKNOWN | False | — | 0.38% | EXECUTABLE |
| FETH | HOLD | — | UNKNOWN | False | — | 0.21% | EXECUTABLE |
| FMCSX | HOLD | — | UNKNOWN | False | — | 0.16% | EXECUTABLE |
| FCPGX | HOLD | — | UNKNOWN | False | — | 0.04% | EXECUTABLE |
| FSOL | HOLD | — | UNKNOWN | False | — | 0.02% | EXECUTABLE |

**Note:** FIGFX not found in overlays for this PAR (not held or excluded).

### Why ALL ETFs Have Empty ESS and UNKNOWN Signal

ETFs are NOT scored by the SIH analytical pipeline (Zacks, Danelfin, Yahoo). The `analytical_universe.csv` contains only directly-scored equity securities. ETFs appear in `_ETF_OVERRIDES` in `enrichment.py` for classification purposes (asset_class, geography, market_cap_bucket) but receive NO:
- `composite_score` (ESS)
- `ess_score_text`
- `signal_direction`
- `replay_supported`
- `zacks_rating`
- `danelfin_score`

This is structurally by design: ESS measures individual equity signal strength, which is not applicable to broad passive vehicles.

### CW-DAS Eligibility

| Symbol | DQ Eligible? | Blocking Gate |
|---|---|---|
| All ETFs above | **No** | `signal_direction != "BULLISH"` → `_is_eligible()` returns False |

Source: `src/portfolio/deployment_queue.py` line 413:
```python
if (overlay.signal_direction or "").upper() != "BULLISH":
    return False
```

ETFs have `signal_direction = "UNKNOWN"` because they have no ESS coverage. This gate is a hard architectural exclusion.

A secondary gate also fails:
```python
if profile.strategic_classification != "HIGH_CONVICTION_RETAIN":
    return False
```

ETFs receive `strategic_classification = "TACTICAL_GROWTH"` because they lack BULLISH signal + replay evidence.

### Strategic Profile Classification (from drilldown data)

| Symbol | strategic_classification | trim_priority_score | strategic_importance | exposure_origin |
|---|---|---|---|---|
| VOO | TACTICAL_GROWTH | 40.1 | MEDIUM | ETF_INHERITED |
| DODFX | TACTICAL_GROWTH | 40.0 | MEDIUM | ETF_INHERITED |
| VO | TACTICAL_GROWTH | 27.8 | MEDIUM | ETF_INHERITED |

**Root cause detail:** `strategic_importance = MEDIUM` because `strategic_role` is **empty** on ETF holdings (not set by enrichment pipeline). `_ROLE_IMPORTANCE` in `trim_intelligence.py` maps `CORE_BROAD_US → CRITICAL` for VOO — but VOO never receives this role because `_ETF_OVERRIDES` in `enrichment.py` does not set `strategic_role`. The role is only assigned via the `analytical_universe.csv` → `exposure_decomposition.py` → `strategic_role` field path, which ETFs bypass.

### CRA Categorization (from build_capital_sources)

| Symbol | CRA Category | Priority | Est. Proceeds | Sizing | Policy |
|---|---|---|---|---|---|
| VB | LOW_CONVICTION_REDUCTION | MODERATE | $4,370 | 25% | — |
| VOO | LOW_CONVICTION_REDUCTION | MODERATE | $4,236 | 25% | — |
| VO | LOW_CONVICTION_REDUCTION | LOW | $2,128 | 25% | — |
| FXAIX | LOW_CONVICTION_REDUCTION | LOW | $1,537 | 25% | — |
| DODFX | OVERWEIGHT_REDUCTION | LOW | $3,728 | 25% | SELL_LAST |
| VEA | OVERWEIGHT_REDUCTION | LOW | $873 | 25% | — |
| BNDX | TAX_AWARE_EXIT | MODERATE | $3,599 | 100% | — |
| BND | TAX_AWARE_EXIT | MODERATE | $3,284 | 100% | — |
| VWO | TAX_AWARE_EXIT | MODERATE | $2,922 | 100% | — |
| FBTC | TAX_AWARE_EXIT | MODERATE | $1,757 | 100% | — |
| FETH | TAX_AWARE_EXIT | MODERATE | $959 | 100% | — |
| FSOL | TAX_AWARE_EXIT (suppressed) | MODERATE | $77 | 100% | — |

### FVI Tier Assignment

| Symbol | FVI Tier | Vehicle Quality Assessment |
|---|---|---|
| VOO | ELITE | Best-in-class passive US equity vehicle |
| VB | ELITE | Best-in-class US small cap vehicle |
| VO | ELITE | Best-in-class US mid cap vehicle |
| VEA | ELITE | Best-in-class international developed vehicle |
| FXAIX | ELITE | Best-in-class US large cap passive vehicle |
| BNDX | ELITE | Best-in-class international bond vehicle |
| BND | ELITE | Best-in-class US bond vehicle |
| VWO | ELITE | Best-in-class emerging markets vehicle |
| DODFX | HIGH | High quality actively managed international fund |
| FBTC | HIGH | Quality Bitcoin ETF vehicle |
| FETH | HIGH | Quality Ethereum ETF vehicle |
| FMCSX | MEDIUM | Adequate US mid cap fund |
| FCPGX | MEDIUM | Adequate US small cap growth fund |
| FSOL | LOW | Lower quality Solana fund |

### PAP Categorization

ETFs appear in PAP Cat 3 (Allocation Reduction) when they are in overweight allocation nodes, and in Cat 4 (Funding Sources) as low-composite candidates. They do NOT appear in Cat 1 (Signal Deterioration) because their ESS is empty and signal is UNKNOWN — the filter `flag == "TRIM"` or `ess == "VERY_BEARISH"` doesn't trigger.

---

## Part 2 — Root Cause: Why VOO is "Low Conviction"

### The Five-Gate Trigger

`LOW_CONVICTION_REDUCTION` in `capital_source_builder.py` (line 558) fires when ALL five conditions are met:

| Gate | Rule | VOO Value | Pass? |
|---|---|---|---|
| 1 | `opportunity_flag == "HOLD"` | HOLD | ✓ |
| 2 | Not already in higher-priority category (Cat 1–4) | Not overweight → no Cat 3 | ✓ |
| 3 | Not in deployment queue (`queue_symbols`) | Not in DQ | ✓ |
| 4 | `percent_of_portfolio >= 1.0%` (de minimis filter) | 3.65% | ✓ |
| 5 | `replay_supported == False` | False | ✓ |
| 6 | `signal_direction != "BULLISH"` | UNKNOWN | ✓ |

**All six gates pass for VOO → LOW_CONVICTION_REDUCTION.**

### The Evidence String

The evidence field set at line 595:
```python
evidence = [f"HOLD flag | no replay support | {pct:.1f}% weight | opportunity cost position"]
```

This is the string displayed in the Reduction Queue as the "reason."

### The Causal Chain

```
VOO is an ETF
    → analytical_universe.csv does NOT contain VOO (ETFs not scored)
    → No composite_score, no ESS, no signal_direction
    → signal_direction = "" → normalized to "UNKNOWN" in overlay
    → signal_direction != "BULLISH" → CW-DAS ineligible → NOT in DQ
    → No replay evidence in replay_matrix (ETFs not in equity replay universe)
    → replay_supported = False in overlay
    → opportunity_flag = "HOLD" (no ESS → no TRIM/ACCUMULATE determination)
    → All LOW_CONVICTION gates pass
    → Category = LOW_CONVICTION_REDUCTION
    → Label shown in Reduction Queue = "Low Conviction"
```

### Root Cause Classification

This is **Root Cause B: Missing CW-DAS Eligibility** (cascading from Root Cause A: Missing ESS Coverage).

The absence of ESS scoring is correct by design — ETFs should not be scored on individual security conviction metrics. However, the DOWNSTREAM label "Low Conviction" in the Reduction Queue is an incorrect semantic consequence of the correct technical design decision.

---

## Part 3 — Code Path References

| Component | File | Line | Rule |
|---|---|---|---|
| ESS exclusion | `src/portfolio/enrichment.py` | ETF_OVERRIDES table, ~line 38 | ETFs classified via override, not universe |
| Signal UNKNOWN | `src/portfolio/ess.py` (implied) | N/A | No ESS scoring for ETFs |
| DQ exclusion | `src/portfolio/deployment_queue.py` | line 413 | `signal_direction != BULLISH` gate |
| DQ exclusion 2 | `src/portfolio/deployment_queue.py` | line 418 | `strategic_classification != HIGH_CONVICTION_RETAIN` |
| strategic_role empty | `src/portfolio/enrichment.py` | line 231 | `decomposition.strategic_role` not set in ETF_OVERRIDES path |
| MEDIUM importance | `src/portfolio/trim_intelligence.py` | line 744 | `_ROLE_IMPORTANCE.get(role, "MEDIUM")` → empty role → MEDIUM |
| TACTICAL_GROWTH | `src/portfolio/trim_intelligence.py` | line 416 | No BULLISH + no replay → can't be HIGH_CONVICTION_RETAIN → fallback TACTICAL_GROWTH |
| LOW_CONVICTION | `src/portfolio/cra/capital_source_builder.py` | line 558–601 | 6-gate filter → category assignment |
| Label display | `ui/portfolio_alignment/app.js` | `_RQ_CATEGORY_LABELS` | `"LOW_CONVICTION_REDUCTION": "Low Conviction"` |
