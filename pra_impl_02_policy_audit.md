# PRA-IMPL-02 Policy Audit

Repository: security-intelligence-hub  
Date: 2026-06-08  
Baseline: PRA-IMPL-01 certified (commit 5444689)

## Forensic Audit — All Recommendation Surfaces

### Surface 1: Deployment Queue (apply_policy_to_queue)

Current policy handling: COMPLETE  
Location: src/portfolio/deployment_queue.py via apply_policy_to_queue()  
Policy effects applied:
- DO_NOT_SELL: entry moved to policy_suppressed list; not in executable queue
- SELL_LAST: entry tail-ranked within sell cohort
- CORE_ANCHOR: annotation only; no queue position change
- PREFERRED_ACCUMULATION: rank boost at top of buy cohort

Missing: None — deployment queue is fully policy-aware.

### Surface 2: security_overlays.csv (compute_execution_state)

Current policy handling: COMPLETE  
Location: runner.py lines 858–875  
Policy effects applied:
- compute_execution_state() called per symbol per overlay
- execution_state and effective_action written to CSV

Missing: None — overlays are fully policy-aware.

### Surface 3: PortfolioRecommendation objects (generate_recommendations)

Current policy handling: MISSING  
Location: src/portfolio/recommendations.py; assembled into recs_with_drilldown in runner.py  
Policy effects applied: None at time of construction  
Root cause: _policy_registry is loaded AFTER recs_with_drilldown is assembled  
Issue: Recommendation dicts keep card_type/execution_state defaults from PRA-IMPL-01 (EXECUTABLE) without reflecting policy

Missing:
- REDUCE_OVERWEIGHT recs that include DO_NOT_SELL symbols do not carry BLOCKED_BY_POLICY state
- REDUCE_OVERWEIGHT recs that include SELL_LAST symbols do not carry DEFERRED_BY_POLICY state
- execution_state, effective_action, and card_lifecycle_state are always default on all recs

### Surface 4: Allocation Reduction (REDUCE_OVERWEIGHT recommendations)

Current policy handling: MISSING  
These recs list affected_symbols (e.g., DODFX, TSLA) but do not annotate policy state.  
DODFX (SELL_LAST): appears as ordinary REDUCE candidate with no deferral annotation.  
TSLA (DO_NOT_SELL): appears as ordinary REDUCE candidate with no block annotation.

### Surface 5: Funding Sources (INCREASE_UNDERWEIGHT drilldown funding)

Current policy handling: NOT APPLICABLE AT THIS SCOPE  
Funding sources are embedded in drilldown objects from the drilldown builder, not in PortfolioRecommendation directly. Policy normalization at the recommendation level is the PRA-IMPL-02 scope; funding source drilldown policy is PRA-IMPL-02 extension.

### Surface 6: CRA

Current policy handling: PARTIAL  
CRA CapitalSourceRecord includes blocked_by_policy and policy_type fields (from Phase 23.6 data model). However, the CRA proposal is not regenerated as part of every PAR run — it is a separate operator-initiated proposal. CRA policy is structurally present but depends on operator triggering a proposal rebuild.

### Surface 7: PAP

Not yet implemented as an independent surface. Policy in PAP context flows through deployment queue. No additional scope here.

### Surface 8: recs_with_drilldown (the recommendation JSON output)

Current policy handling: MISSING  
This is the output consumed by the UI and the operator. Policy state must be injected here after _policy_registry is loaded.

## Key Finding

The sole required fix for PRA-IMPL-02:

After _policy_registry is loaded in runner.py, iterate recs_with_drilldown and apply compute_execution_state() to each recommendation's primary affected symbol, updating the execution_state, effective_action, and card_lifecycle_state fields.

This is purely additive. No scoring, no ranking, no generation logic changes.
