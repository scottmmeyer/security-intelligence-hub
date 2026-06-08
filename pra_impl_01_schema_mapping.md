# PRA-IMPL-01 Schema Mapping

Project: Security Intelligence Hub (SIH)  
Issue: PRA-IMPL-01 Typed Recommendation Contract and Card Schema  
Date: 2026-06-08

## card_type Mapping by recommendation_type

| recommendation_type | card_type | execution_state | Notes |
|---|---|---|---|
| REDUCE_OVERWEIGHT | ACTION | EXECUTABLE | Allocation reduction directive |
| INCREASE_UNDERWEIGHT | ACTION | EXECUTABLE | Allocation build directive |
| DIVERSIFY_CONCENTRATION | ACTION | EXECUTABLE | Risk reduction directive |
| IMPROVE_RISK_PROFILE | ACTION | EXECUTABLE | Trim directive |
| IMPROVE_REPLAY_ALIGNMENT | ACTION | EXECUTABLE | Deployment opportunity |
| IMPROVE_SECTOR_EXPOSURE | ACTION | EXECUTABLE | Sector rebalancing directive |
| STRATEGIC_TRIM_CANDIDATE | ACTION | EXECUTABLE | STI-driven trim signal |
| TOP_TRIM_CANDIDATES | ACTION | EXECUTABLE | Phase E aggregated trim |
| STRATEGIC_RETAIN_SIGNAL | OBSERVATION | INFORMATIONAL_ONLY | Retain posture signal; no immediate execution |
| STRATEGIC_RETAIN_NARRATIVE | NARRATIVE | INFORMATIONAL_ONLY | Portfolio conviction narrative |
| THEMATIC_SATURATION_NARRATIVE | NARRATIVE | INFORMATIONAL_ONLY | Thematic concentration narrative |
| PORTFOLIO_CONSTRUCTION_NARRATIVE | NARRATIVE | INFORMATIONAL_ONLY | Portfolio composition synthesis |
| REPLAY_ALIGNMENT_CONTEXT | EXPLAINABILITY | INFORMATIONAL_ONLY | Replay evidence context |
| CONVICTION_EXPLAINABILITY_CARD | EXPLAINABILITY | INFORMATIONAL_ONLY | UCF conviction evidence |

## Canonical card_type Values

ACTION — prescribes a concrete portfolio execution step  
OBSERVATION — materially relevant state; no immediate execution required  
NARRATIVE — portfolio posture synthesis; no execution  
EXPLAINABILITY — evidence trace explaining another recommendation  
DIAGNOSTIC — system/model integrity metadata  

Default: DIAGNOSTIC (safe fallback for any unrecognised type)

## Canonical execution_state Values

EXECUTABLE — ready for operator action  
BLOCKED_BY_POLICY — operator policy prevents execution (PRA-IMPL-02 scope)  
DEFERRED_BY_POLICY — execution deferred by ordering policy (PRA-IMPL-02 scope)  
INFORMATIONAL_ONLY — no execution path; purely contextual  

Default: EXECUTABLE

## Canonical card_lifecycle_state Values

OBSERVED — initial state  
ACTION_QUALIFIED — promoted to action lane  
POLICY_ADJUSTED — execution state modified by policy (PRA-IMPL-02 scope)  
DECISION_PENDING — operator has seen card  
EXECUTED — action has been taken  

Default: OBSERVED

## evidence_link Convention

Empty string = no linked artifact (default)  
Non-empty = reference ID of a supporting artifact (replay run ID, PAR ID, etc.)

## effective_action Convention

Empty string = not yet resolved (default)  
Non-empty = human-readable action verb phrase (set by PRA-IMPL-02 for policy-affected cards)
