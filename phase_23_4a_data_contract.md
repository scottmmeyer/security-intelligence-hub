# Phase 23.4A — Q2: NextBestAction Data Contract Design
**DESIGN ONLY — NO IMPLEMENTATION**
**Generated:** 2026-06-04
**Baseline:** PAR-20260604-8DB0393D | 853 tests | 0 failures | 1 skip

---

## 1. Schema Design

### 1.1 Proposed `NextBestAction` Structure

```json
NextBestAction {
    // --- Core identity ---
    "blocker_type": string,              // MANDATE_BLOCKED | ETF_GATE_FAILED |
                                         //   WORSENS_OVERWEIGHT | BLOCKED_BY_POLICY
    "blocked_symbol": string | null,     // symbol that was blocked (null for node-level blocks)
    "blocked_node": string | null,       // affected_node_key (null for security-level blocks)

    // --- Action guidance ---
    "action_type": string,               // ACCUMULATE | TRIM | REDUCE | HOLD | REBALANCE
    "action_priority": string,           // HIGH | MEDIUM | LOW | NONE
    "rationale": string,                 // Human-readable explanation (1 sentence)

    // --- Alternatives ---
    "candidate_symbols": string[],       // Ordered: highest-ranked first, max 5
    "deployment_scores": number[],       // Parallel to candidate_symbols
    "narrative_tiers": string[],         // Parallel to candidate_symbols (CCL / HCA / etc.)
    "execution_states": string[],        // Parallel — EXECUTABLE | BLOCKED_BY_POLICY | etc.

    // --- Portfolio effect ---
    "expected_portfolio_effect": string, // IMPROVES_ALIGNMENT | NEUTRAL | MAINTAINS_DRIFT
    "headroom_available": boolean,       // True if at least one candidate has > 0% headroom

    // --- Metadata ---
    "generation_source": string,         // DEPLOYMENT_QUEUE | ALIGNMENT_NODES | NONE
    "alternatives_count": number,        // Total candidates considered before top-N selection
    "no_action_available": boolean       // True if no executable alternatives found
}
```

### 1.2 Field-by-Field Analysis

#### Required Fields

| Field | Required? | Rationale |
|---|---|---|
| `blocker_type` | REQUIRED | Determines which alternative-generation path to use |
| `action_type` | REQUIRED | Core operator guidance — what to do |
| `action_priority` | REQUIRED | Triage signal — operator attention allocation |
| `rationale` | REQUIRED | Single-sentence human explanation |
| `candidate_symbols` | REQUIRED (may be empty `[]`) | Primary content of the panel |
| `deployment_scores` | REQUIRED | Needed for ranking comparison |
| `execution_states` | REQUIRED | Filters candidates to only executable ones at render |
| `no_action_available` | REQUIRED | Explicit signal when framework finds no path |

#### Conditionally Required Fields

| Field | Required When | Notes |
|---|---|---|
| `blocked_symbol` | Security-level block | MANDATE_BLOCKED on security rec, BLOCKED_BY_POLICY |
| `blocked_node` | Node-level block | INCREASE_UNDERWEIGHT rec blocked by mandate |
| `narrative_tiers` | DEPLOYMENT_QUEUE source | Available from `DeploymentCandidate.narrative_tier` |
| `headroom_available` | Any ACCUMULATE action | Used to qualify the alternative |
| `expected_portfolio_effect` | ACCUMULATE / REBALANCE | Less relevant for TRIM path |

#### Optional Fields

| Field | Optional | Default |
|---|---|---|
| `alternatives_count` | Optional | 0 |
| `generation_source` | Optional | "UNKNOWN" |

---

## 2. Source Data Mapping

### 2.1 Where Each Field Comes From

```
deployment_queue.json        security_overlays.csv       operator_policy state
       │                              │                           │
       │  rank                        │  execution_state          │
       │  symbol                      │  effective_action         │
       │  deployment_score       ─────┤  opportunity_flag         │
       │  narrative_tier              │  signal_direction         │
       │  notes (headroom%)           │                           │
       └──────────┬───────────────────┘                           │
                  │                                               │
                  ▼                                               │
         candidate_symbols[]                          execution_states[]
         deployment_scores[]                          (per-candidate filter)
         narrative_tiers[]
         headroom_available
```

The `NextBestAction` object is a **read-only projection** over existing pipeline outputs. It does not require any new computed fields in Python.

### 2.2 Blocker → Action Type Mapping

| Blocker Type | action_type | action_priority | generation_source |
|---|---|---|---|
| `MANDATE_BLOCKED` (UW node) | `ACCUMULATE` | `HIGH` | `DEPLOYMENT_QUEUE` |
| `ETF_GATE_FAILED` | `ACCUMULATE` (direct security) | `MEDIUM` | `DEPLOYMENT_QUEUE` |
| `WORSENS_OVERWEIGHT` | `ACCUMULATE` (non-OW node) | `MEDIUM` | `DEPLOYMENT_QUEUE` |
| `BLOCKED_BY_POLICY` (TRIM/REDUCE) | `HOLD` or `MONITOR_ONLY` | `LOW` | `DEPLOYMENT_QUEUE` |
| `BLOCKED_BY_POLICY` (DO_NOT_SELL) | `MONITOR_ONLY` | `INFORMATIONAL` | `NONE` |

---

## 3. Persistence Requirements

### 3.1 Assessment

