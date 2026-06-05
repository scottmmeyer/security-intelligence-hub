# Phase 23.6B.3 — International Reduction Logic Review

**Date:** 2026-06-04  
**PAR Run:** PAR-20260604-5EE3622B  
**Analysis type:** Forensic only — no code changes

---

## 1. Current State

**EQUITIES.INTERNATIONAL is overweight by +5.22%**  
(actual 17.2% vs target 12.0%)

**EQUITIES.INTERNATIONAL.LARGE is overweight by +3.61%**  
(actual 7.6% vs target 4.0%)

### CRA identifies these as OVERWEIGHT_REDUCTION sell sources:

| Symbol | MV | Proceeds | Geography | Category | Signal |
|--------|-----|----------|-----------|----------|--------|
| DODFX | $15,293 | $3,823 | INTERNATIONAL | OVERWEIGHT_REDUCTION LOW | UNKNOWN / no ESS |
| VEA | $3,594 | $899 | INTERNATIONAL | OVERWEIGHT_REDUCTION LOW | UNKNOWN / no ESS |
| TTNDY | $539 | $135 | INTERNATIONAL | OVERWEIGHT_REDUCTION LOW | UNKNOWN / no ESS |
| SBS | $18,133 | $4,533 | INTERNATIONAL | OVERWEIGHT_REDUCTION LOW | BULLISH |
| CVE | $12,479 | $3,120 | INTERNATIONAL | OVERWEIGHT_REDUCTION LOW | VERY_BULLISH |
| TSM | $11,636 | $2,909 | INTERNATIONAL | OVERWEIGHT_REDUCTION LOW | BULLISH |
| ASML | $3,551 | $888 | INTERNATIONAL | OVERWEIGHT_REDUCTION LOW | VERY_BULLISH |
| GTX | $9,053 | $2,263 | INTERNATIONAL | OVERWEIGHT_REDUCTION LOW | VERY_BULLISH |

### CRA simultaneously proposes deploying INTO:

| Symbol | DAS | Allocation | Node | Signal |
|--------|-----|-----------|------|--------|
| GTX | 84.15 | $12,675 | EQUITIES.INTERNATIONAL.SMALL | VERY_BULLISH |
| CVE | 83.86 | $10,473 | EQUITIES.INTERNATIONAL.MID | VERY_BULLISH |
| ASML | 78.01 | $1,676 | EQUITIES.INTERNATIONAL.MEGA | VERY_BULLISH |
| TSM | 70.76 | $1,138 | EQUITIES.INTERNATIONAL.MEGA | BULLISH |
| SBS | 69.29 | $706 | EQUITIES.INTERNATIONAL.LARGE | BULLISH |

---

## 2. Is CRA Properly Distinguishing Security Quality vs Allocation Exposure?

**No.** CRA is treating these as two independent decisions when they are the same securities.

The CRA architecture has two layers that generate conflicting signals for the same holdings:

- **Capital Source Builder** looks at `is_overweight_vs_target=True` → generates OVERWEIGHT_REDUCTION sell candidate
- **Deployment Queue** (CW-DAS) applies a `redundancy_pen` of 0 or −15 for overweight nodes, but still includes these securities as deployment targets when they have high conviction scores

For CVE, GTX, TSM, ASML, and SBS: both layers fire simultaneously because these securities have strong conviction (VERY_BULLISH ESS, replay supported) but are in overweight allocation nodes.

---

## 3. Can a Security Legitimately Be Both a Buy and Sell Candidate?

**Yes — but only in a very specific scenario:** when the allocation node is overweight but the individual security is underweight *within that node*, and the intent is to consolidate rather than reduce total exposure. 

In the current CRA, that nuance is absent. The proposal simply lists CVE as:
- **Source row:** "overweight allocation node | drift +5.2%" → sell $3,120 (25% of position)
- **Target row:** Deploy $10,473 into CVE (#23 in CW-DAS queue)

**Net effect:** If executed as-is, the operator would sell $3,120 of CVE and buy $10,473 — a net increase of $7,353 in CVE, in an already-overweight international node. This is the opposite of what the sell recommendation implied.

---

## 4. Does the Current Proposal Create Circular Behavior?

**Yes — definitively.** For 5 of the 37 capital sources:

| Symbol | Sell Proceeds | Buy Allocation | Net Direction | Circular? |
|--------|-------------|--------------|--------------|-----------|
| CVE | $3,120 | $10,473 | +$7,353 net BUY | ✅ Yes |
| GTX | $2,263 | $12,675 | +$10,412 net BUY | ✅ Yes |
| TSM | $2,909 | $1,138 | −$1,771 net SELL | Circular but consistent |
| ASML | $888 | $1,676 | +$788 net BUY | ✅ Yes |
| SBS | $4,533 | $706 | −$3,827 net SELL | Circular but consistent |

For CVE, GTX, and ASML: the operator would simultaneously receive instructions to sell (due to overweight) and buy more (due to conviction) the same security. This is internally contradictory and would confuse any operator.

**Root cause:** The CW-DAS queue does not exclude securities whose allocation nodes are overweight from deployment. The `redundancy_pen` dampens (but does not eliminate) their score. These securities remain in the queue because their conviction signals are strong enough to overcome the penalty.

---

## 5. Would an Operator Understand the Conflicting Signals?

**No, without explicit UI explanation.** An operator looking at the current three-column CRA layout would see:

- **Column 1 (Sources):** "Sell CVE — overweight international exposure"
- **Column 2 (Rotation Map):** "Deploy $10,473 → CVE (#23)"

Without an explicit cross-reference warning ("⚠ CVE appears in both SELL and BUY lists"), the operator has no way to know these are the same security. This is a genuine UX failure that could lead to contradictory execution.

---

## 6. Required Improvements

### A. Cross-symbol conflict detection (future implementation)
Before building the rotation map, CRA should detect symbols that appear in both the source list and deployment targets and either:
1. Remove them from one list (recommended: remove from sources if they have positive conviction and are in sources only due to OW node)
2. Flag them explicitly in the UI with a "⚠ This security appears in both SELL and BUY recommendations"

### B. Node-aware deployment filtering (future implementation)
CRA deployment allocation should filter out (or significantly deprioritize) candidates whose `allocation_node` is already overweight. The CW-DAS `redundancy_pen` exists for a reason — CRA should respect it more aggressively.

### C. UI conflict badge
Even before backend fixes, the UI should surface: "⚠ 5 securities appear in both capital sources and deployment targets" in the review flags.

---

## 7. Answers to Investigation Questions

**Q1.** Is CRA distinguishing security quality vs allocation exposure?  
→ **No.** These are treated independently. The same security can receive opposing instructions simultaneously.

**Q2.** Can a security remain a buy candidate while its node is overweight?  
→ **Yes, legitimately** — but the CRA must show the net direction, not independent contradictory signals.

**Q3.** Does the proposal create circular behavior?  
→ **Yes.** CVE, GTX, and ASML receive net-buy instructions contradicting their sell recommendation.

**Q4.** Would an operator understand?  
→ **No.** No cross-reference exists in the current UI. The operator would need to manually cross-check all 37 sources against 31 targets.

**Q5.** Required improvements?  
→ Cross-symbol conflict detection, OW-node deployment filtering, and a UI conflict badge are all needed.
