# Phase 23.4A — Q8: Final Verdict
**DESIGN ONLY — NO IMPLEMENTATION**
**Generated:** 2026-06-04
**Baseline:** PAR-20260604-8DB0393D | 853 tests | 0 failures | 1 skip

---

## 1. Five Design Questions — Answers

### Q1: Does Next Best Action improve operator usability?

**YES — definitively.**

The current workflow terminates at a block badge. The operator knows their action was blocked but receives no forward guidance. From the canonical examples:

- **Case A (EQUITIES.US.LARGE MANDATE_BLOCKED):** The operator sees "VOO blocked" and must independently consult the deployment queue, cross-reference ESS, verify execution states, and identify VRT/ARW/DELL as alternatives. The NBA panel collapses this to a single scannable table. Time to first actionable step: reduced from ~5 manual steps to 0.
- **Case B (TSLA DO_NOT_SELL):** The operator sees "TRIM blocked" and might search for whether any sell path exists. The NBA panel makes the answer immediate: "MONITOR ONLY — no action available." The value is clarity, not alternatives.

Both archetypes (execution-focused, oversight-focused) benefit. The framework does not reduce information — it reorganizes it to match the operator's primary decision need.

**Verdict: YES — NBA improves usability in all tested scenarios.**

---

### Q2: Should it appear before diagnostics?

**YES — NBA before Diagnostics.**

Evidence from Q1 workflow analysis:
- Operators come to the UI to deploy capital, not to audit the mandate engine
- "What do I do instead?" is the primary question; "Why was this blocked?" is secondary reference material
- Expert operators rarely need the diagnostic detail; new operators need the action guidance most
- The redesigned section order (NBA → Alternatives → Why Blocked → Evidence → Unblock) ensures the operator reaches an actionable answer before encountering explanatory content
- Collapsible Diagnostics sections mean expert operators can expose them; non-expert operators are not forced to navigate them

The current Phase 23.3 state has badges but no forward path. Phase 23.5 must not simply add a diagnostics panel — it must answer the operator's actual question first.

**Verdict: YES — NBA must appear before diagnostics. The section order in Q5 UI design is correct.**

---

### Q3: Can alternatives be generated using existing CW-DAS outputs?

**YES — with one known gap.**

The deployment queue (`deployment_queue.json`) produced by CW-DAS in each PAR run contains:
- Symbol, deployment_score, narrative_tier, notes (headroom), rank
- Sufficient to generate ranked alternative lists for all MANDATE_BLOCKED, ETF_GATE_FAILED, and WORSENS_OVERWEIGHT cases

Cross-referencing `security_overlays.csv` provides `execution_state` for the EXECUTABLE filter.

The gap: `allocation_node` per `DeploymentCandidate` is not currently in `deployment_queue.json`. This field is needed for the OW-node exclusion filter in ETF_GATE_FAILED and WORSENS_OVERWEIGHT paths. The fallback behavior (surface all top-5 without node filter, add operator caveat) is acceptable for Phase 23.5. Adding `allocation_node` to `DeploymentCandidate` output is a small Python change (~10–15 lines) that should be included in Phase 23.5.

**Verdict: YES — alternatives can be generated from existing outputs. One small Python addition (`allocation_node`) recommended but not blocking.**

---

### Q4: Can this be implemented without affecting scoring?

**YES — provably.**

The constraint: "NOT alter optimizer scoring, NOT alter CW-DAS, NOT alter ESS, NOT alter replay, NOT alter conviction, NOT alter mandate logic."

The full non-change manifest from Q7:
- 0 changes to `optimizer.py` scoring logic
- 0 changes to `mandate.py`
- 0 changes to `deployment_queue.py` CW-DAS formula
- 0 changes to ESS pipeline
- 0 changes to replay engine
- 0 changes to conviction model
- 0 changes to `operator_policy.py`

The only Python changes are **additive**: 4 new optional output fields in `optimizer_metadata` (`mandate_type`, `concentration_tolerance`, `overlap_with_ow_pct`, `ow_node_key`) and optionally `allocation_node` in `DeploymentCandidate`. These are read-only metadata — they do not influence any score computation.

The NBA layer is a **filtered read-only projection** over existing pipeline outputs. It does not recompute scores, does not rerank securities in the pipeline, and does not modify any data structure that feeds into scoring.

**Verdict: YES — scoring integrity is fully preserved. Constraint is satisfied.**

---

### Q5: Should Phase 23.5 implement DIAGNOSTICS ONLY or DIAGNOSTICS + NEXT BEST ACTION?

**DIAGNOSTICS + NEXT BEST ACTION.**

See Section 2 below for full recommendation rationale.

---

## 2. Phase 23.5 Recommendation

### **PHASE 23.5: DIAGNOSTICS + NEXT BEST ACTION**

**Rationale:**

1. **Logical coupling:** The BLOCK DIAGNOSTICS card section order (NBA first, diagnostics collapsed below) cannot be correctly designed for DIAGNOSTICS ONLY — you'd be shipping a panel that's in the wrong order from day one. Shipping DIAGNOSTICS ONLY means a layout redesign is required when NBA is added in Phase 23.6.

2. **No additional risk from including NBA:** The NBA layer is frontend-only (except 4 additive backend fields). It adds ~275–380 frontend lines alongside the ~150–200 lines of DIAGNOSTICS. Total scope is MEDIUM — bounded and well-understood.

