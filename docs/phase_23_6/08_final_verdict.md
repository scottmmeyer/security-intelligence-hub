# Phase 23.6 — Capital Rotation Advisor
## Deliverable 8: Final Verdict

**Date:** 2026-06-04
**Status:** Design Phase — Ready for Implementation Decision

---

## 8.1 Executive Summary

The Capital Rotation Advisor (CRA) is a read-only composition layer that connects the system's existing sell signals to its existing buy queue. It introduces no new scoring models, no new data sources, and no automated execution. It is the operational bridge between signal intelligence and portfolio action.

**Verdict: APPROVED FOR IMPLEMENTATION**

The design is coherent, architecturally clean, and implementable within the existing system boundaries. All non-negotiable constraints are satisfied.

---

## 8.2 Problem Resolution Summary

| Original Problem | CRA Solution | Status |
|-----------------|-------------|--------|
| "What should I sell?" | 5-category capital source taxonomy with priority ranking | ✅ Solved |
| "How much?" | Sizing heuristics per category; estimated_proceeds per source | ✅ Solved |
| "What do I buy with proceeds?" | Proceeds allocated to CW-DAS queue in rank order | ✅ Solved |
| "What will this do to my portfolio?" | PortfolioImpactEstimate with delta calculations | ✅ Solved (approximate) |
| "What's the tax angle?" | Tax bucket modifier from Phase 23.0A infrastructure | ✅ Solved |
| "Am I violating any policies?" | Policy gates surfaced on every source card | ✅ Solved |

---

## 8.3 Design Strengths

1. **Fully additive.** Every CRA output reads from existing system artifacts. Nothing upstream is touched.

2. **Transparent.** Every capital source card shows its evidence chain. Every deployment target shows its unmodified CW-DAS rank and score. Every impact estimate is labeled as approximate.

3. **Operator-centric.** Include/Skip controls, policy gate display, OPERATOR_REVIEW_REQUIRED status, and draft persistence all reinforce operator authority.

4. **Degradation-safe.** If STI profiles, tax data, or deployment queue are unavailable, the CRA degrades gracefully with clear messaging rather than failing or showing corrupted data.

5. **Complete data contract.** All input/output schemas are fully specified. Implementation can proceed without additional design rounds.

---

## 8.4 Design Risks and Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| Operator over-relies on approximate impact estimate | Medium | Persistent "Approximate" label; "Run Full Re-Analysis" button always visible |
| Sizing heuristics feel arbitrary | Medium | All sizing heuristics are documented and override-friendly (operator uses Include/Skip) |
| Tax bucket assignment inaccurate (no cost_basis) | High (common) | "No cost basis data" annotation; tax modifier not applied if bucket unknown |
| CRA surfaces a rotation that makes alignment worse | Low | Alignment delta estimate would show negative delta; operator reviews before acting |
| Deployment queue stale when CRA is rendered | Low | PAR run timestamp shown; staleness warning if run > 24 hours old |

---

## 8.5 Implementation Plan (Phased)

### Phase 23.6A — Backend Core (Recommended First)
- `src/portfolio/cra/capital_source_builder.py` — builds CapitalSourceRecords from overlays + STI + alignment
- `src/portfolio/cra/rotation_proposal_builder.py` — assembles RotationProposal
- `src/portfolio/cra/impact_estimator.py` — computes PortfolioImpactEstimate
- `scripts/run_outcome_ui.py` — add `/api/cra/proposal` endpoint
- Unit tests for capital source detection logic and sizing heuristics

### Phase 23.6B — UI Integration
- New `renderCapitalRotationAdvisor()` function in `app.js`
- Three-column layout (Sources / Rotation Map / Impact)
- Source card with Include/Skip controls
- Rotation map visualization
- Impact panel

### Phase 23.6C — Draft Persistence and Export
- `POST /api/cra/proposal/draft` endpoint
- Draft load on page load
- CSV export of rotation proposal
- Clipboard copy of rotation summary

---

## 8.6 Estimated Complexity

| Phase | Backend | Frontend | Tests | Total Estimate |
|-------|---------|---------|-------|----------------|
| 23.6A | ~350 lines | 0 | ~150 lines | Moderate |
| 23.6B | ~40 lines (endpoint) | ~300 lines | ~50 lines | Moderate |
| 23.6C | ~80 lines | ~100 lines | ~30 lines | Light |

No new dependencies required. No schema migrations required. No modifications to existing modules.

---

## 8.7 Success Criteria

Phase 23.6 is complete when:

1. Given a loaded PAR run, `GET /api/cra/proposal` returns a valid RotationProposal with at least one CapitalSourceRecord and at least one RotationDeploymentTarget (assuming portfolio has sell signals and queue entries).

2. The UI renders the three-column CRA panel with source cards, rotation map, and impact summary.

3. Operator can include/skip sources and the rotation map updates accordingly.

4. DO_NOT_SELL blocked sources appear on source column as blocked (greyed, lock icon), excluded from capital pool.

5. Tax bucket modifier correctly elevates Bucket A sources and defers Bucket E sources.

6. All non-negotiables pass governance check (no modifications to CW-DAS, ESS, Replay, FMI, Policy engine).

7. Unit tests pass for capital source detection in each of the five categories.

---

## 8.8 Open Questions for Implementation

1. **Minimum lot size threshold** — default $500 proposed. Confirm with operator context.
2. **Alignment delta formula coefficients** — the simplified scoring (+4 per resolved OW node, etc.) should be calibrated against actual PAR run deltas from historical data before labeling as "guidance."
3. **Draft retention policy** — how long to retain old rotation drafts? Recommend 90 days then manual cleanup.
4. **Strategic profiles availability** — if Phase D STI profiles are not in the PAR output, Category 2 (Strategic Exit) falls back to opportunity_flag=TRIM only. This should be documented in the source card.

---

*Design complete. All 8 deliverables produced. Proceed to Phase 23.6A implementation on operator approval.*
