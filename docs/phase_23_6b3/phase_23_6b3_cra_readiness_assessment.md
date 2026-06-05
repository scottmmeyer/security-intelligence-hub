# Phase 23.6B.3 — CRA Readiness Assessment

**Date:** 2026-06-04  
**Analysis type:** Forensic only — no code changes

---

## Assessment Framework

Each dimension is scored: ✅ Ready / ⚠ Ready with limitations / ❌ Needs improvement

---

## 1. Capital Source Selection

**Score: ⚠ Ready with limitations**

**Strengths:**
- All 5 category types are detected and produce meaningful signals
- Non-tradeable exclusion (SPAXX, PENDING ACTIVITY) is now correct
- Priority sort is reasonable
- Tax bucket annotation provides useful context
- Policy-blocked sources remain visible (TSLA)

**Limitations:**
- 5 of 37 sources are circular (also deployment targets) — no conflict flag
- 6 sources have proceeds < $500 — below any rational execution threshold
- Strategic exits receive 25% sizing instead of 100%
- Index/ETF legacy positions mixed with intentional alpha positions
- No minimum proceeds filter

---

## 2. Rotation Target Selection

**Score: ⚠ Ready with limitations**

**Strengths:**
- CW-DAS rank order strictly preserved
- 31 targets correctly distributed across CCL and HCA tiers
- No target exceeds 6% WARN threshold (Phase 23.6B.2 fix)
- DELL and VRT receive meaningful CCL allocations
- ARW, PSX, AVT, ATLC, LRCX, CAH, PCB, SNX all funded

**Limitations:**
- 22 of 31 targets are in overweight allocation nodes
  - For US.SMALL, US.MICRO, INTERNATIONAL nodes: deploying into already-OW nodes
  - The CW-DAS `redundancy_pen` dampens but doesn't prevent these
- No net-exposure awareness: the rotation creates net inflow into international despite international being overweight
- Rank 26 (MU) skipped with headroom=0% — noted correctly
- Rank 32 (SIMO) has `EQUITIES.UNKNOWN.UNKNOWN` node — classification gap

---

## 3. Policy Interaction

**Score: ✅ Ready**

- DO_NOT_SELL correctly blocks pool entry while keeping source visible
- SELL_LAST correctly defers DODFX without excluding
- CORE_ANCHOR triggers operator review flag
- PREFERRED_ACCUMULATION correctly excludes from Category 5
- Policy type and annotation displayed on source cards

**Minor gap:** Policy rationale and cost not surfaced in UI (Inv. 3).

---

## 4. Tax Interaction

**Score: ⚠ Ready with limitations**

**Strengths:**
- Bucket A detection from cost_basis comparison is functional
- Tax annotation describes the situation clearly
- Bucket D triggers operator review correctly
- Large tax-harvest list (LMAT, CIEN, HCI, AVGO, etc.) with Bucket A is appropriate

**Limitations:**
- Bucket B and E require holding_days data not in PAR artifacts — not assigned
- No gain/loss budget awareness ("you've already realized $X in gains this year")
- De minimis positions (AGEN $340, XRP $92) surface as tax harvest candidates — transaction costs would exceed tax benefit
- Tax context not used to order sources within the same priority tier when multiple Bucket A candidates exist

---

## 5. Operator Workflow

**Score: ⚠ Ready with limitations**

**Strengths:**
- Three-column layout (Sources / Map / Impact) is logical
- Category accordion in Sources column provides organization
- Include/Skip checkboxes give operator control
- Refresh Proposal available without re-running analysis
- Impact estimate labeled as approximate

**Limitations:**
- No cross-reference between sources and deployment targets (circular conflict)
- Policy rationale not visible in source card
- No minimum proceeds filter to suppress de minimis noise
- No "net direction" calculation for circular symbols
- Strategic exits don't auto-suggest full sizing
- Source list of 37 items is overwhelming — no executive summary showing "3 genuinely actionable sources vs 34 contextual"

---

## 6. Explainability

**Score: ⚠ Ready with limitations**

**Strengths:**
- Evidence summary string is present for all sources
- Tax annotation provides clear human text
- CW-DAS score breakdown visible on deployment target expand
- Impact estimate narrative is generated
- `is_estimate=True` is prominently labeled

**Limitations:**
- Evidence strings are technical (e.g., "ESS=BEARISH | [also: STRATEGIC_EXIT] operator-designated strategic exit") — not plain English
- No plain-language summary: "You have 3 urgent actions and 9 tax opportunities"
- Deployment allocation note says "T1-CCL proportional share" — jargon
- No explanation for why OW-node targets are still in the rotation map

---

## 7. Trustworthiness

**Score: ⚠ Ready with limitations**

**Strengths:**
- CW-DAS scores are never modified
- All estimates labeled as approximate
- Policy gates cannot be bypassed
- No trade execution — guidance only
- Full audit trail via proposal_id + run_id linkage

**Concerns:**
- Circular behavior (sell and buy CVE/GTX/TSM/ASML/SBS simultaneously) damages trust if an operator spots it
- De minimis sources suggest the system is showing everything rather than curating
- 22/31 deployment targets in overweight nodes would look wrong to an experienced PM who knows the portfolio needs to reduce international exposure
- The system doesn't explain why it's recommending buying into overweight nodes

---

## Overall Strengths

1. **Technically sound foundation** — CW-DAS integration, policy gates, tax detection, non-tradeable exclusion all work correctly
2. **Multi-target distribution** — 31 targets, correctly tiered, no concentration violations
3. **TSLA handling** — DO_NOT_SELL clearly surfaced, excluded from pool
4. **FIS detection** — correctly identified, tax A, strategic exit visible
5. **Explainability infrastructure** — evidence strings, tax annotations, estimate labels all present

## Overall Weaknesses

1. **Circular conflict** — CVE, GTX, TSM, ASML, SBS in both sell and buy lists
2. **OW-node deployment** — 22 of 31 targets are in overweight nodes; net exposure increases
3. **Strategic exit sizing** — FIS at 25% when operator intent is 100%
4. **De minimis noise** — 6+ sources below $500 proceeds
5. **No executive summary** — 37-item source list without curation

## Remaining Gaps

| Gap | Severity | Required for operational? |
|-----|----------|--------------------------|
| Circular conflict detection | HIGH | Yes |
| Minimum proceeds filter ($500+) | MEDIUM | Recommended |
| Strategic exit full sizing | MEDIUM | Yes |
| OW-node deployment filtering | MEDIUM | Recommended |
| Policy rationale display | LOW | Nice to have |
| Executive summary view | LOW | Nice to have |

---

## Recommendation

**B. Additional CRA refinement required before declaring operational.**

Specifically:
1. Circular conflict detection and flagging (CVE/GTX/TSM/ASML/SBS cannot appear in both columns simultaneously)
2. Strategic exit full sizing override
3. Minimum proceeds filter (suppress sources below $500 estimated proceeds)

These three changes would meaningfully improve operator realism. The underlying infrastructure is sound. The issues are compositional, not architectural.

**After those 3 fixes:** CRA would be ready for broader operator usage and FMP integration could proceed in parallel.
