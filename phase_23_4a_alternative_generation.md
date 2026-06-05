# Phase 23.4A — Q3: Alternative Generation Logic
**DESIGN ONLY — NO IMPLEMENTATION**
**Generated:** 2026-06-04
**Baseline:** PAR-20260604-8DB0393D | 853 tests | 0 failures | 1 skip

---

## 1. Overview

For each blocker type, this document specifies:
1. **Candidate Source** — where to look for alternatives
2. **Ranking Source** — what determines order
3. **Selection Logic** — inclusion/exclusion rules
4. **Tie-Break Rules** — when scores are equal

All generation happens at presentation time in `app.js`. No Python changes.

---

## 2. MANDATE_BLOCKED → Direct Security Alternatives

### 2.1 Context

When a node-level recommendation is `MANDATE_BLOCKED` (e.g., `EQUITIES.US.LARGE`), the CONCENTRATED_ALPHA mandate has suppressed the recommendation entirely. The ETF vehicles on the recommendation are also typically `ETF_GATE_FAILED` (see PAR-20260604-8DB0393D: VOO/IVV/SPY all gated with `worsens_overweight=True`).

The system already knows the right answer: **the deployment queue contains direct securities that would fulfill the same allocation intent.**

### 2.2 Candidate Source

**Primary:** `deployment_queue.json` → all entries where:
- `execution_state != "BLOCKED_BY_POLICY"` (cross-reference `security_overlays.csv`)
- `signal_direction == "BULLISH"` (already pre-filtered by CW-DAS eligibility)
- `narrative_tier` in `{CCL, HCA}` (confirmed eligible by CW-DAS)

**Secondary (fallback):** `security_overlays.csv` entries where:
- `opportunity_flag == "ACCUMULATE"`
- `execution_state == "EXECUTABLE"`

The primary source is preferred because deployment scores are already computed and ranked.

### 2.3 Ranking Source

`deployment_score` (CW-DAS score, 0–100). Higher = preferred.

Scores are already in rank order in `deployment_queue.json` (rank field 1-N).

### 2.4 Selection Logic

```
FOR each candidate in deployment_queue (rank order):
    IF candidate.execution_state == "EXECUTABLE":
        IF candidate.signal_direction == "BULLISH":
            IF candidate.narrative_tier in {CCL, HCA}:
                ADD to alternatives
    IF alternatives.length == MAX_ALTERNATIVES (5):
        BREAK
```

### 2.5 Tie-Break Rules

Ties in `deployment_score` are resolved by:
1. `narrative_tier` (CCL > HCA > WATCH > REDUCE)
2. `ucf_rank` (lower rank = higher conviction)
3. Alphabetical by symbol (deterministic)

### 2.6 Real Example (PAR-20260604-8DB0393D)

Blocked: `EQUITIES.US.LARGE` → `MANDATE_BLOCKED`
Alternatives generated from deployment queue (top 5 EXECUTABLE, BULLISH):

| Rank | Symbol | Score | Tier | Execution State |
|---|---|---|---|---|
| 1 | VRT | 94.97 | CCL | EXECUTABLE |
| 2 | ARW | 93.93 | HCA | EXECUTABLE |
| 3 | PSX | 93.53 | HCA | EXECUTABLE |
| 4 | DELL | 92.45 | HCA | EXECUTABLE |
| 5 | AVT | 91.96 | HCA | EXECUTABLE |

**Result:** NBA = ACCUMULATE, 5 candidates, all executable.

---

## 3. ETF_GATE_FAILED → Better ETF or Direct Security

### 3.1 Context

`ETF_GATE_FAILED` (UI label) / `ETF_GATED` (Python `optimizer_status`) occurs when:
- `suit_tier == "LOW"` OR
- `ncs < 10.0` OR
- `worsens_overweight == True`

The ETF failed its suitability assessment. The alternative is either a higher-suitability ETF or a direct security with better alignment.

### 3.2 Candidate Source

**For ETF alternatives:**
Not generated. The current system has no ETF suitability ranking table (all low-NCS ETFs fail the same gate). ETF alternatives require data not available in existing pipeline outputs.

