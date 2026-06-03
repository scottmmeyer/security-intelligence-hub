# Optimizer vs Legacy Recommendation Report

**Generated:** 2026-05-30T15:53:23Z
**Mandate:** Concentrated Alpha
**Portfolio:** 472,220 | 81 holdings | Date: 2026-05-30
**Run ID:** PAR-20260530-7B861236

## Design Principles
> This report compares the **legacy recommendation engine output** (existing, unchanged) against the **Phase 7.3A parallel optimizer** candidate rankings. The legacy recommendations are **not modified** by this analysis. This report informs Phase 7.3D migration planning only.

## Build Recommendation Comparison

| Legacy Rec | Legacy Vehicles | Legacy Severity | Mandate Urgency | Optimizer Preferred | PIS | Optimizer Decision | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Build EQUITIES.US.LARGE allocation (-7.3% drift) | VOO, IVV, SPY | MODERATE | INFORMATIONAL | DELL (SECURITY) | 0.0 | MANDATE_BLOCKED | Mandate BLOCKED; replay ✓; composite=4.500; STI=HIGH_CONVICTION_ANCHOR; [T1:VOO] [T1:IVV] [T1:SPY] [T2:VOO] [T3:None] |
| Build EQUITIES.US.MEGA.EXTENDED_MEGA allocation (-4.1% drift) | VTI, SCHB, VOO | MODERATE | INFORMATIONAL | VTI (ETF) | 0.0 | MANDATE_BLOCKED | Mandate BLOCKED; [T1:VTI] [T1:SCHB] [T1:VOO] [T2:VOO] [T3:None] |

## Spotlight: US Large Deployment Decision

The Phase 7.3A key validation: for the 'Build US Large' recommendation, does the optimizer correctly rank individual portfolio securities (VRT, LRCX, DELL) above ETF vehicles (VOO, IVV, SPY) when the ETFs would worsen the HYPER_MEGA overweight?

**Recommendation:** Build EQUITIES.US.LARGE allocation (-7.3% drift)
**Mandate urgency:** INFORMATIONAL | **Optimizer decision:** MANDATE_BLOCKED

**Security candidates:**
| Symbol | PIS | Composite | Replay | STI | % of Port | Status |
| --- | --- | --- | --- | --- | --- | --- |
| **DELL** | 0.0 | 4.500 | ✓ | HIGH_CONVICTION_ANCHOR | 1.32% | MANDATE_BLOCKED |
| **LRCX** | 0.0 | 4.500 | ✓ | HIGH_CONVICTION_ANCHOR | 0.95% | MANDATE_BLOCKED |
| **PLTR** | 0.0 | 3.286 |  | TACTICAL_GROWTH_CANDIDATE | 0.03% | MANDATE_BLOCKED |
| **VRT** | 0.0 | 4.556 | ✓ | CORE_CONVICTION_LEADER | 3.60% | MANDATE_BLOCKED |

**ETF candidates:**
| Symbol | PIS | NCS | ETF Gate | Suitability | Worsens OW | Status |
| --- | --- | --- | --- | --- | --- | --- |
| VOO | 0.0 | 0.0% | FAIL [suitability=LOW; NCS=0.0%<10.0%; worsens_overweight=True] | LOW | ⚠ YES | MANDATE_BLOCKED |
| IVV | 0.0 | 0.0% | FAIL [suitability=LOW; NCS=0.0%<10.0%; worsens_overweight=True] | LOW | ⚠ YES | MANDATE_BLOCKED |
| SPY | 0.0 | 0.0% | FAIL [suitability=LOW; NCS=0.0%<10.0%; worsens_overweight=True] | LOW | ⚠ YES | MANDATE_BLOCKED |

## All Recommendation Optimizer Decisions

