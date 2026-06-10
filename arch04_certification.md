# ARCH-04: Certification

**Date:** 2026-06-09

---

## Certification Checklist

| Criterion | Status |
|---|---|
| KGC no longer inherits DODFX deferral | PASS |
| TSLA remains BLOCKED_BY_POLICY | PASS |
| DODFX remains DEFERRED_BY_POLICY | PASS |
| `symbol_execution_states` dict present on all sell-context recs | PASS |
| Drilldown holdings annotated with per-symbol states | PASS |
| All policy surfaces agree on KGC = EXECUTABLE | PASS |
| No CW-DAS changes | PASS |
| No RPS changes | PASS |
| No ESS changes | PASS |
| No STI changes | PASS |
| No CRA ranking changes | PASS |
| No PAP rec generation changes | PASS |
| 11 new ARCH-04 tests pass | PASS |
| Full regression: 1203 passed, 0 failed | PASS |

---

## Final Q&A

### Q1: What symbols were incorrectly inheriting policy state?

**14 symbols across 2 recommendations:**

From REC-5DD333BD (REDUCE INTERNATIONAL, DODFX SELL_LAST):
VEA, TTNDY, KGC, STNG, NVS, SIMO, TSM, SBS, CVE, GTX, ASML (11 symbols)

From REC-F129627C (REDUCE ULTRA_MEGA, TSLA DO_NOT_SELL):
MU, VOO, FXAIX (3 symbols)

All 14 are now correctly classified as EXECUTABLE.

### Q2: Was KGC corrected?

**Yes.** KGC is now EXECUTABLE in all policy surfaces:
- `symbol_execution_states["KGC"]["execution_state"] = "EXECUTABLE"`
- Drilldown holding annotated: `execution_state = "EXECUTABLE"`, `policy_type = ""`
- CRA capital source for KGC: EXECUTABLE (was already correct — CRA uses per-symbol)
- Reduction Queue: KGC at rank #5 with no policy badge

### Q3: Do all policy surfaces now agree?

**Yes.** TSLA = BLOCKED, DODFX = DEFERRED, KGC/VEA/MU/etc. = EXECUTABLE across:
- `apply_policy_to_recommendations()` output
- Drilldown holdings
- Security overlays (were always correct)
- PAP Cat 3 (was always correct)
- CRA capital sources (was always correct)
- Reduction Queue (was always correct via CRA)

### Q4: Were any recommendation rankings changed?

**No.** Signal scores (composite, ESS, RPS, CW-DAS) are unchanged. Recommendation generation logic is unchanged. The recommendation order in `recommendations.json` is unchanged. Only the policy annotation fields (`execution_state`, `effective_action`, `card_lifecycle_state`, `symbol_execution_states`) changed.

PAP lane placement changed (both REDUCE_OVERWEIGHT recs move from Blocked → Actions lane), but this is a correct consequence of the per-symbol fix, not a ranking change.

### Q5: Should recommendation-level execution_state be retired in favor of symbol-level state long term?

**Partially, for sell-context recommendations.** Recommendation-level `execution_state` continues to serve a useful purpose:
- Lane placement in PAP (Actions vs Blocked)
- Typed rec counts (`blocked_action_count`, `action_count`)
- Narrative summary warnings

However, its semantics have changed from "most-restrictive propagation" to "least-restrictive viable state." This is more correct operationally: a rec is actionable if any symbol in it can be acted on.

The `symbol_execution_states` dict is now the canonical source of per-symbol constraint information. Long term, the UI should use `symbol_execution_states` for granular display rather than inferring symbol constraints from the rec-level state. ARCH-04 delivers both.

The rec-level `execution_state = BLOCKED_BY_POLICY` should be reserved for recs where truly no action is possible (all symbols blocked) — which is the correct semantic under ARCH-04.
