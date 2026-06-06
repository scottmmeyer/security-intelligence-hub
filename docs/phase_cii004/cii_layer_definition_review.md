# CII Layer Definition Review — Phase CII-004

## Review Against Certified Architecture

### Layer 1 — Analyst Consensus

**Current modal description:** "Capture what the professional investment community currently believes."  
**Current sources:** ESS, Zacks, Danelfin AI, Yahoo ABR  
**Post-ISSUE-07 accuracy:** ✅ FULLY ACCURATE. Layer 1 is unchanged. Consensus remains primary.  
**Action:** None.

---

### Layer 2 — Fundamental Validation

**Current modal description:** "Validate whether business fundamentals support the consensus."

**Post-ISSUE-07 accuracy:** ⚠️ PARTIALLY ACCURATE.

The description correctly identifies the *function* (validation) but understates the *consequence* (scoring adjustment). Before ISSUE-07, validation was informational — producing Thesis Integrity and Fundamental Consistency labels in the display layer. After ISSUE-07, validation produces the `fundamental_modifier` component of the CW-DAS score, directly influencing deployment queue ranking.

**Recommended description:** "Validate whether business fundamentals support the consensus, and adjust conviction scores accordingly."

**Current sources:** Revenue Growth, ROIC, Beat Rate, FCF Yield, Revisions  
**Post-ISSUE-07 accuracy:** ✅ Sources are accurate. The modifier uses Beat Rate (primary), Thesis Integrity (from Revenue Growth + Acceleration), and Fundamental Consistency (combining ESS with fundamentals). The source pills correctly represent the data inputs.  
**Action:** Update purpose text only. Source pills unchanged.

**Important precision:** The modifier uses a derived signal (Thesis Integrity = classification from Revenue Growth + Acceleration + Beat Rate) rather than raw field values. The source pills represent the underlying data, which is accurate for display purposes.

---

### Layer 3 — Historical Validation

**Current modal description:** "Require empirical evidence that similar signal configurations have historically succeeded."  
**Current sources:** Replay  
**Post-ISSUE-07 accuracy:** ✅ FULLY ACCURATE. Replay gate is unchanged. The fundamental modifier does not affect the Replay eligibility requirement.  
**Action:** None.

---

### Layer 4 — Portfolio Discipline

**Current modal description:** "Deploy capital intelligently within concentration, allocation, and conviction constraints."  
**Current sources:** CW-DAS, CRA, Allocation Controls, Position Limits

**Post-ISSUE-07 accuracy:** ✅ ACCURATE with one nuance.

The CW-DAS source pill now encompasses the fundamental modifier as a component. The modal description "conviction constraints" is appropriate since the modifier adjusts conviction, which feeds into CW-DAS. No change to the Layer 4 description is needed.

**Optional enhancement:** Add "Fundamental Modifier" as a CW-DAS sub-component note in the tooltip or as an additional source pill. This would be a UI enhancement, not a required change.

---

## Architecture Consistency Summary

| Layer | Architectural Accuracy | Documentation Accuracy | Gap |
|-------|----------------------|----------------------|-----|
| L1: Analyst Consensus | Unchanged | ✅ Accurate | None |
| L2: Fundamental Validation | **Now active** (scoring) | ⚠️ Describes passive validation only | Update purpose text |
| L3: Historical Validation | Unchanged | ✅ Accurate | None |
| L4: Portfolio Discipline | CW-DAS gains fundamental_modifier | ✅ Accurate (CW-DAS pill covers it) | None |

---

## Core Architecture Invariants (Unchanged by ISSUE-07)

1. ✅ Consensus remains primary alpha source
2. ✅ Replay gate is a hard eligibility requirement  
3. ✅ CCL tier outranks HCA tier (enforced by CCL guard in v1.1)
4. ✅ Operator authority is final (modifier is visible, explainable, never autonomous)
5. ✅ No black-box behavior (breakdown grid shows "Fund. Mod" card)
