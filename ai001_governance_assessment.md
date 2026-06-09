# AI-001 Governance Assessment

Repository: security-intelligence-hub  
Issue: AI-001 (#29)  
Date: 2026-06-09

## Q1: What Was the Original Design Intent?

The validators in `src/allocation/validators.py` were designed to validate the **recalculation governance process** — ensuring that proposed strategic allocation target changes are internally consistent and policy-compliant before being committed. They answer: "Is this proposed strategic target set valid?"

The Concentration Risk section in the Allocation Intelligence UI answers a separate question: "Does the actual portfolio satisfy the policy ceilings today?"

These are two legitimate and different questions. The design intent is coherent, but the governance gap is that there is no explicit check connecting them: "Is the gap between actual portfolio and policy ceiling being tracked as a governance concern?"

## Q2: Should Allocation Methodology Be Allowed to Exceed Policy Ceilings?

The policy file (`allocation_policy.yaml`) states `max_micro_cap_pct: 5.0` as a structural policy. `allocation_methodology.yaml` for EQUITIES.US.MICRO explicitly notes "Governance cap: max_micro_cap_pct enforced at 5% of total."

Intent: No. The policy ceiling is meant to be enforced, not advisory.

However, there is no mechanism that prevents a portfolio from holding actual positions in excess of the strategic target or policy ceiling. The target represents the goal; actual holdings drift continuously due to price movements, purchases, and portfolio changes.

## Q3: Under What Conditions Should Exceedance Be Permitted?

Current documentation does not define any authorized exception window. Given portfolio drift:
- A brief breach during rebalancing should probably carry a WARN, not a hard FAIL
- A sustained or large breach (>2pp over ceiling) should carry a more urgent advisory
- The operator is currently receiving an OVER indicator but no explicit severity guidance

## Q4: Should Validators PASS or WARN?

**For the strategic target validators:** PASS is correct — the targets are not in violation.

**A new validator is needed** for actual-portfolio-vs-policy-ceiling compliance. This would:
- Read actual portfolio allocation data from the latest PAR
- Compare actual micro-cap combined exposure to `max_micro_cap_pct`
- Return WARN if actual > ceiling by < 2pp
- Return FAIL if actual > ceiling by >= 2pp

## Q5: What Should the Operator See?

The operator should see:

1. **Strategic target**: "Micro Cap target = 2.21% (PASS vs 5% ceiling)" — governance of the planning model
2. **Actual allocation**: "Micro Cap actual = 6.5% (OVER vs 5% ceiling)" — current state advisory
3. **Severity**: The 6.5% actual vs 5% target is a +1.5pp exceedance. This is MODERATE — worth operator attention but not an emergency.

What the operator should NOT see: unlabeled presentation of actual values under a panel that also shows PASS badges based on strategic targets, without any explanation that these are different datasets.

## Q6: What Is the Correct Governance Behavior?

Correct governance behavior requires:

1. Keep existing validators as-is (they correctly validate the strategic target recalculation pipeline)
2. Add a separate "actual vs policy ceiling" check in the Allocation Intelligence panel
3. Label every allocation display explicitly: "Strategic Target" or "Current Actual"
4. Provide a cross-check section: "Your current holdings vs your strategic targets vs policy limits"
5. The PASS/FAIL/WARN badge in the validator grid should be clearly labelled: "Strategic target recalculation compliance"

The fix for the operator-visible contradiction does not require changing the validators — it requires adding clear labeling and an actual-portfolio compliance advisory.
