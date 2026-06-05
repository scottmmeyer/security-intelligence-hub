# Phase 23.2 — Operator Policy Taxonomy

**Date:** 2026-06-03
**Status:** APPROVED

---

## Taxonomy Overview

```
OPERATOR_POLICY
├── DO_NOT_SELL            [execution suppression — sell]
├── SELL_LAST              [execution ordering — sell]
├── CORE_ANCHOR            [execution friction — trim]
└── PREFERRED_ACCUMULATION [execution priority — buy/add]
```

Policies are grouped by the **execution dimension they modify**:

| Dimension | Policies |
|-----------|----------|
| Sell suppression | DO_NOT_SELL |
| Sell ordering | SELL_LAST |
| Trim friction | CORE_ANCHOR |
| Buy priority | PREFERRED_ACCUMULATION |

---

## Policy 1: DO_NOT_SELL

### Intent
Operator designates a holding as strategically protected from sale, regardless of intelligence signal.

### Trigger
Any execution recommendation involving reduction of position (TRIM, REDUCE_CANDIDATE, strategic exit).

### Behavior
- Symbol is excluded from sell queue and trim execution list
- `opportunity_flag` intelligence value is preserved as-is (e.g., TRIM remains)
- A separate `policy_execution_gate` field is set to `DO_NOT_SELL`
- UI annotation: `🔒 Operator Protected` badge on overlay card
- Deployment queue: not inserted into sell/reduction portion of queue

### Does NOT do
- Does not change ESS, composite score, replay data
- Does not suppress intelligence overlay from UI
- Does not affect reconciliation input data
- Does not affect alignment/allocation calculations

### Example
```
TSLA: intelligence says TRIM (VERY_BEARISH, overweight)
Policy: DO_NOT_SELL
Execution outcome: NOT sent to trim queue
Intelligence overlay: TRIM flag still displayed
UI badge: "🔒 Operator Protected"
```

### Valid Combinations
- DO_NOT_SELL + CORE_ANCHOR: valid (belt-and-suspenders; protect + confirm required if trim ever considered)
- DO_NOT_SELL + PREFERRED_ACCUMULATION: valid (hold and possibly add)
- DO_NOT_SELL + SELL_LAST: **CONFLICT — rejected at write time**

---

## Policy 2: SELL_LAST

### Intent
Operator designates a holding as acceptable to sell, but only as a last resort after all unprotected candidates have been evaluated.

### Trigger
Symbol appears in sell queue (from intelligence or allocation rebalancing).

### Behavior
- Symbol remains in sell queue
- Rank is always pushed to the **tail of the sell cohort**, after all unprotected candidates in the same PAP category
- Within the SELL_LAST cohort (if multiple), tax-aware ranking applies
- `policy_execution_gate` field: `SELL_LAST`
- UI annotation: `⏸ Sell Last` badge

### Does NOT do
- Does not prevent eventual sale
- Does not change intelligence scores
- Does not remove from overlay

### Example
```
DODFX: intelligence says HOLD (UNKNOWN signal, overweight allocation)
Policy: SELL_LAST
If allocation reduction needed: DODFX goes to tail of candidate list
UI badge: "⏸ Sell Last"
```

### Valid Combinations
- SELL_LAST + CORE_ANCHOR: valid (delay sell, add friction to trim)
- SELL_LAST + PREFERRED_ACCUMULATION: **semantically inconsistent — warn but allow** (operator may be repositioning)
- SELL_LAST + DO_NOT_SELL: **CONFLICT — rejected at write time**

---

## Policy 3: CORE_ANCHOR

### Intent
Operator designates a position as a core holding that should not be trimmed without explicit confirmation. Adds governance friction to trim recommendations.

### Trigger
Symbol receives a trim recommendation or REDUCE_CANDIDATE opportunity flag.

### Behavior
- Trim recommendation is retained in output
- UI shows an additional confirmation gate: "⚓ Core Anchor — confirm before trimming"
- `policy_execution_gate` field: `CORE_ANCHOR`
- Deployment queue: position is annotated but not reranked (ordering unchanged)
- No automatic blocking — operator must acknowledge

### Does NOT do
- Does not suppress trim recommendation
- Does not change intelligence data
- Does not alter deployment queue rank

