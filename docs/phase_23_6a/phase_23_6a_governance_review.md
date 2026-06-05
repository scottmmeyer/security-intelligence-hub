# Phase 23.6A — Governance Review

**Date:** 2026-06-04

---

## Non-Negotiable Constraint Verification

| Constraint | Verified | Evidence |
|------------|----------|----------|
| CW-DAS not modified | ✅ | `deployment_score` and `rank` are immutable copy-through from `deployment_queue.json`. `test_cw_das_scores_unchanged` confirms this. |
| ESS not modified | ✅ | `ess_score_text` and `signal_direction` are read from `security_overlays.csv` only. No recalculation. |
| Replay not modified | ✅ | `replay_supported` read from overlay; not modified or recalculated. |
| FMI not modified | ✅ | FMI outputs not referenced in any CRA module. |
| Policy engine not modified | ✅ | Policies read from `portfolio_alignment_state.json` via `OperatorPolicyRegistry.load()`. DO_NOT_SELL blocks pool entry but is never overridden. |
| No new scoring models | ✅ | The impact estimator uses heuristic coefficients (documented as approximation). These do not modify or replace alignment scores; `is_estimate=True` always. |
| No new signal providers | ✅ | No external API calls in CRA modules. |
| No upstream artifact writes | ✅ | `test_no_upstream_files_modified` explicitly verifies the PAR run directory is unchanged after `build_rotation_proposal()`. |

---

## Operator Authority Verification

| Principle | Implementation |
|-----------|---------------|
| Guidance only | All returned values labeled as guidance; proposal is not a trade instruction |
| Policy gates respected | DO_NOT_SELL → `blocked_by_policy=True`, excluded from `total_capital_pool` |
| CORE_ANCHOR requires review | `operator_review_required=True` + added to `review_flags` |
| Impact is approximate | `is_estimate=True` on every `PortfolioImpactEstimate` |
| Auditability | Every `RotationProposal` carries `run_id`, `as_of_date`, `created_at_utc`, `cra_version` |

---

## Failure Mode Behavior

| Failure Mode | Behavior |
|-------------|---------|
| No manifest | API returns 404 with clear message |
| No COMPLETE runs | API returns 404 with clear message |
| Missing PAR files | API returns 404 via `FileNotFoundError` handler |
| No strategic_profiles.json | Cat 2 falls back to `strategic_exit_symbols` + overlay flags; no crash |
| No tax state file | Tax modifiers disabled; `tax_annotation = "No cost basis data"` |
| No cost_basis in holdings | `tax_bucket = None`; annotation surfaced |
| Empty deployment queue | `deployments = []`; `proposal_status = DRAFT` |
| All sources blocked | `total_capital_pool = 0`; `deployments = []`; `proposal_status = DRAFT` |
| Unexpected exception | API returns 500 with error message; traceback logged server-side |

---

## Scope Boundary Confirmation

Items explicitly NOT implemented (as required by governance):

| Out of Scope | Confirmed |
|-------------|-----------|
| Automated trade execution | ✅ Not present |
| Lot selection (FIFO, HIFO) | ✅ Not present |
| Wash-sale tracking | ✅ Not present |
| Predictive price modeling | ✅ Not present |
| PAR re-run or alignment engine invocation | ✅ Not present |
| Multi-account rotation | ✅ Not present |
| Portfolio construction optimizer | ✅ Not present |
| Bucket E assignment (requires holding_days) | ✅ Not present; noted as open question |

---

## Data Integrity Rules Enforcement

| Rule | Status |
|------|--------|
| `estimated_proceeds ≤ current_value_usd` | ✅ `estimated_proceeds = current_value_usd × sizing_pct`; `sizing_pct` capped at 1.0 |
| `sizing_pct ∈ [0.0, 1.0]` | ✅ All sizing constants are ≤ 1.0 |
| `deployment_score` unchanged | ✅ Direct copy from queue; verified by test |
| `rank` unchanged | ✅ Direct copy; allocation preserves rank order |
| `is_estimate = True` always | ✅ Hardcoded in `PortfolioImpactEstimate` |
| Blocked sources excluded from pool | ✅ `pool_sources = [s for s in all_sources if not s.blocked_by_policy ...]`; verified by test |