**For direct security alternatives:**
Same as MANDATE_BLOCKED case — `deployment_queue.json` filtered to EXECUTABLE + BULLISH + CCL/HCA.

### 3.3 Candidate Source Decision

```
IF worsens_overweight == True:
    → Direct security alternatives (deployment_queue, avoid OW nodes)
    → Filter: exclude symbols whose parent node is the OW node

IF suit_tier == "LOW" AND ncs < 10.0:
    → Direct security alternatives (deployment_queue, any node)
    → No ETF alternatives available (data gap)

IF suit_tier == "MEDIUM" or "HIGH":
    → This case should not occur (gate only fires on LOW)
    → Handle defensively: same as LOW path
```

### 3.4 Node Overweight Filtering

When `worsens_overweight == True`, candidates in the overweight node should be de-prioritized:

```
FOR each candidate in deployment_queue:
    IF candidate node == gated_etf_node:
        SKIP (candidate would also worsen overweight)
    ELSE:
        ADD to alternatives
```

**Implementation note:** `deployment_queue.json` entries do not currently include `allocation_node` per candidate. This is a data gap (identified in Phase 23.4). At implementation time, either:
a) Add `allocation_node` to `DeploymentCandidate` output, or
b) Cross-reference `security_overlays.csv` `asset_class` field (approximate)

### 3.5 Tie-Break Rules

Same as MANDATE_BLOCKED case.

---

## 4. WORSENS_OVERWEIGHT → Candidates That Avoid OW Nodes

### 4.1 Context

`WORSENS_OVERWEIGHT` fires when adding to a position would increase overweight concentration in an already-overweight node. Example: VOO on `EQUITIES.US.LARGE` — node is UW, but MEGA.ULTRA_MEGA is OW, and VOO spans both.

### 4.2 Candidate Source

`deployment_queue.json` — same primary source. Additional filter: candidates whose underlying node is **not** the flagged overweight node.

### 4.3 Selection Logic

```
FOR each candidate in deployment_queue (rank order):
    IF candidate.execution_state == "EXECUTABLE":
        IF candidate's allocation_node NOT IN overweight_nodes:
            ADD to alternatives
        ELSE:
            SKIP with note: "would also worsen overweight"
```

### 4.4 Expected Behavior

In the PAR-20260604-8DB0393D case:
- `EQUITIES.US.MEGA.ULTRA_MEGA` is overweight (drift +4.97%)
- Candidates like NVDA or other mega-cap positions would be filtered
- VRT, ARW, PSX (industrial/tech, different nodes) would pass through

### 4.5 Data Gap Note

As with ETF_GATE_FAILED, per-candidate `allocation_node` is not in the current `deployment_queue.json` schema. This must be added at Phase 23.5 implementation time. Without it, the filter cannot be node-aware. A fallback behavior is to surface all top EXECUTABLE alternatives with a caveat note: "Verify candidate does not add to overweight node."

---

## 5. BLOCKED_BY_POLICY → Next Executable Candidate

### 5.1 Context

`BLOCKED_BY_POLICY` occurs in two scenarios:
1. **DO_NOT_SELL (TSLA):** Signal says TRIM, policy says no sell action
2. **SELL_LAST (DODFX):** Signal says TRIM, policy defers to last exit

In both cases, the blocked action is a **reduce/sell** action. The alternative is not "find another security to sell" — it is "accept hold, monitor for policy change."

### 5.2 DO_NOT_SELL Path

```
action_type = "MONITOR_ONLY"
action_priority = "INFORMATIONAL"
candidate_symbols = []
no_action_available = true
rationale = "DO_NOT_SELL policy in effect. Hold current position. 
             Monitor for signal reversal before re-evaluating."
```

No deployment queue lookup required. The policy overrides all sell intent.

### 5.3 SELL_LAST Path

```
action_type = "DEFERRED_REDUCE"
action_priority = "LOW"
candidate_symbols = []
no_action_available = true
rationale = "SELL_LAST policy in effect. Position may be reduced as 
             final exit step. No immediate action available."
```