3. **Data already available:** The deployment queue is already loaded by `app.js`. The generation logic is O(N) over a small dataset (≤32 entries). There is no infrastructure required.

4. **Highest user value is unlocked together:** A blocked recommendation panel that explains "why" but not "what instead" is only half of the operator's need. DIAGNOSTICS answers the explanation question; NBA answers the decision question. Both are required for the panel to be complete.

5. **Test impact is minimal:** All Python changes are additive to `optimizer_metadata`. No existing test assertions are invalidated. New tests add assertions on the 4 new fields.

### Phase 23.5 Scope

```
BACKEND (src/portfolio/optimizer.py):
  - Add mandate_type to _build_result() output
  - Add concentration_tolerance to _build_result() output  
  - Add overlap_with_ow_pct to ETF candidate output
  - Add ow_node_key to ETF candidate output
  - (Optional) Add allocation_node to DeploymentCandidate

FRONTEND (ui/portfolio_alignment/app.js):
  - _buildNextBestAction(r, deploymentQueue, overlaysBySymbol)
  - _renderBlockDiagnosticsPanel(r, nba, deploymentQueue)
  - _buildWhyBlocked(r)
  - _buildEvidence(r)
  - _buildHowToUnblock(r)
  - Integration: wire panel into recommendation card renderer
  - CSS: new .nba-panel, .alternatives-table, .diagnostics-section classes

TESTS:
  - test_optimizer_metadata_includes_mandate_type
  - test_optimizer_metadata_includes_concentration_tolerance
  - test_etf_candidate_includes_ow_context
  - (Integration): test_nba_generated_for_mandate_blocked_node
```

---

## 3. Success Criteria

**The design is successful if:**

> "If I cannot do this recommendation, what should I do instead?" can be answered by looking at a single panel — without requiring manual interpretation of mandates, ETF gates, or the deployment queue.

**Test against canonical cases:**

| Scenario | Question | NBA Answer | Success? |
|---|---|---|---|
| EQUITIES.US.LARGE MANDATE_BLOCKED | "VOO is blocked — what do I buy?" | VRT, ARW, PSX, DELL, AVT | YES |
| TSLA DO_NOT_SELL | "I want to trim TSLA — what can I do?" | MONITOR ONLY — policy blocks all action | YES |
| FIS Strategic Exit | "Should I redeploy FIS capital?" | Not in scope — not a blocked recommendation | CORRECT SCOPE BOUNDARY |

**The criterion is satisfied.** The operator receives a direct answer in all in-scope scenarios without any external reference lookup.

---

## 4. Data Contract Summary

```
NextBestAction {
    blocker_type:             string   // MANDATE_BLOCKED | ETF_GATE_FAILED | WORSENS_OVERWEIGHT | BLOCKED_BY_POLICY
    blocked_symbol:           string?  // null for node-level blocks
    blocked_node:             string?  // null for security-level blocks
    action_type:              string   // ACCUMULATE | MONITOR_ONLY | DEFERRED_REDUCE | HOLD
    action_priority:          string   // HIGH | MEDIUM | LOW | INFORMATIONAL
    rationale:                string   // 1-sentence human explanation
    candidate_symbols:        string[] // ranked, max 5
    deployment_scores:        number[] // parallel to candidate_symbols
    narrative_tiers:          string[] // parallel
    execution_states:         string[] // parallel
    expected_portfolio_effect: string  // IMPROVES_ALIGNMENT | NEUTRAL | MAINTAINS_DRIFT
    headroom_available:       boolean
    generation_source:        string   // DEPLOYMENT_QUEUE | NONE
    alternatives_count:       number
    no_action_available:      boolean
}
```

---

## 5. Gap Table (Phase 23.6 and Beyond)

| Gap | Phase |
|---|---|
| `CONFLICTS_WITH_MANDATE` badge has no Python source (JS-only, fires on same condition as `MANDATE_BLOCKED`) | 23.5 cleanup |
| `ETF_GATED` (Python) vs `ETF_GATE_FAILED` (UI badge) naming inconsistency | 23.5 cleanup |
| `allocation_node` per `DeploymentCandidate` for precise OW-node filtering | 23.5 optional |
| FIS/WATCH strategic exit redeployment path | 23.6+ |
| Policy clearance timeline ("when will DO_NOT_SELL lift?") | 23.6+ |
| Capital availability model (what-if analysis for position reduction) | 23.7+ |

---

## 6. Certification

This document certifies the completion of Phase 23.4A design work.

**Findings:**
1. NBA improves operator usability — answers "what do I do instead?" without manual queue lookup
2. NBA must precede diagnostics in section order — operator decision need takes priority over explanation
3. CW-DAS deployment_queue outputs are sufficient to generate alternatives — no new scoring infrastructure needed
4. Implementation satisfies all scoring integrity constraints — zero impact on optimizer, CW-DAS, ESS, replay, conviction, mandate
5. Phase 23.5 should implement DIAGNOSTICS + NBA combined — splitting into two phases creates needless layout churn

**Recommendation: PHASE 23.5 — DIAGNOSTICS + NEXT BEST ACTION**

---

**PHASE 23.4A CERTIFIED — DESIGN COMPLETE — NO IMPLEMENTATION**

Baseline preserved: 853 tests | 0 failures | 1 skip | PAR-20260603-0487E65C
