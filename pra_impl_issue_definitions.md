# PRA Implementation Issue Definitions

Project: Security Intelligence Hub (SIH)  
Type: Implementation planning reference  
Date: 2026-06-08

---

## PRA-IMPL-01 — Typed Recommendation Contract and Card Schema

### Problem Statement

SIH recommendation outputs currently lack a shared semantic type field. Actions, observations, narrative items, and explainability artifacts all render as undifferentiated cards with no machine-readable classification. This makes truthful counting, lane routing, and policy-state composition impossible without additional infrastructure.

### Implementation Scope

Additive JSON schema fields on recommendation card output:

| Field | Type | Values |
|---|---|---|
| `card_type` | string | ACTION, OBSERVATION, NARRATIVE, EXPLAINABILITY, DIAGNOSTIC |
| `execution_state` | string | EXECUTABLE, BLOCKED_BY_POLICY, DEFERRED_BY_POLICY, INFORMATIONAL_ONLY |
| `effective_action` | string | action verb or MONITOR_ONLY, REDUCE_SELL_LAST |
| `evidence_link` | string or null | reference ID for supporting evidence artifact |
| `card_lifecycle_state` | string | OBSERVED, ACTION_QUALIFIED, POLICY_ADJUSTED, DECISION_PENDING, EXECUTED |

These fields are additive. No existing fields are removed. No scoring is changed.

### Acceptance Criteria

1. All recommendation card objects in `recommendations.json` carry `card_type` field.
2. `card_type` value set is constrained to canonical five-class enum.
3. `execution_state` field present with a valid value on all ACTION cards.
4. `effective_action` present on all ACTION cards with execution state other than INFORMATIONAL_ONLY.
5. Field defaults to safe values (DIAGNOSTIC or OBSERVATION) for any card not explicitly classified.
6. Existing test suite passes without modification (additive only).

### Dependencies

None. This is the foundation for all other PRA-IMPL children.

### Implementation Risk

Low. Purely additive JSON schema extension; no scoring, ranking, or methodology changes.

### Labels

enhancement, governance, recommendation-engine, priority-high, ready

---

## PRA-IMPL-02 — Policy-Aware Funding Sources and Allocation Reduction

### Problem Statement

DO_NOT_SELL and SELL_LAST policies currently apply execution gates in the deployment queue and Strategic Exit surface but are not propagated consistently to Funding Sources and Allocation Reduction. This creates cross-surface policy divergence: a symbol blocked from execution in one surface may still appear as an executable candidate in another.

### Implementation Scope

**Funding Sources — DO_NOT_SELL:**
- Symbol excluded from executable funding source candidate list.
- Symbol remains visible in a policy-suppressed transparency section.
- Explanation: "[Symbol] excluded from funding candidates — DO_NOT_SELL policy active."
- execution_state: BLOCKED_BY_POLICY
- effective_action: MONITOR_ONLY

**Funding Sources — SELL_LAST:**
- Symbol remains in list, ranked at tail of funding cohort behind non-SELL_LAST candidates.
- Badge: "⏸ Sell Last — liquidation last resort"
- execution_state: DEFERRED_BY_POLICY when funding action exists

**Allocation Reduction — DO_NOT_SELL:**
- Reduction intelligence still computed and displayed (truth preserved).
- execution_state: BLOCKED_BY_POLICY
- effective_action: MONITOR_ONLY
- UI badge: "🔒 Operator Protected — not executable"

**Allocation Reduction — SELL_LAST:**
- Reduction recommendation visible; ranked below non-SELL_LAST candidates.
- execution_state: DEFERRED_BY_POLICY
- effective_action: REDUCE_SELL_LAST
- UI badge: "⏸ Sell Last"

### Acceptance Criteria (12 required)

1. Funding Sources + DO_NOT_SELL → BLOCKED_BY_POLICY, not executable, visible with badge
2. Funding Sources + SELL_LAST → tail-ranked, DEFERRED_BY_POLICY, badge visible
3. Allocation Reduction + DO_NOT_SELL → BLOCKED_BY_POLICY / MONITOR_ONLY
4. Allocation Reduction + SELL_LAST → DEFERRED_BY_POLICY / REDUCE_SELL_LAST
5. Strategic Exit + DO_NOT_SELL → BLOCKED_BY_POLICY / MONITOR_ONLY
6. Strategic Exit + SELL_LAST → DEFERRED_BY_POLICY, tail-ranked
7. CRA + DO_NOT_SELL → advisory-only, not in executable reduce sequence
8. CRA + SELL_LAST → deferred priority
9. PAP + DO_NOT_SELL → policy_suppressed section
10. PAP + SELL_LAST → tail of sell cohort
11. Any surface + non-sell action + DO_NOT_SELL → EXECUTABLE (policy does not block non-sell)
12. Any surface + any active policy → intelligence signal always visible alongside policy effect

### Must Not Change

- CW-DAS composite scores
- ESS signal values
- Reconciliation inputs
- Dislocation intelligence scores

### Dependencies

PRA-IMPL-01 (card schema fields)

### Implementation Risk

Low-Medium. Execution state propagation extends existing `apply_policy_to_queue` pattern to two additional surfaces; no scoring risk.

### Labels

enhancement, governance, ui-ux, policy-engine, priority-high, ready

---

## PRA-IMPL-03 — Recommendation Surface Lane Separation and Typed Counts

### Problem Statement

