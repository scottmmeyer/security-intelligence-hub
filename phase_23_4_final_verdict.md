# Phase 23.4 — Final Verdict
**Forensic analysis only. No implementation changes.**

Generated: 2026-06-04  
Baseline: PAR-20260603-0487E65C | 853 tests | 0 failures | 1 skip

---

## Phase objective

Design and forensically trace every source of the four actionable mandate/optimizer
blocker codes: `MANDATE_BLOCKED`, `ETF_GATE_FAILED`, `WORSENS_OVERWEIGHT`, and
`CONFLICTS_WITH_MANDATE`. Deliver a normalized blocker-explanation model and a
UI design for a new BLOCK DIAGNOSTICS section.

**Implementation constraint**: Do NOT implement. Design and forensic analysis only.

---

## Deliverables produced

| Document | Status | Summary |
|----------|--------|---------|
| `phase_23_4_block_source_inventory.md` | ✅ Complete | Full code-level trace of all 4 blocker codes |
| `phase_23_4_blocker_taxonomy.md` | ✅ Complete | Normalized 3-tier taxonomy (M / V / P types) |
| `phase_23_4_unblock_action_framework.md` | ✅ Complete | 7 frameworks: explanation + evidence + remediation + alternative |
| `phase_23_4_ui_design.md` | ✅ Complete | Full BLOCK DIAGNOSTICS UI design with HTML/CSS/JS spec |
| `phase_23_4_final_verdict.md` | ✅ This document | Summary, findings, gaps, and implementation recommendation |

---

## Key forensic findings

### Finding 1: CONFLICTS_WITH_MANDATE exists only in the UI layer

The string `CONFLICTS_WITH_MANDATE` does not appear in any Python source file. It is
generated entirely in `app.js` and co-fires with `MANDATE_BLOCKED` (they share the same
`mandate_blocked` Boolean condition). This means operators see two badges for one
underlying condition with no differentiation in meaning. This is a design debt item.

**Recommendation**: Merge `CONFLICTS_WITH_MANDATE` into `MANDATE_BLOCKED` display logic
or clarify its distinct advisory meaning (legacy vehicle conflict vs. node-level block).

---

### Finding 2: ETF_GATE_FAILED (UI name) vs. ETF_GATED (optimizer_status) mismatch

The Python optimizer writes `optimizer_status = "ETF_GATED"` but the UI renders
`ETF_GATE_FAILED`. This inconsistency creates confusion when reading data vs. UI.

**Recommendation**: Standardize to `ETF_GATE_FAILED` in both layers.

---

### Finding 3: WORSENS_OVERWEIGHT advisory is under-explained

The current `WORSENS_OVERWEIGHT` badge is a one-line advisory with no evidence fields
and no pointer to which OW node is being worsened or which specific ETFs caused it.
The conflict_penalty of 20.0 pts is invisible to operators.

**Recommendation**: Surface per-vehicle details (overlap_with_existing_pct, OW node key)
in the BLOCK DIAGNOSTICS section.

---

### Finding 4: Suggested Alternatives panel is missing entirely

The BLOCK DIAGNOSTICS spec example (from the Phase 23.4 mandate) called for surfacing
direct-security alternatives when ETFs are blocked. Currently, no alternatives are shown
on blocked recommendations — the operator is left with a dead-end banner. The deployment
queue has exactly the data needed (CW-DAS candidates by node).

**Recommendation**: Implement the Suggested Alternatives panel in Phase 23.5 using
Option A (embed top-N deployment queue candidates in the optimizer result by target_node).

---

### Finding 5: Mandate tolerance value not surfaced in optimizer output

The MANDATE_BLOCKED block row needs `concentration_tolerance` from the active mandate to
explain WHY the mandate is blocking (tolerance=0.9 → INTENTIONAL). This field exists in
`PortfolioMandate` but is not currently included in `optimizer_metadata`.

**Recommendation**: Add `mandate_type` and `concentration_tolerance` to `_build_result()`
in `optimizer.py` as Phase 23.5 prerequisites.

---

## Blocker code canonical reference

