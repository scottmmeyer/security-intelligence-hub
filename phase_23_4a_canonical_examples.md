# Phase 23.4A — Q6: Canonical Examples
**DESIGN ONLY — NO IMPLEMENTATION**
**Generated:** 2026-06-04
**Baseline:** PAR-20260604-8DB0393D | 853 tests | 0 failures | 1 skip | Analytical universe: 2026-06-04

---

## Overview

Three canonical cases are evaluated against the NBA framework using live data from PAR-20260604-8DB0393D. Each case traces the blocker to its source, applies the generation logic from Q3, and evaluates whether the framework produces useful operator guidance.

---

## Case A: EQUITIES.US.LARGE — MANDATE_BLOCKED → Alternatives: VRT, ARW, PSX, DELL, AVT

### A.1 Situation

| Attribute | Value |
|---|---|
| Node | `EQUITIES.US.LARGE` |
| Drift direction | UNDERWEIGHT −5.42% |
| Target pct | 14.0% |
| Actual pct | 8.58% |
| Severity | MODERATE |
| Recommendation type | `INCREASE_UNDERWEIGHT` |
| Optimizer decision | `MANDATE_BLOCKED` |
| Legacy vehicles considered | VOO, IVV, SPY |
| Mandate type | CONCENTRATED_ALPHA |
| Concentration tolerance | 0.90 |

### A.2 Why Blocked

The CONCENTRATED_ALPHA mandate applies `concentration_tolerance = 0.9` to equity underweight nodes. In `evaluate_drift_under_mandate()`:
- Tolerance ≥ 0.8 → label = `INTENTIONAL`
- `severity != HIGH` → `suppress_recommendation = True`
- `suppress_recommendation = True` → `mandate_blocked = True`
- `mandate_blocked = True` → `optimizer_decision = "MANDATE_BLOCKED"`

Additionally, all three legacy vehicles (VOO, IVV, SPY) independently fail the ETF gate:
- `suit_tier = "LOW"`, `NCS = 0.0%` (< 10.0 threshold)
- `worsens_overweight = True` (MEGA.ULTRA_MEGA node is OW +4.97%)

The recommendation is doubly blocked: mandate gate AND ETF gate.

### A.3 NBA Framework Output

**Blocker type:** `MANDATE_BLOCKED`  
**Generation path:** Q3 §2 — deployment_queue, EXECUTABLE + BULLISH + CCL/HCA

Deployment queue scan (PAR-20260604-8DB0393D):

| Rank | Symbol | CW-DAS Score | Tier | Execution State | Headroom |
|---|---|---|---|---|---|
| 1 | VRT | 94.97 | CORE_CONVICTION_LEADER | EXECUTABLE | 33% |
| 2 | ARW | 93.93 | HIGH_CONVICTION_ANCHOR | EXECUTABLE | 82% |
| 3 | PSX | 93.53 | HIGH_CONVICTION_ANCHOR | EXECUTABLE | 86% |
| 4 | DELL | 92.45 | HIGH_CONVICTION_ANCHOR | EXECUTABLE | 77% |
| 5 | AVT | 91.96 | HIGH_CONVICTION_ANCHOR | EXECUTABLE | 83% |

**NBA Object:**
```json
{
  "blocker_type": "MANDATE_BLOCKED",
  "blocked_symbol": null,
  "blocked_node": "EQUITIES.US.LARGE",
  "action_type": "ACCUMULATE",
  "action_priority": "HIGH",
  "rationale": "CONCENTRATED_ALPHA mandate suppresses ETF allocation to this node; direct securities ranked by conviction are the preferred deployment path.",
  "candidate_symbols": ["VRT", "ARW", "PSX", "DELL", "AVT"],
  "deployment_scores": [94.97, 93.93, 93.53, 92.45, 91.96],
  "narrative_tiers": ["CCL", "HCA", "HCA", "HCA", "HCA"],
  "execution_states": ["EXECUTABLE", "EXECUTABLE", "EXECUTABLE", "EXECUTABLE", "EXECUTABLE"],
  "expected_portfolio_effect": "IMPROVES_ALIGNMENT",
  "headroom_available": true,
  "generation_source": "DEPLOYMENT_QUEUE",
  "alternatives_count": 5,
  "no_action_available": false
}
```

### A.4 Operator Guidance Evaluation

**Question: Does the framework produce useful guidance here?**

YES — strong result. Analysis:
- The blocked recommendation (add VOO to LARGE) has an obvious answer hidden in the deployment queue: the top 5 conviction-ranked direct securities are already being suggested for ACCUMULATE elsewhere in the UI.
- The NBA panel makes the connection explicit: "The reason VOO is blocked doesn't mean you can't add to this category — buy VRT/ARW/DELL instead."
- All 5 candidates are EXECUTABLE, all have meaningful headroom (33–86%), and the portfolio ESS data supports them: ARW (composite 4.89), DELL (4.72), VRT (4.56), LRCX (4.50), CAH (4.50).
- The operator does not need to understand mandate logic to act. They see: "ACCUMULATE VRT, score 94.97, 33% headroom." That is a complete action item.

