# AI-001 Implementation Options

Repository: security-intelligence-hub  
Issue: AI-001 (#29)  
Date: 2026-06-09

## Option A: Strict Enforcement

**Description:** Add a hard check that blocks the system from producing PASS validator output when actual portfolio positions exceed any policy ceiling. The reconciliation report would fail if actual holdings exceed the 5% micro-cap ceiling.

**Benefits:**
- Eliminates the operator confusion completely
- Enforces governance intent literally
- Hardest possible guarantee of policy compliance visibility

**Risks:**
- Portfolios will routinely exceed strategic targets due to drift; this would produce persistent FAIL states that may not represent actionable concerns
- Could create alert fatigue
- Breaks the separation between "recalculation governance" and "portfolio status"

**Complexity:** M — requires cross-referencing PAR alignment data inside the allocation validator pipeline, which currently operates independently of portfolio runs

**Recommended status:** Not recommended as sole approach; acceptable as an escalation threshold for large breaches (>3pp over ceiling)

---

## Option B: Exception Framework

**Description:** Introduce an explicit tolerance window — e.g., "actual micro-cap may exceed target by up to 2pp before generating a governance event." Within tolerance: WARN. Outside tolerance: FAIL. Strategic target compliance remains separate.

**Benefits:**
- Accounts for normal portfolio drift
- Graduated response (WARN before FAIL)
- Provides governance context for why exceedance may be acceptable temporarily

**Risks:**
- Adds configuration complexity (who sets the tolerance windows?)
- Risk that tolerance windows become normalized and are never acted on

**Complexity:** M — requires new tolerance fields in allocation_policy.yaml, new actual-portfolio check in either validators or runner

**Recommended status:** Yes — this is the recommended approach for an actual-vs-policy ceiling check

---

## Option C: Informational Ceilings Only

**Description:** Reclassify the 5% micro-cap ceiling as informational/advisory. Remove the OVER indicator from the UI or relabel it. Validators continue to check only strategic targets. No new check added.

**Benefits:**
- Simplest change
- Eliminates the contradiction by removing the OVER indicator's governance claim

**Risks:**
- Abandons the governance ceiling that was explicitly designed as an enforcement constraint
- Reduces operator awareness of real policy drift

**Complexity:** S — UI label change only

**Recommended status:** Not recommended. The ceiling is documented as a governance constraint; marking it informational reverses the design intent without explicit governance review.

---

## Option D: Explicit Dataset Labeling (Minimum Required Fix)

**Description:** Add clear labels to all allocation displays distinguishing "Strategic Target" from "Current Actual." Add a new "Actual Portfolio Compliance" section that shows actual-vs-ceiling status separately from the strategic target validator results. The PASS badges in the validator grid are relabeled "Strategic target recalculation compliance."

**Benefits:**
- Eliminates operator confusion immediately
- No changes to validators or policy logic
- Additive only — no risk of regression
- Can be deployed independently before Option B

**Risks:**
- Does not enforce anything; still requires operator to interpret the two datasets
- Does not provide a formal governance event for actual breaches

**Complexity:** S — UI labeling and display additions

**Recommended status:** YES — implement first as an immediate fix, then pursue Option B for the actual compliance check

---

## Recommended Sequence

1. **Immediate (Option D):** Add dataset labels and a separate Actual vs Policy section
2. **Planned (Option B):** Add actual-portfolio tolerance-window compliance check
3. **Future consideration:** Formal governance event (email/alert) when actual breach exceeds tolerance for more than N days
