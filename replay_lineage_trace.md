# Replay Evidence Lineage Trace — Phase 7.5S-A
**Date:** 2026-06-01  
**Symbols:** VRT, ARW, CIEN, CAH, ATLC, PRG  
**Purpose:** Trace `replay_supported` from final UI boolean all the way back to the source record that caused it.

---

## Architecture Summary

`replay_supported` is a single boolean field on `SecurityIntelligenceOverlay`. It is set in exactly one place: `build_security_overlays()` in `src/portfolio/recommendations.py`, using evidence loaded by `_load_replay_evidence()`.

**Call chain:**
```
UI (replay_supported displayed)
  → PAR run JSON (data/portfolio_ingestion/analysis_runs/{run_id}/security_overlays.csv)
    → runner.py: run_analysis() → build_security_overlays()
      → recommendations.py: _load_replay_evidence()
        → data/current/replay_inputs.csv  ← SOLE DETERMINANT
```

`replay_performance_series.csv` is accepted as a parameter but **is not read** by `_load_replay_evidence()`. It does not affect `replay_supported`.

---

## Evidence Routing Logic

`_load_replay_evidence()` reads `replay_inputs.csv` and partitions symbols into two buckets:

| Bucket | Condition | Promotion |
|--------|-----------|-----------|
| `symbol_tier` | `filter_industry == "ALL"` | Unconditional — `in_replay = True` immediately |
| `industry_replay_evidence` | Any industry-specific `filter_industry` | Conditional — requires tier-compatibility check |

In `build_security_overlays()`:
```python
in_replay = sym in symbol_tier          # unconditional path
if not in_replay and sym in industry_replay_evidence:
    ev = industry_replay_evidence[sym]
    if (ev["geo"] == h.geography
            and ev["cap"] == h.market_cap_bucket
            and ev["industry"] == h.industry.strip().upper()):
        in_replay = True                # conditional path (tier check)
```

**Priority rule:** `symbol_tier` (ALL replays) takes precedence over `industry_replay_evidence`. If a symbol appears in an ALL replay, the industry-specific replay evidence is bypassed entirely.

---

## Per-Symbol Lineage

---

### VRT — `replay_supported = True`

**Derivation path:** `symbol_tier` (unconditional promotion)

**Governing replay (active):**
```
replay_id: REPLAY-2026-05-20-TO-2026-05-26-US-LARGE-ALL-TOP20-WP05D-20260526-ALL2-US-LARGE-ALL
source file: data/current/replay_inputs.csv
field: selected_symbols (contains "VRT")
filter_geography: US
filter_market_cap_bucket: LARGE
filter_industry: ALL          ← routes to symbol_tier (no tier check needed)
replay_mode: CURRENT_RECOMMENDATION
composite_score_snapshot_date: 2026-05-20
top_n: 20
```

**Bypassed replay (also present but inactive):**
```
replay_id: REPLAY-2025-05-14-TO-2026-05-14-US-LARGE-INDUSTRIALS-TOP20-RUN-WP05D-20260515-INDUS1-US-LARGE-INDUSTRIALS
filter_industry: INDUSTRIALS  ← routes to industry_replay_evidence
status: BYPASSED — symbol_tier already populated by ALL replay above
```

**Symbol classification (analytical_universe.csv):**
- geo=US, cap=LARGE, ind=INDUSTRIALS, composite=4.556, ess=VERY_BULLISH

**Key finding:** VRT's `replay_supported=True` is driven by a 4-day-old CURRENT_RECOMMENDATION replay, not the 252-day historical record. The historical INDUSTRIALS basket (+66.7%) is tracked in the performance series but does NOT govern the support boolean.

---

### ARW — `replay_supported = True`

**Derivation path:** `symbol_tier` (unconditional promotion)