**Operator decision path after NBA panel:**
```
Sees: EQUITIES.US.LARGE MANDATE_BLOCKED
NBA: → ACCUMULATE VRT (94.97), ARW (93.93), PSX (93.53), DELL (92.45), AVT (91.96)
Action: Proceeds to add to any of these positions
Result: Capital deployed into highest-conviction securities, underweight drift begins closing
```

**Framework grade: PASS — high operator utility.**

---

## Case B: TSLA — BLOCKED_BY_POLICY/MONITOR_ONLY

### B.1 Situation

| Attribute | Value |
|---|---|
| Symbol | TSLA |
| Portfolio weight | 3.01% |
| Signal direction | BEARISH |
| ESS | VERY_BEARISH |
| Composite score | 1.33/5.0 |
| UCF label | TRIM_WATCH |
| UCF score | 0.0 (rank 79) |
| Opportunity flag | TRIM |
| Execution state | `BLOCKED_BY_POLICY` |
| Effective action | `MONITOR_ONLY` |
| Policy | DO_NOT_SELL |

### B.2 Why Blocked

`operator_policy.py` → `compute_execution_state()`:
- `opportunity_flag = "TRIM"` → in `_SELL_ACTION_FLAGS`
- Policy `DO_NOT_SELL` for TSLA → `execution_state = "BLOCKED_BY_POLICY"`, `effective_action = "MONITOR_ONLY"`

### B.3 NBA Framework Output

**Blocker type:** `BLOCKED_BY_POLICY` → `effective_action = "MONITOR_ONLY"` → DO_NOT_SELL path (Q3 §5.2)

**NBA Object:**
```json
{
  "blocker_type": "BLOCKED_BY_POLICY",
  "blocked_symbol": "TSLA",
  "blocked_node": null,
  "action_type": "MONITOR_ONLY",
  "action_priority": "INFORMATIONAL",
  "rationale": "DO_NOT_SELL policy in effect. Hold current position. Monitor for signal reversal or policy change before re-evaluating.",
  "candidate_symbols": [],
  "deployment_scores": [],
  "narrative_tiers": [],
  "execution_states": [],
  "expected_portfolio_effect": "NEUTRAL",
  "headroom_available": false,
  "generation_source": "NONE",
  "alternatives_count": 0,
  "no_action_available": true
}
```

**UI panel (no alternatives table):**
```
┌──────────────────────────────────────────────────────────┐
│  NEXT BEST ACTION                       [INFORMATIONAL]  │
│                                                          │
│  Instead of reducing TSLA:                               │
│                                                          │
│  → MONITOR ONLY — no action available                    │
│                                                          │
│  DO_NOT_SELL policy in effect. Hold current position.    │
│  Monitor for signal reversal or policy change.           │
└──────────────────────────────────────────────────────────┘
```

### B.4 Operator Guidance Evaluation

**Question: Does the framework produce useful guidance here?**

PARTIAL — contextually appropriate. Analysis:
- The NBA panel correctly communicates: "No sell action is available. This is expected policy behavior."
- The operator is not left wondering "can I sell TSLA?" — the answer is explicit: no.
- There is no alternative security to suggest because the blocked action is a REDUCE (sell direction), not an ACCUMULATE. Suggesting "buy VRT instead" would be misleading — the operator wanted to reduce a deteriorating position, not add capital elsewhere.
- The `INFORMATIONAL` priority signals correctly: this is not an urgent action gap, it is a deliberate policy constraint.

**Limitation:** The framework does not answer "when will this policy clear?" or "what would the portfolio look like if TSLA were sold?" Those are out-of-scope for Phase 23.5 (see Q7, Phase 23.6+ territory).

**Operator decision path after NBA panel:**
```
Sees: TSLA BLOCKED_BY_POLICY / MONITOR_ONLY
NBA: → MONITOR ONLY
Action: Notes TSLA as watchlist item, no immediate capital change
Result: Policy respected, signal degradation tracked passively
```

**Framework grade: PASS — correctly terminates with no false alternatives. Informational value is in the clarity of "no action possible," not in suggesting alternatives.**

---

## Case C: FIS — Strategic Exit / Suggested Redeployment Path

### C.1 Situation

| Attribute | Value |
|---|---|
| Symbol | FIS |
| Portfolio weight | 4.09% |
| Signal direction | BEARISH |
| ESS | BEARISH |
| Composite score | 2.22/5.0 |
| UCF label | TRIM_WATCH |
| UCF score | 13.34 (rank 78) |
| Opportunity flag | WATCH |
| Execution state | `EXECUTABLE` |
| Effective action | `WATCH` |

### C.2 Why This Case Is Different

FIS does not have a current execution block — `execution_state = "EXECUTABLE"`. Its signal is weak (BEARISH) but not policy-blocked. The opportunity flag is `WATCH`, not `TRIM`.