| Code | Layer | Scope | Hard block? |
|------|-------|-------|-------------|
| `MANDATE_BLOCKED` | Mandate (PMI) | Node-level | Yes — PIS = 0, no deployment |
| `ETF_GATE_FAILED` (V1-suitability) | Optimizer | Vehicle-level | ETF only (PIS × 0.3) |
| `ETF_GATE_FAILED` (V2-NCS) | Optimizer | Vehicle-level | ETF only (PIS × 0.3) |
| `ETF_GATE_FAILED` (V3-worsens OW) | Optimizer | Vehicle-level | ETF only (PIS × 0.3) |
| `WORSENS_OVERWEIGHT` | Optimizer | Vehicle-level | Advisory only (part of V3) |
| `CONFLICTS_WITH_MANDATE` | UI only | Node-level | Advisory (same condition as MANDATE_BLOCKED) |
| `BLOCKED_BY_POLICY` | Operator policy | Symbol-level | Yes — action suppressed |

---

## Normalized blocker-explanation model (data contract)

The following schema defines the target data model for a complete blocker explanation.
Fields marked (available) exist today; fields marked (gap) require Phase 23.5 work.

```
BlockDiagnostic {
    blocker_code:        string       -- MANDATE_BLOCKED | ETF_GATE_FAILED | WORSENS_OVERWEIGHT | BLOCKED_BY_POLICY
    blocker_type:        string       -- M1 | M2 | V1 | V2 | V3 | P1 | P2 | P3
    affected_symbol:     string?      -- ETF symbol (V-types) or position symbol (P-types)
    affected_node:       string       -- allocation node key (available)
    affected_node_label: string       -- human name (available)

    reason:              string       -- human explanation sentence
    evidence: {
        mandate_type:           string?   -- (gap — need to add to optimizer output)
        concentration_tolerance: float?   -- (gap)
        mandate_drift_label:    string?   -- (available on rec)
        mandate_urgency:        string?   -- (available on rec)
        raw_drift_pct:          float?    -- (available on rec)
        ncs:                    float?    -- (available on candidate)
        suitability_tier:       string?   -- (available on candidate)
        worsens_overweight:     bool?     -- (available on candidate)
        overlap_with_ow_pct:    float?    -- (gap — need from suitability note)
        ow_node_key:            string?   -- (gap — need to surface which OW node)
        etf_gate_reason:        string?   -- (available — embedded in etf_gate string)
    }
    remediation_primary:  string       -- top recommended action
    alternative_path:     AlternativeCandidate[]  -- deployment queue results (gap)
}

AlternativeCandidate {
    symbol:            string
    narrative_tier:    string
    ess_score_text:    string
    deployment_score:  float
    notes:             string
}
```

---

## Gap analysis for Phase 23.5 implementation

| Gap | Severity | Work required |
|-----|----------|--------------|
| `mandate_type` missing from `optimizer_metadata` | Medium | Add to `_build_result()` in optimizer.py (1 field) |
| `concentration_tolerance` missing | Medium | Add to `_build_result()` — read from active mandate |
| `overlap_with_ow_pct` and `ow_node_key` not surfaced per failed ETF | Medium | Enhance `score_etf_candidate()` to include these in etf_gate evidence |
| Suggested Alternatives panel | High | Two options: embed in optimizer (preferred) or separate API |
| `CONFLICTS_WITH_MANDATE` / `ETF_GATED` naming inconsistency | Low | Standardize string values |

---

## Certification

**Phase 23.4 design is COMPLETE.**

All 5 design documents have been produced. No code has been modified. All forensic traces
are grounded in exact line numbers from the production codebase.

Codebase baseline state at certification:
- Tests: 853 passing, 0 failing, 1 skip
- Certification ID: PAR-20260603-0487E65C
- Analytical universe: 2026-06-04 snapshot, 2,473 rows
- Active policies: TSLA DO_NOT_SELL | DODFX SELL_LAST

**PHASE 23.4 CERTIFIED — DESIGN COMPLETE — NO IMPLEMENTATION**

---

*Phase 23.4 — Design document 5 of 5.*