### Example
```
MU: intelligence says HOLD/MONITOR
Policy: CORE_ANCHOR
If trim signal emerges: trim recommendation shown with confirmation gate
UI: "⚓ Core Anchor — this is a designated anchor position. Confirm trim."
```

### Valid Combinations
- CORE_ANCHOR + DO_NOT_SELL: valid (strongest protection)
- CORE_ANCHOR + PREFERRED_ACCUMULATION: valid (anchor + accumulate on weakness)
- CORE_ANCHOR + SELL_LAST: valid (sell only as last resort, confirm first)

---

## Policy 4: PREFERRED_ACCUMULATION

### Intent
Operator designates a holding as the preferred buy candidate. Buy/add recommendations receive a priority boost in the deployment queue.

### Trigger
Symbol appears in buy/add portion of deployment queue.

### Behavior
- `deployment_score` rank is adjusted upward **at the queue output layer only** — the underlying `deployment_score` value is preserved
- `policy_rank_boost` field records the boost delta applied
- UI annotation: `⭐ Preferred Accumulation` badge
- `policy_execution_gate` field: `PREFERRED_ACCUMULATION`

### Does NOT do
- Does not change `deployment_score` value
- Does not change CW-DAS composite score
- Does not change conviction tier
- Does not bypass allocation ceiling — if position is at cap, boost has no effect

### Boost Mechanics
The boost is a **rank adjustment**, not a score adjustment:
```
Base rank (from deployment_score):  VRT=1, ARW=2, PSX=3
If ARW has PREFERRED_ACCUMULATION:  ARW moves to rank 1, VRT to rank 2, PSX to rank 3
deployment_score values: unchanged
```

### Example
```
VRT: rank 1 in deployment queue (no policy needed — already first)
ARW: rank 2 in deployment queue
Policy: PREFERRED_ACCUMULATION on both VRT and ARW
Result: both promoted to top of queue (already there); no change needed
Future scenario: if VRT falls to rank 5 due to score change,
PREFERRED_ACCUMULATION ensures it still ranks in top 3
```

### Valid Combinations
- PREFERRED_ACCUMULATION + CORE_ANCHOR: valid
- PREFERRED_ACCUMULATION + DO_NOT_SELL: valid
- PREFERRED_ACCUMULATION + SELL_LAST: warn but allow (repositioning scenario)

---

## Policy Conflict Matrix

| | DO_NOT_SELL | SELL_LAST | CORE_ANCHOR | PREFERRED_ACCUMULATION |
|--|:-:|:-:|:-:|:-:|
| **DO_NOT_SELL** | — | ❌ CONFLICT | ✅ | ✅ |
| **SELL_LAST** | ❌ CONFLICT | — | ✅ | ⚠️ WARN |
| **CORE_ANCHOR** | ✅ | ✅ | — | ✅ |
| **PREFERRED_ACCUMULATION** | ✅ | ⚠️ WARN | ✅ | — |

- ❌ **CONFLICT**: Rejected at write time with 409 response
- ⚠️ **WARN**: Accepted but response includes `"warning": "Semantically inconsistent policies on symbol"`
- ✅ **COMPATIBLE**: Accepted without warning

---

## Policy Lifecycle

```
ACTIVE → (operator revokes) → REVOKED
ACTIVE → (expires_at reached) → EXPIRED (dormant, not deleted)
ACTIVE → (symbol removed from portfolio) → DORMANT (preserved for re-entry)
```

Policy records are never hard-deleted from the JSON registry. Revocation sets `status: "REVOKED"` with a `revoked_at` timestamp. This provides a full audit trail.

---

## Canonical Policy Type Values (for code/storage)

```python
POLICY_TYPES = frozenset({
    "DO_NOT_SELL",
    "SELL_LAST",
    "CORE_ANCHOR",
    "PREFERRED_ACCUMULATION",
})
```

---

## Policy Annotation Field Names (output layer)

| Field | Type | Description |
|-------|------|-------------|
| `policy_type` | str \| None | Canonical policy type or None |
| `policy_execution_gate` | str \| None | Same as policy_type; explicit gate label |
| `policy_annotation` | str \| None | Human-readable badge text for UI |
| `policy_rank_boost` | bool | True if rank was adjusted by PREFERRED_ACCUMULATION |
| `policy_protected` | bool | True if DO_NOT_SELL is active |
| `policy_rationale` | str \| None | Operator-provided rationale text |
