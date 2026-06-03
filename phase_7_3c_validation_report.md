# Phase 7.3C Validation Report
## Optimizer-Preferred Candidate Display

**Date:** 2026-05-30  
**Baseline:** `portfolio-manager-v7.3b-stable` (504 tests passing)  
**Post-7.3C:** 533 tests passing (29 new + 504 existing)

---

## Objective

Surface the optimizer-preferred candidate **alongside** the legacy recommendation in the UI, enabling side-by-side comparison without replacing or suppressing any existing recommendation.

---

## Deliverables

### 1. Optimizer-Preferred Candidate Display ✅

**File:** `src/portfolio/optimizer.py`  
**Added:** `_build_preferred_display()` function

Computes a display-ready comparison dict attached to each optimizer result as `preferred_display`.

Populated only when:
- `optimizer_decision == "SECURITY_SUPERIOR"`, AND
- The preferred candidate symbol differs from `legacy_vehicles`

Returns `None` in all other cases (ETF_ADEQUATE, MANDATE_BLOCKED, NO_CANDIDATES, REDUCE_COHERENT, NOT_APPLICABLE).

`preferred_display` structure:
```
{
  legacy_symbol:        str   — e.g. "VOO"
  preferred_symbol:     str   — e.g. "VRT"
  pis_delta:            float — preferred.pis - best_etf.pis
  key_advantages:       list  — human-readable advantage text
  legacy_summary:       dict  — ETF fields: pis, etf_gate, suitability_tier, ncs, worsens_overweight
  preferred_summary:    dict  — Security fields: pis, composite_score, sti_tier, replay_supported, ess_score
}
```

Key advantages computed:
- `Higher PIS (+N)` — when pis_delta > 0
- `Replay-supported` — when preferred.replay_supported is True
- `Core conviction leader` — when sti_tier = CCL
- `High conviction anchor` — when sti_tier = HCA
- `No overweight amplification` — when legacy ETF worsens_overweight
- `Avoids ETF gate failure` — when best ETF etf_gate != PASS
- `Strong composite score (N.NN)` — when composite_score >= 4.0

---

### 2. Side-by-Side Legacy vs Optimizer Comparison ✅

**File:** `ui/portfolio_alignment/app.js`  
**Added:** `_buildOptimizerPreferredPanel(r)` function

Renders a two-column comparison panel when `preferred_display` is present:

```
┌─────────────────────────┐     ┌─────────────────────────┐
│ Legacy Recommendation   │ vs  │ Optimizer Preferred      │
│ VOO                     │     │ VRT                      │
│ ETF                     │     │ SECURITY                 │
│ PIS: 1.5                │     │ PIS: 37.0                │
│ ETF Gate: FAIL          │     │ Composite: 4.56          │
│ Suitability: LOW        │     │ STI: CCL                 │
│ NCS: 4.5%               │     │ Replay: Yes              │
│ ⚠ Worsens overweight    │     │                          │
└─────────────────────────┘     └─────────────────────────┘
Key advantages: +35.5 PIS  Replay-supported  Core conviction leader
                No overweight amplification  Avoids ETF gate failure
                Strong composite score (4.56)
```

Panel is embedded **inside** the existing Optimizer View collapsible block, appearing after the ETF Assessment section.

---

### 3. Recommendation Card Enhancement ✅

**File:** `ui/portfolio_alignment/index.html`  
**Added:** Phase 7.3C CSS block (`.optpref-*` selectors)

- `.optpref-panel` — green-tinted container with 4px left accent border
- `.optpref-comparison` — two-column CSS grid layout
- `.optpref-col-legacy` — amber-tinted legacy column
- `.optpref-col-preferred` — green-tinted preferred column
- `.optpref-advantage` — green pill chips for each advantage
- `.optpref-delta` — dark-green PIS delta badge
- Responsive: collapses to single-column on narrow viewports (<640px)

---

### 4. Validation Report ✅

This document.

---

### 5. Full Regression Suite ✅

| Scope | Before | After | Delta |
|---|---|---|---|
| Total tests | 504 | 533 | +29 |
| Failures | 0 | 0 | 0 |

**New tests in `tests/test_7_3c_optimizer_preferred.py`:** 29 tests  
- 21 unit tests for `_build_preferred_display()`
- 8 integration tests for `run_parallel_optimizer()` → `preferred_display`

**Existing tests updated:**
- `tests/test_optimizer.py` line 246: version assertion relaxed to accept `"7.3A"`, `"7.3B"`, or `"7.3C"`

---

## Governance Verification

| Constraint | Status |
|---|---|
| Legacy recommendation ordering unchanged | ✅ Verified (run_parallel_optimizer returns scores dict; does not mutate rec list) |
| Legacy recommendation count unchanged | ✅ Verified by test_legacy_rec_count_and_order_unchanged |
| No legacy recommendation fields modified | ✅ Verified by test_17_legacy_rec_fields_unchanged |
| ETF fallback logic intact | ✅ ETF candidates still scored and surfaced |
| No recommendation replacement | ✅ preferred_display is display-only metadata |
| Backward compatibility | ✅ preferred_display=None when not applicable; no existing field removed |
| optimizer_version | ✅ Updated default to "7.3C" |

---

## Canonical Example: VOO → VRT

**Recommendation:** Build US Large (EQUITIES.US.LARGE)  
**Legacy vehicle:** VOO

| Dimension | VOO (Legacy ETF) | VRT (Optimizer Preferred) |
|---|---|---|
| Candidate type | ETF | SECURITY |
| PIS | ~1.5 | ~37.0 |
| ETF Gate | FAIL (suitability=LOW) | NA |
| Suitability | LOW | NA |
| NCS | ~4.5% | 100% |
| Worsens overweight | Yes | No |
| Replay supported | No | Yes |
| STI tier | NA | CCL |
| Composite score | — | 4.556 |

**Key advantages surfaced:** Higher PIS (+35.5), Replay-supported, Core conviction leader, No overweight amplification, Avoids ETF gate failure, Strong composite score (4.56)

---

## What Phase 7.3C Does NOT Do

- Does **not** change legacy recommendation ordering
- Does **not** suppress legacy recommendations
- Does **not** replace VOO with VRT in `affected_symbols`
- Does **not** remove ETF fallback logic
- Does **not** grant optimizer preferred any action authority

Optimizer preferred display is **visibility only**. Legacy recommendations take precedence until Phase 7.3D.

---

## Ready for Phase 7.3D

Phase 7.3D scope (not yet implemented):
- Allow optimizer-preferred candidate to replace legacy vehicle in recommendation ordering
- Gate behind explicit user/portfolio manager confirmation
- Requires audit trail of the switch