### 5.4 Future Extension: Redeployment Path

When `BLOCKED_BY_POLICY` blocks a sell, released capital is not yet available. However, the operator might want to see: "When this policy clears, where should the capital go?" This is a Phase 23.6+ concern — out of scope for Phase 23.5.

### 5.5 Determination of Policy Type at Render Time

In `app.js`, the current data surface:
- `execution_state`: `"BLOCKED_BY_POLICY"`
- `effective_action`: `"MONITOR_ONLY"` (DO_NOT_SELL) or `"TRIM_SELL_LAST"` (SELL_LAST)

The effective_action suffix can be used to distinguish paths:
```javascript
if (r.effective_action === 'MONITOR_ONLY') → DO_NOT_SELL path
if (r.effective_action?.endsWith('_SELL_LAST')) → SELL_LAST path
```

---

## 6. Generation Logic Decision Tree

```
function generateNextBestAction(recommendation, deploymentQueue, overlays):

    blocker = determineBlockerType(recommendation)

    switch blocker:

        case MANDATE_BLOCKED:
            candidates = deploymentQueue
                .filter(c => overlays[c.symbol].execution_state == "EXECUTABLE")
                .filter(c => c.signal_direction == "BULLISH")
                .filter(c => ["CCL","HCA"].includes(c.narrative_tier))
                .slice(0, 5)
            return NBA(
                action_type="ACCUMULATE", priority="HIGH",
                rationale="CONCENTRATED_ALPHA mandate suppresses ETF vehicles; 
                           direct securities are preferred deployment path.",
                candidates=candidates
            )

        case ETF_GATE_FAILED:
            candidates = deploymentQueue
                .filter(c => overlays[c.symbol].execution_state == "EXECUTABLE")
                .filter(c => c.signal_direction == "BULLISH")
                .slice(0, 5)
            return NBA(
                action_type="ACCUMULATE", priority="MEDIUM",
                rationale="ETF suitability gate failed; direct securities 
                           are available alternatives.",
                candidates=candidates
            )

        case WORSENS_OVERWEIGHT:
            candidates = deploymentQueue
                .filter(c => overlays[c.symbol].execution_state == "EXECUTABLE")
                .filter(c => c.signal_direction == "BULLISH")
                // TODO Phase 23.5: add .filter(c => !owNodes.includes(c.allocation_node))
                .slice(0, 5)
            return NBA(
                action_type="ACCUMULATE", priority="MEDIUM",
                rationale="Adding this position would worsen overweight drift; 
                           select alternative candidates in non-overweight nodes.",
                candidates=candidates
            )

        case BLOCKED_BY_POLICY:
            if effective_action == "MONITOR_ONLY":
                return NBA(
                    action_type="MONITOR_ONLY", priority="INFORMATIONAL",
                    rationale="DO_NOT_SELL policy in effect. No action available.",
                    candidates=[]
                )
            else: // SELL_LAST
                return NBA(
                    action_type="DEFERRED_REDUCE", priority="LOW",
                    rationale="SELL_LAST policy in effect. Reduction deferred.",
                    candidates=[]
                )

        default:
            return null  // no NBA panel rendered
```

---

## 7. Summary

| Blocker | Candidate Source | Node Filter | Executable Filter | Max Results |
|---|---|---|---|---|
| MANDATE_BLOCKED | deployment_queue | None | YES | 5 |
| ETF_GATE_FAILED | deployment_queue | OW node exclusion (gap) | YES | 5 |
| WORSENS_OVERWEIGHT | deployment_queue | OW node exclusion (gap) | YES | 5 |
| BLOCKED_BY_POLICY (DNS) | None | — | — | 0 |
| BLOCKED_BY_POLICY (SL) | None | — | — | 0 |

**Data gap for Phase 23.5:** `allocation_node` per `DeploymentCandidate` needed for OW-node filtering in ETF_GATE_FAILED and WORSENS_OVERWEIGHT paths. Fallback: surface without node filter, add operator note.

**Status: Q3 COMPLETE — GENERATION LOGIC DESIGN CERTIFIED**
