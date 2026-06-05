# Phase 23.2 — Operator Portfolio Policy Framework: Requirements

**Date:** 2026-06-03
**Status:** DESIGN APPROVED — PENDING IMPLEMENTATION
**Predecessor:** Phase 23.1 (Reconciliation: 12/13 PASS, 1 WARN, 0 FAIL certified)

---

## 1. Motivation

The Security Intelligence Hub correctly identifies candidate portfolio actions based on:
- ESS / Zacks / Danelfin signal data
- Replay return percentiles
- CCL conviction tier classifications
- CW-DAS composite scoring
- Allocation alignment drift calculations

However, the operator may hold **intentional, policy-driven positions** that the intelligence engine cannot contextually distinguish from execution-eligible positions.

Current architecture: `Intelligence → Action`
Required architecture: `Intelligence → Operator Policy → Action`

### Concrete Problem Cases

| Symbol | Intelligence Signal | Engine Action | Operator Intent |
|--------|--------------------|--------------:|-----------------|
| TSLA | VERY_BEARISH (ESS 1.5) | TRIM | DO NOT SELL — strategic hold |
| DODFX | UNKNOWN signal | HOLD | SELL LAST — intentional legacy |
| MU | Strong anchor | Retain | CORE ANCHOR — protect from trims |
| VRT | CORE_CONVICTION_LEADER | Buy | PREFERRED — prioritize accumulation |
| ARW | High CW-DAS rank | Buy | PREFERRED — prioritize accumulation |

---

## 2. Scope

### In Scope
- Policy type taxonomy (4 types: Phase 23.2)
- Per-symbol policy data model and persistence
- Policy application layer (post-intelligence, pre-execution)
- Policy annotation in security overlays and deployment queue
- API endpoints for policy management
- UI panel for policy administration
- Backward compatibility with existing PAR data
- Governance audit constraints

### Out of Scope
- Intelligence score modification (hard constraint — never allowed)
- Automated policy generation (operator-driven only)
- Bulk policy import
- Multi-portfolio policy isolation (single portfolio scope — Phase 23.2)
- Policy-driven rebalancing triggers (Phase 23.3 candidate)

---

## 3. Critical Constraint (Non-Negotiable)

**Policies MUST NOT modify:**
- ESS scores (`ess_score_text`)
- Composite scores (`composite_score`)
- Replay return percentiles (`replay_percentile`, `best_replay_return`)
- Conviction tier classifications (`narrative_tier`, CCL tier)
- CW-DAS scores (`cw_das_score`, `deployment_score`)
- STI classifications (`signal_direction`, `opportunity_flag` intelligence value)
- Zacks or Danelfin ratings

**Policies MAY modify:**
- Deployment queue entry rank ordering
- Sell queue inclusion/exclusion
- Execution annotations (distinct from intelligence annotations)
- Category execution priority ordering
- Recommendation narrative annotations

This constraint is enforced architecturally: the policy engine operates on a separate output layer and receives read-only access to intelligence data.

---

## 4. Required Policy Types (Phase 23.2)

### Policy 1: DO_NOT_SELL
- Symbol is excluded from all sell/trim execution queues
- Intelligence overlay remains fully visible (TRIM flag still shown)
- Policy annotation appears alongside intelligence: `[OPERATOR PROTECTED]`
- Cannot override: allocation ceiling enforcement, reconciliation

### Policy 2: SELL_LAST
- Symbol remains in sell queue
- Always ranked after all unprotected candidates in the same category
- Within the sell-last cohort, tax-aware ranking applies
- Annotation: `[SELL LAST]`

### Policy 3: CORE_ANCHOR
- Symbol is in active accumulation; protect from trim recommendations
- Trim recommendations receive an additional confirmation gate (UI warning)
- Does NOT suppress the trim recommendation — it adds friction
- Annotation: `[CORE ANCHOR — confirm trim]`

### Policy 4: PREFERRED_ACCUMULATION
- Buy/add recommendations for this symbol receive priority boost in deployment queue
- Boost applied as a post-scoring rank adjustment (not a score change)
- Annotation: `[PREFERRED ACCUMULATION]`

---

## 5. Required Q&A

