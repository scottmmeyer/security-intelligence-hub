# AI-001 Option B — Final Recommendation

Repository: security-intelligence-hub  
Date: 2026-06-09

## Summary

AI-001 Option B should be implemented. The design is complete, the thresholds are grounded in real portfolio data, and the implementation is additive with no risk to existing scoring or recommendation logic.

---

## Q1 — Which Ceilings Should Be Monitored?

Eight rules recommended for v1:

| ID | Rule | Policy Value | Today's Status |
|---|---|---|---|
| CPV-01 | Combined Micro Cap | max 5% | ADVISORY (+3.33pp) |
| CPV-02 | Mega Cap | max 50% | OK |
| CPV-03 | Digital Assets | max 8% | OK |
| CPV-04 | Cash Floor | min 2% | OK |
| CPV-05 | International Min | min 10% | OK |
| CPV-06 | Single Asset Class Max | max 80% | ADVISORY (+4.86pp) |
| CPV-07 | Equities Min | min 40% | OK |
| CPV-08 | Fixed Income Max | max 40% | OK |

Excluded from v1: `max_single_sector_pct` (sector data not reliably available at PAR alignment level).

---

## Q2 — What Tolerance Bands Are Appropriate?

Three-tier model: OK → ADVISORY → WARN → FAIL.

Recommended defaults are calibrated against today's actual portfolio to avoid false WARN signals from normal drift:
- CPV-01 Micro Cap: advisory=2pp, warn=4pp (today's breach=3.33pp → ADVISORY, not WARN)
- CPV-06 Asset Class: advisory=5pp, warn=10pp (today's breach=4.86pp → ADVISORY, not WARN)
- CPV-03 Digital: tighter (advisory=1pp, warn=2pp) reflecting hard-cap governance design

Today's portfolio: 2 ADVISORY, 0 WARN, 0 FAIL. This is the correct sensitivity for routine operations.

---

## Q3 — Should WARN and FAIL Be Configurable?

**Yes.** Add a `compliance_tolerance` section to `config/allocation_policy.yaml`. Benefits: governed, versioned, no code changes for threshold adjustments.

---

## Q4 — How Should Results Appear in Allocation Intelligence?

Three-layer display:
1. **Current Portfolio Compliance bars**: replace "OVER" with ADVISORY/WARN/FAIL + breach amount
2. **Governance banner**: appears only when WARN or FAIL is present
3. **Validator grid**: new "Current Portfolio Compliance" group below strategic target validators

---

## Q5 — Should Any Validator Affect Recommendation Generation?

**No.** The validator is informational governance only. Recommendation generation (REDUCE_OVERWEIGHT, INCREASE_UNDERWEIGHT etc.) is driven by drift from strategic targets; the compliance validator operates in a separate, informational lane.

---

## Q6 — Governance Model

Graded Advisory with Hard Stop threshold. ADVISORY → awareness only. WARN → review recommended. FAIL → operator acknowledgment recommended before worsening actions. No autonomous blocking.

---

## Implementation Recommendation

**Priority:** Medium. Implement after:
1. PRA-IMPL-05 FVI Advisory Overlay (#28) — has clear data dependency (peer group config needed)
2. AI-003 Allocation Philosophy Narrative (#31) — content-first, low technical risk

**Complexity:** M (Medium)
- Backend: 1 new function in `src/allocation/validators.py` (~80 lines)
- Config: 8-rule YAML extension in `allocation_policy.yaml`
- Runner: 1 additive call in `runner.py` to attach results to PAR output
- UI: extend existing `renderPortfolioCompliance()` function + new banner

**Breaking changes:** None. All changes are additive.

**Test plan:** 26 tests defined. Expected: 100% pass with no regression.

---

## Recommended Issue for Backlog

Create GitHub issue:

**Title:** AI-001-OPTION-B: Actual Portfolio Compliance Validator (CPV Rules)

**Labels:** enhancement, governance, priority-medium, ready

**Parent:** References AI-001 (#29 — closed) and AI-002 (#30 — closed)

**Dependencies:** None (config and validator are self-contained)

**Acceptance Criteria:**
1. CPV-01 through CPV-08 check actual portfolio against policy ceilings
2. Three-tier status: ADVISORY / WARN / FAIL with configurable thresholds
3. Results stored in PAR output (additive field)
4. UI shows severity badges in Current Portfolio Compliance section
5. Governance banner appears when WARN or FAIL is present
6. No scoring, ranking, or recommendation generation changes
7. Full regression suite passes
