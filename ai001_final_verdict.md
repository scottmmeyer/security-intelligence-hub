# AI-001 Final Verdict

Repository: security-intelligence-hub  
Issue: AI-001 (#29)  
Date: 2026-06-09

## Final Root Cause Determination

**Root cause: Governance design gap + UI labeling defect**

This is not a data defect, not a calculation defect, and not a validator bug. Both calculations are correct for their respective inputs. The defect is that two different datasets (strategic targets vs actual portfolio) are both compared against the same policy ceiling, but this is not communicated to the operator, making the PASS and OVER indicators appear contradictory.

---

## Q1: Why Do policy_bounds and concentration_ceilings PASS When Actual Micro Cap Is 6.5% vs 5%?

Because the validators check **strategic allocation targets** (2.212% combined), not actual portfolio holdings (6.5% combined). These are different datasets:

- Strategic target US.MICRO = 1.512%
- Strategic target INTL.MICRO = 0.700%
- **Combined strategic target = 2.212%** → PASS (< 5%)

The validators were never designed to check actual portfolio positions. They validate the recalculation governance pipeline.

---

## Q2: Is the Ceiling Actually Enforceable?

The ceiling as defined is an aspirational/planning constraint — it governs whether the strategic target allocation model violates policy. There is no mechanism in the current codebase that enforces the ceiling against actual holdings in real-time. The portfolio alignment engine reports actual allocation drift (which can show 6.5%) but this is not wired into the validator PASS/FAIL reporting.

The ceiling is **defined as enforceable** in the governance documentation but is **not mechanically enforced** against live portfolio values in the validator pipeline.

---

## Q3: Is This a Bug or Expected Behavior?

**Expected behavior, incorrectly communicated.**

The validators are working as designed. The UI's concentration bars are working as designed. The governance gap is that no component explicitly answers the question: "Does the actual portfolio currently violate the policy ceiling?" and presents the answer alongside the validator results.

The operator experience creates the appearance of a contradiction because:
1. Validators show PASS (correct for strategic targets)
2. Concentration bars show OVER (correct for actual portfolio)
3. Neither display labels its data source

---

## Q4: What Should the Operator See?

The operator should see two clearly separated and labeled indicators:

**Strategic Target Compliance (what the recalculation model plans):**
- Micro Cap combined target: 2.21% → PASS vs 5% ceiling
- All validators: PASS → recalculation governance is clean

**Current Portfolio Status (what is held today):**
- Micro Cap combined actual: 6.5% → OVER vs 5% ceiling (exceedance: +1.5pp)
- Severity: ADVISORY (within 2pp tolerance zone — no immediate action required)

**Drift Gap:**
- Strategic target: 2.21% | Actual: 6.5% | Gap: +4.29pp overweight vs target

---

## Q5: Recommended Fix Path

**Immediate (S complexity — Option D):**
1. Add explicit dataset labels to every allocation percentage table: "Strategic Target" vs "Current Portfolio"
2. Add a "Current Portfolio vs Policy" section to the Allocation Intelligence panel that renders actual exposure vs policy ceiling separately from the strategic target validator grid
3. Relabel the validator grid header: "Strategic Target Recalculation Compliance"

**Planned (M complexity — Option B):**
4. Add an actual-portfolio compliance check to the Allocation Intelligence panel or runner that produces a WARN/FAIL advisory when actual positions exceed a policy ceiling by more than a configurable tolerance (default: 2pp WARN, 4pp FAIL)
5. This check should be clearly labeled "Portfolio Compliance Advisory" and separated from the strategic target validators

**This issue does not require:**
- Changing the validators (they are correct)
- Changing the policy ceiling
- Changing the scoring or recommendation logic

---

## Defect Classification

| Defect Type | Present | Notes |
|---|---|---|
| Data defect | No | All data values are correct |
| Calculation defect | No | Both calculations are correct for their inputs |
| Validator defect | No | Validators work as designed |
| Governance design gap | **YES** | No cross-check exists between actual holdings and policy ceiling |
| UI labeling defect | **YES** | Neither display labels its data source (strategic target vs actual) |
| Documentation defect | No | Code comments are accurate; allocation_methodology.yaml correctly notes the ceiling |

---

## Priority and Complexity

Priority: HIGH (trust-critical — operators see contradictory governance signals)  
Option D fix complexity: S  
Option B fix complexity: M  
Breaking changes: None (both fixes are additive)  
Closes: AI-001 (#29) after Option D minimum implementation
