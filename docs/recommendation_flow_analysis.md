# Recommendation Flow Analysis

**Phase 7.3 — Architecture Design**
**Document type:** Current-state analysis
**Based on:** Phase 7.2 audit findings + live run data (2026-05-30)

---

## 1. Current Recommendation Lifecycle

The current pipeline produces recommendations through a sequential, layer-by-layer
architecture. Each layer has independent inputs and no upstream feedback loop.

```
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 1 — Portfolio Ingestion                                       │
│  ingestion.py → enrichment.py                                       │
│                                                                     │
│  Input:   raw CSV (broker export)                                   │
│  Output:  PortfolioHolding list                                     │
│           fields: symbol, market_value, percent_of_portfolio,       │
│                   asset_class, geography, market_cap_bucket,        │
│                   mega_subtier, composite_score, ess_score_text,    │
│                   zacks_rating, sector, industry                    │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 2 — Allocation Alignment                                      │
│  alignment.py → compute_alignment()                                 │
│                                                                     │
│  Input:   PortfolioHolding list + archetype YAML targets           │
│  Output:  AllocationAlignmentResult list                            │
│           fields: node_key, actual_pct, tactical_target_pct,       │
│                   drift_pct, drift_direction, severity,             │
│                   recommendation_priority                           │
│                                                                     │
│  Logic:   For each allocation node defined in YAML targets:         │
│           actual% = sum(holding MV) / total MV                     │
│           drift = actual - target                                   │
│           severity = f(|drift|, node thresholds)                   │
│                                                                     │
│  GAP HERE: No conviction, replay, or ESS data enters at this step. │
│            Severity is purely drift-magnitude based.                │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 3 — Recommendation Generation                                 │
│  recommendations.py → generate_recommendations()                   │
│                                                                     │
│  Input:   AllocationAlignmentResult list                            │
│  Output:  PortfolioRecommendation list                              │
│                                                                     │
│  Logic for UNDERWEIGHT nodes:                                       │
│    1. Filter: severity in (HIGH, MODERATE)                          │
│    2. Look up investable_vehicle_registry.yaml for node_key        │
│    3. Call _sorted_vehicles_with_suitability() to rank ETF options  │
│    4. Insert top vehicle as affected_symbols[0]                     │
│    5. Attach suitability_notes from VehicleSuitabilityNote objects  │
│                                                                     │
│  ARCHITECTURE GAP: "Best vehicle for node" is determined entirely  │
│  from the registry lookup. Individual securities in the portfolio   │
│  that live in the target node are NOT evaluated as alternatives.    │
│                                                                     │
│  Logic for OVERWEIGHT nodes:                                        │
│    1. Filter: severity in (HIGH, MODERATE)                          │
│    2. Call _symbols_in_node() to find overweight holdings           │
│    3. No conviction/replay/ESS weighting applied to reduce order   │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 4 — Security Intelligence Overlay (Layer G)                  │
│  recommendations.py → build_security_overlays()                    │
│                                                                     │
│  Input:   PortfolioHolding list + AllocationAlignmentResult list    │
│  Output:  SecurityIntelligenceOverlay per holding                   │
│           fields: signal_direction, opportunity_flag,               │
│                   composite_score, replay_supported,                │
│                   is_overweight_vs_target                           │
│                                                                     │
│  Signal Sources that enter here:                                    │
│    • ESS (Empirical Signal Score) — primary direction signal        │
│    • composite_score — Danelfin + Zacks + Yahoo weighted average    │
│    • Zacks rating — component of composite                          │
│    • replay_supported — symbol in any TOP_N_STRATEGY replay tier    │
│                                                                     │
│  ARCHITECTURE GAP: Overlay is computed AFTER recommendations.       │
│  It cannot modify or gate the recommendations produced in Step 3.  │
│  Overlay = intelligence that never feeds back into rec generation.  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 5 — Mandate Intelligence (PMI)                               │
│  mandate.py → build_mandate_recommendation_overlay()               │
│                                                                     │
│  Input:   PortfolioRecommendation list + PortfolioMandate          │
│  Output:  mandate_overlay dict (rec_id → interpretation)           │
│           fields: mandate_label, mandate_severity, mandate_urgency  │
│                                                                     │
│  Logic:                                                             │
│    • CONCENTRATED_ALPHA mandate → high tolerance for deviations     │
│    • INTENTIONAL_UNDERWEIGHT label: urgency demoted to INFORMATIONAL│
│    • INTENTIONAL_OVERWEIGHT label: urgency demoted to INFORMATIONAL │
│                                                                     │
│  ARCHITECTURE GAP: PMI demotes urgency but recommendations remain  │
│  visible in output. The engine produces MODERATE rec, mandate says  │
│  INFORMATIONAL — and both are presented. User sees contradiction.  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 6 — Strategic Trim Intelligence (Phase E)                    │
│  trim_intelligence.py → build_strategic_profiles()                 │
│  phase_e_synthesis.py → synthesize_phase_e_recommendations()       │
│                                                                     │
│  Input:   PortfolioHolding + SecurityOverlay + Alignment           │
│  Output:  HoldingStrategicProfile per holding                       │
│           fields: strategic_classification, trim_priority_score,   │
│                   narrative_tier, strategic_anchor_rank,            │
│                   thematic_overlap_clusters, concentration_pressure │
│                                                                     │
│  Signal Sources entering here:                                      │
│    • STI classification (CCL/HCA/TGC/WTC)                          │
│    • thematic_redundancy_score                                      │
│    • concentration_pressure                                         │
│    • diversification_contribution                                   │
│    • overlap_peers                                                  │
│                                                                     │
│  ARCHITECTURE GAP: STI and trim intelligence run after (and        │
│  separate from) Phase F/G allocation recs. They do not influence   │
│  which vehicle is selected or what Build recs are generated.       │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 7 — Multi-Dimensional Scoring + Runner Output Assembly       │
│  scoring.py → compute_multi_dimensional_score()                    │
│  runner.py → run_analysis()                                        │
│                                                                     │
│  Output keys in result dict:                                        │
│    recommendations        — Phase F/G recs (Step 3 output)         │
│    security_overlays      — per-holding intelligence (Step 4)      │
│    strategic_profiles     — STI profiles (Step 6)                  │
│    alignment              — alignment results (Step 2)             │
│    mandate_overlay        — PMI interpretation (Step 5)            │
│    multi_dimensional_score— composite portfolio quality score       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Where Each Signal Enters

| Signal | Step | How It Enters | Feeds Back to Recs? |
|--------|------|---------------|---------------------|
| Allocation drift | Step 2 | compute_alignment() | ✓ Direct (generates recs) |
| Archetype targets (YAML) | Step 2 | load_archetype_targets() | ✓ Direct |
| Mandate (CONCENTRATED_ALPHA) | Step 5 | build_mandate_recommendation_overlay() | ✗ Interpretation only |
| ESS score | Step 4 | build_security_overlays() | ✗ No rec feedback |
| Composite score | Step 4 | build_security_overlays() | ✗ No rec feedback |
| Zacks rating | Step 4 | build_security_overlays() | ✗ No rec feedback |
| Danelfin (via composite) | Step 4 | build_security_overlays() | ✗ No rec feedback |
| Replay support | Step 4 | _load_replay_evidence() | ✗ No rec feedback |
| STI classification | Step 6 | build_strategic_profiles() | ✗ No rec feedback |
| Trim priority score | Step 6 | build_strategic_profiles() | ✗ No rec feedback |
| Concentration pressure | Step 6 | build_strategic_profiles() | ✗ No rec feedback |
| Vehicle suitability | Step 3 | _sorted_vehicles_with_suitability() | ✓ Partial (sort order only) |
| Overlap peers | Step 6 | thematic overlap engine | ✗ No rec feedback |

**Root Cause Summary:**
The system is structured as a unidirectional pipeline. Intelligence produced
downstream (Steps 4–6) has no pathway to influence the recommendation content
produced upstream (Step 3). The allocation engine is isolated from conviction,
replay, ESS, Zacks, and STI data at the time it generates recommendations.

---

## 3. Current PMI Interaction Diagram

```
Allocation Engine (Step 3)                  PMI (Step 5)
─────────────────────────────               ─────────────────────────────
drift = -7.34% (US LARGE)                  mandate = CONCENTRATED_ALPHA
severity = MODERATE          →  rec  →     tolerance = 0.2 (target_adherence)
rec_type = INCREASE_UNDERWEIGHT             drift_label = INTENTIONAL_UNDERWEIGHT
vehicle = VOO                               mandate_urgency = INFORMATIONAL
suitability = LOW (15/100)                  mandate_severity = NONE
```

**Effect:** Engine says "Build with VOO (MODERATE severity)."
PMI says "This is intentional, ignore (INFORMATIONAL urgency)."
Both statements are presented to the user simultaneously. Neither wins.

---

## 4. Key Architecture Deficits (Ranked by Impact)

### Deficit 1 — No Conviction Gate at Recommendation Generation
**Current:** Any vehicle in the registry can be recommended regardless of whether
portfolio already holds better securities for the same node.
**Impact:** VOO recommended for US Large despite VRT (composite 4.556, CCL, replay)
and DELL (4.500, HCA, replay) already being held in the same node.

### Deficit 2 — No Cross-Node Impact Analysis
**Current:** Each recommendation targets one node in isolation. No analysis is
performed of whether the vehicle worsens other nodes.
**Impact:** VOO repair for US Large (-7.3%) simultaneously amplifies HYPER_MEGA
(+3.7% OW). Net portfolio improvement of VOO purchase = 0 or negative.

### Deficit 3 — PMI-Engine Disconnect (Contradictory Output)
**Current:** Engine generates MODERATE recommendation; PMI independently demotes
it to INFORMATIONAL. Both are emitted. No reconciliation.
**Impact:** User receives contradictory recommendations. System has no authoritative
single output.

### Deficit 4 — No Portfolio Improvement Score at Decision Time
**Current:** PIS (Portfolio Improvement Score) was created as a Phase 7.2 audit
metric. It is not used by the recommendation engine.
**Impact:** Engine ranks recs by allocation severity, not by net portfolio value
created. A rec with HIGH drift severity but LOW conviction and conflicting node
impact outranks a LOW severity rec that creates genuine net improvement.

### Deficit 5 — ETF-First Default
**Current:** Investable vehicle registry defaults to ETFs for all underweight nodes.
Individual securities that the portfolio already owns — and which sit precisely in
the target node — are not evaluated as alternatives.
**Impact:** Engine recommends deploying cash into VOO (15% effective node coverage)
instead of adding to VRT (100% node coverage, CCL, replay supported).

### Deficit 6 — No Conflict Detection
**Current:** Recommendations are generated independently per alignment result.
No post-generation step examines whether recs conflict with each other.
**Impact:** VOO appears in both "Build US Large" and "Build Extended Mega" recs,
with VOO simultaneously implicated in worsening HYPER_MEGA (a separate "Reduce" rec).

---

## 5. Recommendation State Table (Current Run)

| Rec | Engine Severity | Engine Urgency | PMI Label | PMI Urgency | Net Signal |
|-----|----------------|---------------|-----------|-------------|------------|
| Build US Large (VOO) | MODERATE | — | INTENTIONAL_UNDERWEIGHT | INFORMATIONAL | Contradiction |
| Build Ext. Mega (VTI) | MODERATE | — | INTENTIONAL_UNDERWEIGHT | INFORMATIONAL | Contradiction |
| Reduce Intl (MODERATE) | MODERATE | — | STANDARD_OVERWEIGHT | MODERATE | Coherent |
| Reduce Hyper Mega (MODERATE) | MODERATE | — | STANDARD_OVERWEIGHT | MODERATE | Coherent |
| Reduce Intl Large (MODERATE) | MODERATE | — | STANDARD_OVERWEIGHT | MODERATE | Coherent |

**Pattern:** Every "Build" recommendation is simultaneously contradicted by the
PMI layer under Concentrated Alpha mandate. Every "Reduce" recommendation is coherent.
The Build recs exist solely because the allocation engine produced them —
they create no actionable guidance.