The question from the Phase 23.4A spec: "FIS Strategic Exit → Suggested redeployment path."

This tests whether the NBA framework extends beyond blocked recs to also handle **strategic exit sequencing** — when the operator wants to act on a WATCH signal and redirect capital.

### C.3 NBA Framework Output — Redeployment Path

FIS is not blocked. The standard BLOCK DIAGNOSTICS panel would NOT render for FIS.

However, the NBA framework concept applies:

**Operator question:** "If I sell FIS (4.09% of portfolio), where should the capital go?"

This is a redeployment path request. The deployment queue provides the answer:

| Rank | Symbol | Score | Tier | Headroom |
|---|---|---|---|---|
| 1 | VRT | 94.97 | CCL | 33% |
| 2 | ARW | 93.93 | HCA | 82% |
| 3 | PSX | 93.53 | HCA | 86% |
| 4 | DELL | 92.45 | HCA | 77% |
| 5 | AVT | 91.96 | HCA | 83% |

**Proposed redeployment NBA concept:**
```json
{
  "context": "STRATEGIC_EXIT_REDEPLOYMENT",
  "exit_symbol": "FIS",
  "exit_pct": 4.09,
  "action_type": "REBALANCE",
  "action_priority": "MEDIUM",
  "rationale": "FIS BEARISH signal with WATCH flag. Capital available for redeployment into higher-conviction securities.",
  "candidate_symbols": ["VRT", "ARW", "PSX", "DELL", "AVT"],
  "generation_source": "DEPLOYMENT_QUEUE"
}
```

### C.4 Scope Assessment

**Is STRATEGIC_EXIT_REDEPLOYMENT in scope for Phase 23.5?**

**NO — this is Phase 23.6+ territory.** Reasons:

1. FIS is not blocked — the BLOCK DIAGNOSTICS panel does not render for it in Phase 23.5
2. The redeployment path requires pairing a WATCH/TRIM action with a capital availability model — a new concept not present in current pipeline outputs
3. The NBA framework as designed in Q2/Q3 is scoped to blocked recommendations only
4. Adding non-blocked redeployment logic would expand scope significantly and risk introducing a new capital allocation suggestion surface without the constraint analysis that governs the existing pipeline

**Phase 23.5 BLOCK DIAGNOSTICS + NBA is correct for:** `MANDATE_BLOCKED`, `ETF_GATE_FAILED`, `WORSENS_OVERWEIGHT`, `BLOCKED_BY_POLICY`

**FIS redeployment path is:** a valid future enhancement for Phase 23.6+ as a "capital rotation advisor" layer

### C.5 What the Framework Does for FIS Today

No BLOCK DIAGNOSTICS panel renders. FIS appears in the standard portfolio alignment card as:
- `opportunity_flag = WATCH`
- `execution_state = EXECUTABLE`
- Signal: BEARISH, ESS BEARISH (2.22)

The operator can already see: FIS is weak, watch it. The deployment queue shows where better conviction exists. The connection is not made automatically today — and Phase 23.5 does not change that.

**Framework grade for Case C:** NOT APPLICABLE for Phase 23.5. This case validates that the scope boundary is correct — NBA is for blocks, not for all sell/rotation decisions.

---

## 4. Cross-Case Assessment

| Case | Block Type | NBA Useful? | Candidates Generated? | Framework Grade |
|---|---|---|---|---|
| Case A: EQUITIES.US.LARGE | MANDATE_BLOCKED | YES — HIGH utility | YES — 5 alternatives | PASS |
| Case B: TSLA | BLOCKED_BY_POLICY (DNS) | YES — clarity of "no action" | NO (correct) | PASS |
| Case C: FIS | No block | N/A — Phase 23.6+ | N/A | SCOPE BOUNDARY CONFIRMED |

### 4.1 Key Insight from Canonical Examples

Case A and Case B represent the two fundamental NBA archetypes:
1. **Block with available path:** The operator can act; NBA gives them the path (ACCUMULATE alternatives)
2. **Block with no available path:** The operator cannot act; NBA confirms this explicitly (MONITOR_ONLY)

Both are valuable. The "no action available" state is as important as the "here are alternatives" state — it prevents the operator from searching for a non-existent alternative and creates a clear record that the constraint was evaluated.

### 4.2 Framework Validation

The three cases confirm:
1. NBA can be generated from existing `deployment_queue.json` data with no Python changes (Case A)
2. Policy blocks are correctly handled with no false alternatives (Case B)
3. The scope boundary is correctly defined — non-blocked redeployment is out of scope (Case C)

---

## 5. Summary

**Status: Q6 COMPLETE — CANONICAL EXAMPLES CERTIFIED**

The NBA framework produces useful operator guidance in all in-scope blocker scenarios. Case A validates the core ACCUMULATE path. Case B validates the MONITOR_ONLY path. Case C confirms the Phase 23.5 scope boundary.