**Governing replay (active):**
```
replay_id: REPLAY-2026-05-20-TO-2026-05-26-US-SMALL-ALL-TOP20-WP05D-20260526-ALL2-US-SMALL-ALL
source file: data/current/replay_inputs.csv
field: selected_symbols (contains "ARW")
filter_geography: US
filter_market_cap_bucket: SMALL
filter_industry: ALL          ← routes to symbol_tier (no tier check needed)
replay_mode: CURRENT_RECOMMENDATION
composite_score_snapshot_date: 2026-05-20
top_n: 20
```

**Bypassed replay (also present but inactive):**
```
replay_id: REPLAY-2025-05-14-TO-2026-05-14-US-SMALL-TECHNOLOGY-TOP20-RUN-WP05D-20260515-TECH1-US-SMALL-TECHNOLOGY
filter_industry: TECHNOLOGY  ← routes to industry_replay_evidence
status: BYPASSED — symbol_tier already populated by ALL replay above
```

**Symbol classification (analytical_universe.csv):**
- geo=US, cap=SMALL, ind=TECHNOLOGY, composite=4.889, ess=VERY_BULLISH

**Key finding:** Same pattern as VRT. The 4-day CURRENT_RECOMMENDATION replay drives the boolean. The 252-day SMALL-TECHNOLOGY historical basket (+45.3%) is not the governing evidence.

---

### CIEN — `replay_supported = True`

**Derivation path:** `industry_replay_evidence` → tier-compatibility check PASSES

**Governing replay:**
```
replay_id: REPLAY-2025-05-14-TO-2026-05-14-US-MID-TECHNOLOGY-TOP20-RUN-WP05D-20260515-TECH1-US-MID-TECHNOLOGY
source file: data/current/replay_inputs.csv
field: selected_symbols (contains "CIEN")
filter_geography: US
filter_market_cap_bucket: MID
filter_industry: TECHNOLOGY    ← routes to industry_replay_evidence
replay_mode: HISTORICAL_VALIDATION
composite_score_snapshot_date: 2025-05-14
top_n: 20
```

**Tier-compatibility check:**
```
replay: geo=US, cap=MID, ind=TECHNOLOGY
holding: geo=US, cap=MID, ind=TECHNOLOGY   ← all three match → in_replay = True
```

**Symbol classification (analytical_universe.csv):**
- geo=US, cap=MID, ind=TECHNOLOGY, composite=4.278, ess=BULLISH

**Key finding:** CIEN has only one replay and it is historical. No ALL-industry or CURRENT_RECOMMENDATION replay covers CIEN. Support is based entirely on 252 days of HISTORICAL_VALIDATION evidence.

---

### CAH — `replay_supported = True`

**Derivation path:** `industry_replay_evidence` → tier-compatibility check PASSES

**Governing replay:**
```
replay_id: REPLAY-2025-05-14-TO-2026-05-14-US-MID-HEALTHCARE-TOP20-RUN-WP05D-20260515-HEALTH1-US-MID-HEALTHCARE
source file: data/current/replay_inputs.csv
field: selected_symbols (contains "CAH")
filter_geography: US
filter_market_cap_bucket: MID
filter_industry: HEALTHCARE    ← routes to industry_replay_evidence
replay_mode: HISTORICAL_VALIDATION
composite_score_snapshot_date: 2025-05-14
top_n: 20
```

**Tier-compatibility check:**
```
replay: geo=US, cap=MID, ind=HEALTHCARE
holding: geo=US, cap=MID, ind=HEALTHCARE   ← all three match → in_replay = True
```

**Symbol classification (analytical_universe.csv):**
- geo=US, cap=MID, ind=HEALTHCARE, composite=4.500, ess=VERY_BULLISH

**Key finding:** CAH has only one replay. Support is based on 252 days of HISTORICAL_VALIDATION evidence (MID-HEALTHCARE basket +15.0%).

---

### ATLC — `replay_supported = True`

**Derivation path:** `industry_replay_evidence` → tier-compatibility check PASSES