The current Allocation and Portfolio Observations panel presents all card types — actions, observations, conviction narrative, and explainability artifacts — in a single undifferentiated stream with a single aggregate count (e.g., "34 Recommendations"). This overstates actionable workload approximately 5x and prevents operators from focusing on genuine decision tasks.

### Implementation Scope

**Typed count header:**
- Replace single aggregate with: Actions: N | Observations: N | Conviction Anchors: N | Explainability: N
- Total Cards count remains accessible but is not the primary KPI.
- "Recommendations" label reserved for ACTION class cards only.

**Four UI lanes driven by card_type:**
1. Action Queue — ACTION cards only
2. Observation Monitor — OBSERVATION and DIAGNOSTIC
3. Conviction Anchors — NARRATIVE and conviction-class OBSERVATION
4. Explainability Workspace — EXPLAINABILITY (collapsed by default)

**Card routing logic:**
- card_type field (from PRA-IMPL-01) governs lane assignment at render time.

### Acceptance Criteria

1. Header displays typed counts, not a single aggregate.
2. Action Queue contains only cards with concrete action verb and valid execution_state.
3. High Conviction Retain cards do not appear in Action Queue.
4. Conviction Anchors section renders NARRATIVE and conviction-class OBSERVATION items.
5. Total card count remains accessible via secondary display.
6. Existing action functionality (click, drill-down, execute) unchanged.

### Must Not Change

- Intelligence scoring or conviction tier computation
- UCF verdict outputs
- STI profile generation

### Dependencies

PRA-IMPL-01 (card_type field), PRA-IMPL-02 preferred before final UX polish

### Implementation Risk

Medium. UI rendering changes; no backend scoring risk.

### Labels

enhancement, ui-ux, governance, recommendation-surface, priority-medium, ready

---

## PRA-IMPL-04 — Conviction Anchors Section Extraction

### Problem Statement

High Conviction Retain cards (MSFT, ARW, VRT, CVE, etc.) currently appear in the main recommendation stream alongside sell and rebalancing actions. These cards assert confidence in current posture — they are observations, not action directives. Their presence in the action stream inflates recommendation counts and dilutes the salience of genuine action items.

### Implementation Scope

- Create dedicated Conviction Anchors UI section.
- Move cards classified as NARRATIVE or conviction-class OBSERVATION out of Action Queue.
- Display UCF tier (CCL, HCA, TGC, WTC) and supporting conviction context per anchor.
- Cross-link from Conviction Anchor entry to related deployment or reduction action where applicable.
- Remove anchor cards from Actions count; route to Conviction Anchors count.

### Acceptance Criteria

1. High Conviction Retain, Strategic Retain Signal, and Conviction Anchor card types do not appear in Action Queue.
2. Conviction Anchors section renders these items with UCF tier label and conviction evidence.
3. Conviction Anchors count in header updates accordingly.
4. Actions count decreases to reflect true executable workload.
5. Cross-links to related action cards (if any) are functional.

### Dependencies

PRA-IMPL-03 (lane separation and typed count header)

### Implementation Risk

Low-Medium. Primarily a UI classification and routing change; no intelligence or scoring changes.

### Labels

enhancement, ui-ux, sti, recommendation-surface, priority-medium, ready

---

## PRA-IMPL-05 — FVI Advisory Overlay for Allocation Reduction

### Problem Statement

SIH evaluates mutual fund holdings (e.g., DODFX) using sleeve allocation positioning, but has no awareness of fund vehicle quality. A fund may appear as an allocation reduction candidate solely because its sleeve is overweight, even when the fund itself may be an elite-tier vehicle. SIH cannot currently distinguish "reduce sleeve exposure" from "replace fund vehicle."

### Implementation Scope

Phase-1 advisory-only:
- Fund quality label (LOW / MEDIUM / HIGH / ELITE) computed from three percentile inputs:
  1. Category-relative risk-adjusted return percentile
  2. Expense ratio percentile within category
  3. Downside capture percentile
- Label displayed as advisory context on Allocation Reduction cards for mutual fund holdings.
- Peer group configuration per held fund (minimum: DODFX → Foreign Large Value).
- Advisory display only — no modification to CW-DAS scores, conviction tiers, or ranking.
- Policy × FVI combined display: SELL_LAST and ELITE render as independent states (not merged).
- Suggested narrative: "International sleeve reduction recommended — DODFX quality: ELITE. Consider alternative reduction vehicles first."

Explicitly excluded from phase-1:
- Replacement recommendation generation
- FVI influence on CRA ranking
- Scoring integration
- Full-universe fund coverage

### Acceptance Criteria

1. Mutual fund holdings in Allocation Reduction surface display FVI quality label.
2. Quality label is advisory-only; no score fields are modified.
3. ELITE/HIGH quality label is accompanied by "consider retaining vehicle" advisory text.
4. FVI label and policy badge (SELL_LAST) appear as independent elements on same card.
5. Peer group configuration is stored externally (YAML/JSON), not hardcoded.
6. Cards without FVI data display gracefully without label.

### Pre-Implementation Requirement

A peer group mapping configuration file must be created before implementation:
- Maps held mutual fund tickers to canonical peer category.
- Minimum entry: DODFX → Foreign Large Value.

### Dependencies

PRA-IMPL-01, PRA-IMPL-02, PRA-IMPL-03

### Implementation Risk

Low-Medium after dependencies exist. Main risk is data availability; mitigated by accepting manual/semi-automated ingestion for phase-1.

### Labels

enhancement, governance, fvi, recommendation-engine, priority-medium, needs-data
