# DIL Phase 1 — Architecture

**Date:** 2026-06-10  
**Status:** IMPLEMENTED

---

## System Overview

DIL Phase 1 implements a client-side interpretive posture engine. All computation occurs in JavaScript at render time, reading from `_lastAnalysisData`. No server round-trips during render. No scoring or ranking influence.

---

## Data Flow

```
run_analysis() / load_analysis_run()
    ↓ produces _lastAnalysisData containing:
    
analyst_consensus_by_symbol     (Yahoo, weekly)
fidelity_signals_by_symbol      (Fidelity StarMine, daily)
fmp_data_by_symbol              (FMP, weekly) ← NEW in DIL Phase 1
ucf_verdicts_by_symbol          (Computed, PAR time)
security_overlays               (Computed, PAR time)

        ↓ (all display-only; no feedback into scoring)

computeDIL(sym, ac, fs, fmpEntry, ucf, ov, context)
    → { posture_label, postureClass, rationale_text, keyPoints[], evidence[] }

        ↓

_dilHtml(dilResult)
    → HTML string with posture badge, narrative, evidence list

        ↓ injected into:

Reduction Queue profiles (ARCH-05 profile expansion)
Deployment Candidate cards (⚡ Intel expandable panel)
```

---

## `_build_fmp_payload()` — New Backend Function

**File:** `src/portfolio/runner.py`  
**Purpose:** Expose FMP fundamental context fields for DIL  
**Governance:** Read-only display fields. Never injected into CW-DAS, RPS, or any scorer.

Fields exposed:
- `latest_eps_surprise_pct`, `beat_rate_8q`, `beats_last_8q`
- `q1–q4_surprise_pct`, `revenue_growth_q1_yoy`, `eps_growth_q1_yoy`
- `revenue_acceleration`, `fmp_coverage_status`, `fmp_sourced_date`
- `buy_count`, `hold_count`, `sell_count`, `net_buy_score`
- `ev_ebitda_ttm`, `fcf_yield_ttm`, `roe_ttm`, `roic_ttm`

Added to both `run_analysis()` result and `load_analysis_run()` result as `fmp_data_by_symbol`.

---

## `computeDIL()` — Posture Engine

**File:** `ui/portfolio_alignment/app.js`  
**Lines:** ~200  
**Type:** Pure function (no side effects, no DOM writes, no globals mutated)

**Input parameters:**
- `sym` — symbol string
- `ac` — analyst_consensus entry
- `fs` — fidelity_signals entry (includes consensus_matrix)
- `fmpEntry` — FMP fundamental entry (may be null)
- `ucf` — UCF verdict entry
- `ov` — security overlay entry
- `context` — `{ isReduction, isDeployment, category }`

**Output:**
```javascript
{
  posture:      string,     // "INVESTIGATE BEFORE ACTING" etc.
  postureClass: string,     // CSS class for badge color
  rationale:    string,     // Human-readable assessment
  keyPoints:    string[],   // Bullet points
  evidence:     string[],   // Cited signal sources
}
```

---

## `_dilHtml()` — Render Helper

Converts `computeDIL()` output to HTML string with:
- Posture badge (color-coded)
- Rationale text
- Key points list
- Evidence list (source + date citations)
- Advisory disclosure

---

## Integration Points

### Reduction Queue (ARCH-05)
DIL section appended to profile HTML. Visible when operator expands "▼ Profile".

### Deployment Candidates (Top 10)
"⚡ Intel" button added below reason chips. Expands `da-intel-panel` inline within the card.

---

## Governance Compliance

| Requirement | Status |
|---|---|
| No CW-DAS changes | ✓ No changes to deployment_queue.py |
| No RPS changes | ✓ No changes to recommendations.py |
| No PAP changes | ✓ No changes to PAP generation |
| No scoring changes | ✓ FMP payload is read-only display |
| No ranking changes | ✓ computeDIL never touches queue order |
| No PAR persistence | ✓ DIL output not written to any artifact |
| Evidence traceability | ✓ Every signal cited with source and date |
| Advisory disclosure | ✓ Displayed in every DIL panel |