**Governing replay:**
```
replay_id: REPLAY-2025-05-14-TO-2026-05-14-US-MICRO-FINANCIAL_SERVICES-TOP20-RUN-WP05D-20260515-FIN1-US-MICRO-FINANCIAL_SERVICES
source file: data/current/replay_inputs.csv
field: selected_symbols (contains "ATLC")
filter_geography: US
filter_market_cap_bucket: MICRO
filter_industry: FINANCIAL SERVICES   ← routes to industry_replay_evidence
replay_mode: HISTORICAL_VALIDATION
composite_score_snapshot_date: 2025-05-14
top_n: 20
```

**Tier-compatibility check:**
```
replay: geo=US, cap=MICRO, ind=FINANCIAL SERVICES
holding: geo=US, cap=MICRO, ind=FINANCIAL SERVICES   ← all three match → in_replay = True
```

**Symbol classification (analytical_universe.csv):**
- geo=US, cap=MICRO, ind=FINANCIAL SERVICES, composite=4.778, ess=VERY_BULLISH

**Key finding:** ATLC has only one replay. Support is based on 252 days of HISTORICAL_VALIDATION evidence (MICRO-FINANCIAL_SERVICES basket +13.8%).

---

### PRG — `replay_supported = False`

**Derivation path:** Not in `symbol_tier`. Not in `industry_replay_evidence`. → `in_replay` remains False.

**Why PRG is absent:**

Two replays exist for PRG's tier (US-MICRO) and are confirmed AVAILABLE in `replay_availability.csv`:

| Replay | Mode | Snapshot | PRG selected? |
|--------|------|----------|---------------|
| US-MICRO-INDUSTRIALS HISTORICAL | HISTORICAL_VALIDATION | 2025-05-14 | **No** (top-20 full — PRG ranked >20) |
| US-MICRO-ALL CURRENT_RECOMMENDATION | CURRENT_RECOMMENDATION | 2026-05-20 | **No** (top-20 full — PRG ranked >20) |

PRG's current composite is 4.722 (VERY_BULLISH), but this reflects its score as of 2026-06-01. At the historical snapshot date (2025-05-14) and the current recommendation snapshot date (2026-05-20), competing MICRO stocks occupied all 20 slots.

**Symbol classification (analytical_universe.csv):**
- geo=US, cap=MICRO, ind=INDUSTRIALS, composite=4.722, ess=VERY_BULLISH

**Key finding:** PRG has the signal quality for replay support. It is excluded not by disqualification but by rank: it did not place in the top-20 composite scorers among US MICRO-cap stocks at either relevant snapshot date. A future replay snapshot where PRG ranks top-20 would cause `replay_supported` to flip to True without any code change.

---

## Lineage Summary Table

| Symbol | replay_supported | Route | Governing replay_id (abbreviated) | Mode | Replay scope |
|--------|-----------------|-------|-----------------------------------|------|-------------|
| VRT | True | symbol_tier (ALL) | …-US-LARGE-ALL-TOP20-…-20260526-ALL2-… | CURRENT_RECOMMENDATION | US.LARGE |
| ARW | True | symbol_tier (ALL) | …-US-SMALL-ALL-TOP20-…-20260526-ALL2-… | CURRENT_RECOMMENDATION | US.SMALL |
| CIEN | True | industry_replay_evidence (tier match) | …-US-MID-TECHNOLOGY-TOP20-…-TECH1-… | HISTORICAL_VALIDATION | US.MID.TECHNOLOGY |
| CAH | True | industry_replay_evidence (tier match) | …-US-MID-HEALTHCARE-TOP20-…-HEALTH1-… | HISTORICAL_VALIDATION | US.MID.HEALTHCARE |
| ATLC | True | industry_replay_evidence (tier match) | …-US-MICRO-FINANCIAL_SERVICES-TOP20-…-FIN1-… | HISTORICAL_VALIDATION | US.MICRO.FINANCIAL SERVICES |
| PRG | False | neither bucket | n/a — both US-MICRO replays exist but PRG not in top-20 at snapshot dates | — | — |