| Rec ID | Type | Node | Decision |
| --- | --- | --- | --- |
| `REC-C89EEF6E` | PORTFOLIO_CONSTRUCTION_NARRATIVE | `None` | NOT_APPLICABLE |
| `REC-04ADB715` | INCREASE_UNDERWEIGHT | `EQUITIES.US.LARGE` | MANDATE_BLOCKED |
| `REC-3F564454` | REDUCE_OVERWEIGHT | `EQUITIES.INTERNATIONAL.LARGE` | REDUCE_COHERENT |
| `REC-18337245` | INCREASE_UNDERWEIGHT | `EQUITIES.US.MEGA.EXTENDED_MEGA` | MANDATE_BLOCKED |
| `REC-4E732B66` | REDUCE_OVERWEIGHT | `EQUITIES.US.MEGA.HYPER_MEGA` | REDUCE_COHERENT |
| `REC-ED31D83F` | IMPROVE_REPLAY_ALIGNMENT | `EQUITIES.US.LARGE` | NOT_APPLICABLE |
| `REC-FDAE7FA1` | REDUCE_OVERWEIGHT | `EQUITIES.INTERNATIONAL` | REDUCE_COHERENT |
| `REC-4059BC0C` | STRATEGIC_RETAIN_SIGNAL | `None` | NOT_APPLICABLE |
| `REC-741657EB` | STRATEGIC_RETAIN_SIGNAL | `None` | NOT_APPLICABLE |
| `REC-13599529` | STRATEGIC_RETAIN_NARRATIVE | `None` | NOT_APPLICABLE |
| `REC-518A1615` | STRATEGIC_RETAIN_NARRATIVE | `None` | NOT_APPLICABLE |
| `REC-B2B63DE6` | STRATEGIC_RETAIN_NARRATIVE | `None` | NOT_APPLICABLE |
| `REC-F2BE2EFF` | REPLAY_ALIGNMENT_CONTEXT | `None` | NOT_APPLICABLE |
| `REC-A0D758F6` | CONVICTION_EXPLAINABILITY_CARD | `None` | NOT_APPLICABLE |
| `REC-8817AE14` | CONVICTION_EXPLAINABILITY_CARD | `None` | NOT_APPLICABLE |
| `REC-E58FDD84` | CONVICTION_EXPLAINABILITY_CARD | `None` | NOT_APPLICABLE |
| `REC-E6F4D4E0` | CONVICTION_EXPLAINABILITY_CARD | `None` | NOT_APPLICABLE |
| `REC-719353EA` | CONVICTION_EXPLAINABILITY_CARD | `None` | NOT_APPLICABLE |
| `REC-C576FE87` | CONVICTION_EXPLAINABILITY_CARD | `None` | NOT_APPLICABLE |
| `REC-6922E518` | CONVICTION_EXPLAINABILITY_CARD | `None` | NOT_APPLICABLE |
| `REC-B032A6F3` | CONVICTION_EXPLAINABILITY_CARD | `None` | NOT_APPLICABLE |
| `REC-CB196ED9` | CONVICTION_EXPLAINABILITY_CARD | `None` | NOT_APPLICABLE |
| `REC-568F5E71` | CONVICTION_EXPLAINABILITY_CARD | `None` | NOT_APPLICABLE |
| `REC-7251C57D` | CONVICTION_EXPLAINABILITY_CARD | `None` | NOT_APPLICABLE |
| `REC-A207F7FA` | CONVICTION_EXPLAINABILITY_CARD | `None` | NOT_APPLICABLE |
| `REC-4ABDD1D2` | CONVICTION_EXPLAINABILITY_CARD | `None` | NOT_APPLICABLE |
| `REC-F0418C7D` | CONVICTION_EXPLAINABILITY_CARD | `None` | NOT_APPLICABLE |
| `REC-5D4EFC20` | CONVICTION_EXPLAINABILITY_CARD | `None` | NOT_APPLICABLE |
| `REC-E2708405` | CONVICTION_EXPLAINABILITY_CARD | `None` | NOT_APPLICABLE |
| `REC-746044F2` | CONVICTION_EXPLAINABILITY_CARD | `None` | NOT_APPLICABLE |
| `REC-A53382F0` | CONVICTION_EXPLAINABILITY_CARD | `None` | NOT_APPLICABLE |
| `REC-242C836F` | CONVICTION_EXPLAINABILITY_CARD | `None` | NOT_APPLICABLE |
| `REC-2A4E3FE0` | CONVICTION_EXPLAINABILITY_CARD | `None` | NOT_APPLICABLE |