`NextBestAction` is a **stateless derived object**. It should be computed at read time in the UI (from `deployment_queue.json` + `security_overlays.csv`) rather than persisted to a new file.

**Rationale:**
- The deployment queue is already written per PAR run — it is the authoritative ranking surface
- Persisting NBA separately would create a staleness risk if the queue changes
- The UI already loads both `deployment_queue.json` and `security_overlays.csv`
- Generation logic is O(N) over a max-32-entry queue — trivially fast at render time

**Verdict:** No new persistence layer required. NBA is generated client-side (in `app.js`) from the existing PAR data files already loaded by the UI.

### 3.2 What This Means for Implementation Scope

| Layer | Change Required |
|---|---|
| Python pipeline | NONE — no new file output, no scoring changes |
| `runner.py` | NONE |
| `deployment_queue.py` | NONE |
| PAR output files | NONE |
| `app.js` | YES — `_buildNextBestAction(r)` function + rendering |
| `app.js` data loading | Possibly — verify `deployment_queue.json` is already fetched |

---

## 4. Edge Cases and Constraints

### 4.1 `candidate_symbols` = Empty Array

When `candidate_symbols = []`:
- `no_action_available = true`
- `action_type = "HOLD"` or `"NONE"`
- `rationale = "No executable alternatives found in current deployment queue."`
- UI renders: **"No alternative action available at this time"** message (not blank)

### 4.2 All Candidates Are Blocked by Policy

If the top-N candidates from the deployment queue are all `BLOCKED_BY_POLICY`, the framework should:
1. Surface them anyway with their `execution_states`
2. Set `action_priority = LOW`
3. Include a note: "Suggested candidates exist but are policy-protected"

This preserves visibility without implying they are immediately executable.

### 4.3 BLOCKED_BY_POLICY with DO_NOT_SELL

TSLA: `execution_state=BLOCKED_BY_POLICY`, `effective_action=MONITOR_ONLY`
- The blocked action is TRIM (sell direction)
- Next Best Action is not "find another security to trim" — it is "no action, monitor"
- `candidate_symbols = []`, `action_type = "MONITOR_ONLY"`, `no_action_available = true`
- Rationale: "DO_NOT_SELL policy in effect — monitor signal for future review."

### 4.4 Node-Level vs Security-Level Block

```
Node block (EQUITIES.US.LARGE → MANDATE_BLOCKED):
    blocked_symbol = null
    blocked_node = "EQUITIES.US.LARGE"
    candidate_symbols = ["VRT", "DELL", "LRCX", "ARW", "CAH"]
    (from deployment_queue, BULLISH+replay eligible)

Security block (TSLA → BLOCKED_BY_POLICY):
    blocked_symbol = "TSLA"
    blocked_node = null
    candidate_symbols = []
    no_action_available = true
```

### 4.5 Multiple Simultaneous Blockers

A recommendation can have both `mandate_blocked=true` AND `worsens_overweight=true` (e.g., VOO on EQUITIES.US.LARGE: ETF gate FAIL with `worsens_overweight=True`). In this case:
- `blocker_type` = primary blocker (use `MANDATE_BLOCKED` when `mandate_blocked=true`)
- Secondary blockers documented in BLOCK DIAGNOSTICS, not in NBA panel
- NBA panel shows one action type and one candidate set

---

## 5. Schema Variants by Blocker Type

### 5.1 MANDATE_BLOCKED — Node Level
```json
{
  "blocker_type": "MANDATE_BLOCKED",
  "blocked_symbol": null,
  "blocked_node": "EQUITIES.US.LARGE",
  "action_type": "ACCUMULATE",
  "action_priority": "HIGH",
  "rationale": "CONCENTRATED_ALPHA mandate suppresses ETF allocation; direct securities ranked by conviction are alternative deployment path.",
  "candidate_symbols": ["VRT", "DELL", "LRCX", "ARW", "CAH"],
  "deployment_scores": [94.97, 92.45, 91.56, 93.93, 91.58],
  "narrative_tiers": ["CORE_CONVICTION_LEADER", "HCA", "HCA", "HCA", "HCA"],
  "execution_states": ["EXECUTABLE", "EXECUTABLE", "EXECUTABLE", "EXECUTABLE", "EXECUTABLE"],
  "expected_portfolio_effect": "IMPROVES_ALIGNMENT",
  "headroom_available": true,
  "generation_source": "DEPLOYMENT_QUEUE",
  "alternatives_count": 5,
  "no_action_available": false
}
```

### 5.2 BLOCKED_BY_POLICY — DO_NOT_SELL
```json
{
  "blocker_type": "BLOCKED_BY_POLICY",
  "blocked_symbol": "TSLA",
  "blocked_node": null,
  "action_type": "MONITOR_ONLY",
  "action_priority": "INFORMATIONAL",
  "rationale": "DO_NOT_SELL policy in effect. No sell action executable. Monitor for signal reversal.",
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

---

## 6. Summary

| Attribute | Decision |
|---|---|
| Schema style | Flat JSON — no nested sub-objects |
| Persistence | None — derived at read time in app.js |
| Python changes required | NONE |
| Null handling | Explicit `null` for inapplicable symbol/node fields |
| Empty candidate_symbols | Valid state — `no_action_available=true` |
| Multi-blocker handling | Primary blocker wins; others go to BLOCK DIAGNOSTICS |

**Status: Q2 COMPLETE — DATA CONTRACT DESIGN CERTIFIED**