### Q1: Should policies be stored by symbol?
**YES.** Policies are per-security operator decisions. A symbol-keyed dictionary is unambiguous, directly addressable, and consistent with how all other SIH per-holding overrides work (ETF override registry, contra lot registry). Storing by symbol also ensures policies are portable across portfolio uploads (same symbol, new upload = policy still applies).

### Q2: Should policies survive portfolio uploads?
**YES.** Policies represent operator intent that is independent of portfolio state. A new portfolio upload that includes TSLA should continue to honor the DO_NOT_SELL policy. A new upload that excludes TSLA leaves the policy dormant (not deleted). Policies persist until explicitly revoked by the operator. This mirrors the existing behavior of `strategic_exit_symbols` in `portfolio_alignment_state.json`.

### Q3: How should policies interact with tax-aware ranking?
Policy takes precedence over tax-aware ranking for execution suppression. For `DO_NOT_SELL`, the position is excluded regardless of tax bucket. For `SELL_LAST`, the position appears at the end of the sell queue; within the SELL_LAST cohort, tax-aware ranking still applies (e.g., two SELL_LAST symbols would be ordered by tax context among themselves). Precedence hierarchy: **Policy suppression > Tax bucket ranking > Intelligence rank.**

### Q4: How should policies interact with PAP categories?
PAP categories (Cat1–Cat4) are produced by the alignment engine and remain unchanged. Policy applies a **post-categorization execution filter** to the deployment queue. A Cat2 position with `DO_NOT_SELL` retains Cat2 status for all reporting and reconciliation purposes — the policy modifies only execution queue ordering. Category assignments are never altered by policy.

### Q5: Should protected positions remain visible?
**YES — always.** All holdings appear in intelligence overlays regardless of policy. Policy badges are additive to the existing overlay UI. A DO_NOT_SELL position continues to display ESS, replay, conviction, and flag data. Suppressing visibility would undermine governance transparency and the operator's ability to monitor whether a protected position's intelligence case changes over time.

### Q6: Can policies create governance risk?
**YES — with required mitigations:**

| Risk | Severity | Mitigation |
|------|----------|-----------|
| DO_NOT_SELL prevents timely exit from deteriorating position (e.g., TSLA VERY_BEARISH continues) | Medium | Intelligence signal always visible; policy badge explicitly shown; never suppressed from overlay |
| PREFERRED_ACCUMULATION causes concentration drift | Medium | Allocation ceiling enforcement is never bypassed; policy cannot override allocation hard limits |
| Stale policies (forgotten over time) | Low | `created_at` timestamp required; optional `expires_at` supported; governance audit trail in policy registry |
| Policy conflicts (DO_NOT_SELL + SELL_LAST on same symbol) | Low | Conflict detection at write time; POST returns 409 if conflict detected |
| Policy disguising insider motivation | Low (single-user system) | Full audit trail; policies written to persistent registry with timestamps |

---

## 6. Non-Requirements (Explicitly Excluded)

- Policy engine does not rerun reconciliation (reconciliation reads intelligence data, which policies do not alter)
- Policy engine does not touch `holdings.csv`, `alignment.csv`, or `recommendations.json` outputs
- Policy engine does not interact with the ESS 30-day effectiveness tracker
- Policies are not per-account (all apply portfolio-wide in Phase 23.2)

---

## 7. Acceptance Criteria

The implementation is complete when:

1. `data/operator/portfolio_alignment_state.json` contains `operator_policies` key with symbol-keyed policy entries
2. `GET /api/operator/policies` returns current policy registry
3. `POST /api/operator/policies` accepts `{symbol, policy_type, rationale}` and persists
4. `DELETE /api/operator/policies/{symbol}` removes a policy
5. TSLA with `DO_NOT_SELL` does not appear in any trim/sell execution queue but retains full intelligence overlay
6. DODFX with `SELL_LAST` appears last in sell queue behind unprotected candidates
7. All intelligence scores for TSLA and DODFX are identical to pre-policy values
8. Policy badges appear in the Portfolio Alignment UI security overlay panel
9. Reconciliation continues to pass (policy layer is post-reconciliation)
10. All existing tests pass; new policy unit tests added
