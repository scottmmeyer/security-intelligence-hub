# Phase 23.4 — Block Source Inventory
**Forensic analysis only. No implementation changes.**

Generated: 2026-06-04  
Baseline: PAR-20260603-0487E65C | 853 tests | 0 failures | 1 skip

---

## Overview

The Phase 23.4 forensic audit identified **four actionable blocker codes** that appear in the UI
(as badges, banners, or execution-state values) and traced each one to its exact generation
point in the Python layer.  The codes are:

| Code | Layer | Source File |
|------|-------|-------------|
| `MANDATE_BLOCKED` | optimizer_decision + optimizer_status | `src/portfolio/optimizer.py` |
| `ETF_GATE_FAILED` | UI badge (source: `etf_gate="FAIL"`) | `src/portfolio/optimizer.py` |
| `WORSENS_OVERWEIGHT` | UI badge (source: `worsens_overweight=True`) | `src/portfolio/optimizer.py` |
| `CONFLICTS_WITH_MANDATE` | UI badge only (source: `mandate_blocked=True`) | `ui/portfolio_alignment/app.js` |

A fifth blocker code, **`BLOCKED_BY_POLICY`**, was added in Phase 23.3 and is documented
for completeness below, but is outside the Phase 23.4 mandate.

---

## 1. MANDATE_BLOCKED

### 1a. What it is
`MANDATE_BLOCKED` appears in two places on the optimizer result dict:
- `candidate.optimizer_status = "MANDATE_BLOCKED"` (per-candidate field)
- `optimizer_result.optimizer_decision = "MANDATE_BLOCKED"` (per-recommendation field)

When an `INCREASE_UNDERWEIGHT` recommendation has `optimizer_decision="MANDATE_BLOCKED"`,
the UI shows a red "Mandate Blocked" banner and a `MANDATE_BLOCKED` badge.

### 1b. Generation point — Python

**File**: `src/portfolio/optimizer.py`

```
score_security_candidate(..., mandate_blocked: bool) -> dict   [line ~434]
    if mandate_blocked:
        final_pis = _MANDATE_BLOCKED_PIS   # 0.0
        optimizer_status = "MANDATE_BLOCKED"

score_etf_candidate(..., mandate_blocked: bool) -> dict        [line ~543]
    if mandate_blocked:
        final_pis = _MANDATE_BLOCKED_PIS   # 0.0
        optimizer_status = "MANDATE_BLOCKED"

run_parallel_optimizer(...) -> dict                            [line ~789]
    for rec of type INCREASE_UNDERWEIGHT:
        mandate_gate, mandate_blocked = _mandate_gate_for_node(target_node, mandate_interpretations)
        if mandate_blocked:
            optimizer_decision = "MANDATE_BLOCKED"
```

### 1c. The gate function

**File**: `src/portfolio/optimizer.py`, function `_mandate_gate_for_node()` [line ~264]

```python
def _mandate_gate_for_node(node_key, mandate_interpretations) -> tuple[str, bool]:
    """Return (gate_result, mandate_blocked) for a given target node."""
    for mi in mandate_interpretations:
        if mi_node != node_key: continue
        if urgency == "INFORMATIONAL" or suppress or "INTENTIONAL" in label:
            return "FAIL", True      # mandate_blocked = True
    return "PASS", False
```

Returns `mandate_blocked=True` when ANY of the following is true for the target node's
mandate interpretation:
- `mandate_urgency == "INFORMATIONAL"` 
- `suppress_recommendation == True`
- `"INTENTIONAL" in mandate_drift_label`

### 1d. Root cause — where INFORMATIONAL/INTENTIONAL originates

**File**: `src/portfolio/mandate.py`, function `evaluate_drift_under_mandate()` [line ~230]

The `mandate_interpretations` list is built by `evaluate_alignment_under_mandate()` which
calls `evaluate_drift_under_mandate()` for every alignment node.

The decision tree inside `evaluate_drift_under_mandate()`:

| Tolerance | Label suffix | suppress | mandate_urgency |
|-----------|-------------|---------|----------------|
| >= 0.8 | `INTENTIONAL` | True (if severity != HIGH) | `INFORMATIONAL` |
| >= 0.6 | `TOLERATED` | True (if severity == LOW) | varies |
| >= 0.4 | `STANDARD` | False | varies |
| < 0.4 | `STANDARD` | False | may be elevated |

The tolerance is drawn from the active `PortfolioMandate`:
- **CONCENTRATED_ALPHA**: `concentration_tolerance=0.9` → equity nodes → tolerance 0.9 → **INTENTIONAL** → `suppress_recommendation=True` → `mandate_blocked=True`
- `drift_direction == "ON_TARGET"` always → `suppress_recommendation=True`, `mandate_urgency="INFORMATIONAL"` → `mandate_blocked=True`

### 1e. Mandate registry reference

**File**: `src/portfolio/mandate.py`, `_MANDATE_REGISTRY` [line ~125]

| Mandate | concentration_tolerance | Effect on equity UW nodes |
|---------|------------------------|--------------------------|
| BALANCED | 0.3 | STANDARD → may not block |
| GROWTH | 0.6 | TOLERATED → may not block |
| DEFENSIVE | 0.2 | STRICT → never blocks (too low) |
| INCOME | 0.3 | STANDARD → may not block |
| REPLAY_OPTIMIZED | 0.7 | TOLERATED → borderline |
| CONCENTRATED_ALPHA | 0.9 | **INTENTIONAL → always blocks** equity UW adds |

### 1f. UI rendering

**File**: `ui/portfolio_alignment/app.js`

- Line ~2208: `if (decision === "MANDATE_BLOCKED")` → red banner  
- Line ~2601: `MANDATE_BLOCKED` badge rendered  
- Line ~2544: counted in `noActionable` and `mandateBlocked` counters in optimizer summary  
- Message: "This increase is blocked by the active portfolio mandate. No deployment action is currently available."

---

## 2. ETF_GATE_FAILED

### 2a. What it is
`ETF_GATE_FAILED` is a UI badge label applied to each ETF vehicle candidate that fails the
optimizer's ETF gate. The underlying field is `candidate.etf_gate = "FAIL [reasons]"`.
The optimizer_status for that candidate is `"ETF_GATED"` (internal code differs from UI label).

### 2b. Generation point — Python

**File**: `src/portfolio/optimizer.py`, function `score_etf_candidate()` [line ~543]

```python
etf_gate_fails = []
if suit_tier == "LOW":
    etf_gate_fails.append(f"suitability={suit_tier}")
if ncs < _ETF_MIN_NCS_PCT:                     # threshold: 10.0%
    etf_gate_fails.append(f"NCS={ncs:.1f}%<{_ETF_MIN_NCS_PCT}%")
if worsens:
    etf_gate_fails.append("worsens_overweight=True")

etf_gate = "PASS" if not etf_gate_fails else "FAIL"
etf_gate_reason = "; ".join(etf_gate_fails)

# ...
if etf_gate == "FAIL":
    final_pis = max(0.0, raw_pis * 0.3)   # heavy discount, not full zero
    optimizer_status = "ETF_GATED"
```

### 2c. Three distinct gate failure conditions

| Condition | Field checked | Threshold | Meaning |
|-----------|--------------|-----------|---------|
| Suitability too low | `suitability_note.suitability_tier` | `"LOW"` | ETF covers wrong node type |
| NCS below minimum | `ncs` (computed from target_coverage − ow_leakage_penalty) | < 10.0% | Less than 10% of ETF allocation lands in target node |
| Worsens overweight | `suitability_note.worsens_existing_overweight` | `True` | Buying this ETF would deepen an existing OW node |

### 2d. NCS computation chain

```
target_coverage         ← suitability_note.target_node_coverage_pct
off_target              ← suitability_note.off_target_exposure_pct
overlap_ow              ← suitability_note.overlap_with_existing_pct
worsens                 ← suitability_note.worsens_existing_overweight

ow_leakage_penalty = overlap_ow * 0.6  (if worsens, else 0.0)
ncs = max(0.0, target_coverage − ow_leakage_penalty)
```

The `vehicle_suitability_notes` are pre-computed on the `INCREASE_UNDERWEIGHT` recommendation
by the recommendations engine, not by the optimizer.

### 2e. Impact on PIS

When `etf_gate == "FAIL"`: `final_pis = max(0.0, raw_pis * 0.3)` — 70% penalty.
When `mandate_blocked == True`: `final_pis = 0.0` (absolute floor, overrides ETF gate).

### 2f. UI rendering

**File**: `ui/portfolio_alignment/app.js` [line ~2613]

```javascript
const etfFailed = candidates.filter(
    c => c.candidate_type === "ETF" && !String(c.etf_gate || "").startsWith("PASS")
);
for (const c of etfFailed) {
    badges.push(`<span ...>ETF_GATE_FAILED: ${c.symbol}</span>`);
}
```

One badge per failed ETF vehicle. Badge tooltip shows the raw `etf_gate` reason string (e.g.
`"FAIL [worsens_overweight=True]"`).

---

## 3. WORSENS_OVERWEIGHT

### 3a. What it is
`WORSENS_OVERWEIGHT` is a UI badge indicating that at least one ETF candidate would deepen
an existing MODERATE+ overweight allocation node. It is an advisory signal — it does not
independently block deployment but contributes to ETF gate failure.

### 3b. Generation point — optimizer layer

**File**: `src/portfolio/optimizer.py`, function `score_etf_candidate()` [line ~560]

```python
worsens = bool(suitability_note.get("worsens_existing_overweight", False))

if worsens:
    conflict_nodes.append("OVERWEIGHT_NODE_WORSENED")
    conflict_penalty = _T1_CONFLICT_PENALTY   # 20.0
    etf_gate_fails.append("worsens_overweight=True")

worsens_overweight field = worsens  # stored on candidate dict
```

### 3c. Generation point — vehicle suitability layer (upstream)

`worsens_existing_overweight` comes from the `vehicle_suitability_notes` dict attached to
each `INCREASE_UNDERWEIGHT` recommendation. These notes are pre-computed during recommendation
generation — **before** the optimizer runs.

**File**: `src/portfolio/recommendations.py` — vehicle suitability computation sets
`worsens_existing_overweight` when the ETF's exposure overlaps with an OVERWEIGHT node.

### 3d. Cross-cutting appearances (not optimizer)

| Location | Field/mechanism | Impact |
|----------|----------------|--------|
| `src/portfolio/deployment_queue.py` [line ~182] | `redundancy_pen = 15.0 if in_ow_node else 0.0` | Reduces CW-DAS score by 15 pts |
| `src/portfolio/unified_conviction.py` [line ~565] | `deployment_blocked = True if is_ow or redundancy_pen > 0.0` | Sets `deployment_block_reason = "Overweight allocation node active"` |
| `src/portfolio/optimizer.py` `detect_conflicts()` | T1 conflict type | Logged as a conflict when a Build rec vehicle worsens an OW Reduce rec |

### 3e. UI rendering

**File**: `ui/portfolio_alignment/app.js` [line ~2629]

```javascript
if (candidates.some(c => c.worsens_overweight)) {
    badges.push(`<span ...>WORSENS_OVERWEIGHT</span>`);
}
```

Single badge if any candidate has `worsens_overweight=true`. No per-vehicle detail shown
in the current badge — only the ETF_GATE_FAILED badge has per-vehicle specificity.

---

## 4. CONFLICTS_WITH_MANDATE

### 4a. What it is
`CONFLICTS_WITH_MANDATE` is a **UI-only badge** — the string does not appear in any Python
source code. It is an advisory overlay rendered when the optimizer's `mandate_blocked` field
is `True` on the `optimizer_metadata` object.

The badge appears **in addition to** the `MANDATE_BLOCKED` primary decision badge (if
`optimizer_decision == "MANDATE_BLOCKED"`). It is meant to indicate that the legacy vehicle
listed on the recommendation is on a mandate-blocked node.

### 4b. Generation point — JavaScript only

**File**: `ui/portfolio_alignment/app.js` [line ~2623]

```javascript
// CONFLICTS_WITH_MANDATE — legacy vehicle on a mandate-blocked node
if (om.mandate_blocked) {
    badges.push(`<span class="opt-badge opt-badge-CONFLICTS_WITH_MANDATE">CONFLICTS_WITH_MANDATE</span>`);
}
```

### 4c. Source data field

`om.mandate_blocked` is the `mandate_blocked` field on the `optimizer_metadata` object
returned by `run_parallel_optimizer()`.

**File**: `src/portfolio/optimizer.py`, `_build_result()` [line ~192]

```python
def _build_result(
    ...
    optimizer_decision: str,
    mandate_blocked: bool,
    ...
) -> dict:
    return {
        ...
        "mandate_blocked": mandate_blocked,
        ...
    }
```

`mandate_blocked` is the same Boolean derived from `_mandate_gate_for_node()` — i.e., the
same underlying condition that drives `MANDATE_BLOCKED`.

### 4d. Distinction from MANDATE_BLOCKED

| Aspect | MANDATE_BLOCKED | CONFLICTS_WITH_MANDATE |
|--------|----------------|----------------------|
| Layer | Python + UI | UI only |
| What it blocks | The entire deployment action | Advisory: legacy vehicle conflicts |
| When shown | optimizer_decision = "MANDATE_BLOCKED" | mandate_blocked = True (same condition) |
| Actionable | No (deployment is blocked) | Advisory only |
| Evidence shown | None (banner message only) | None |

In practice, both badges fire simultaneously because they share the same trigger condition.
The distinction is historical — `CONFLICTS_WITH_MANDATE` was likely added as a separate
advisory badge for cases where mandate_blocked is True but the optimizer_decision might
be something other than "MANDATE_BLOCKED" (e.g., if only some candidates are blocked).

---

## 5. BLOCKED_BY_POLICY (Phase 23.3 — included for completeness)

### 5a. What it is
`BLOCKED_BY_POLICY` is the `execution_state` value for positions where an operator policy
(DO_NOT_SELL) prevents a sell/trim action that intelligence has flagged.

### 5b. Generation point

**File**: `src/portfolio/operator_policy.py`, `compute_execution_state()` [line ~353]

```python
if policy_type == "DO_NOT_SELL" and flag in _SELL_ACTION_FLAGS:
    return "BLOCKED_BY_POLICY", "MONITOR_ONLY"
```

**File**: `src/portfolio/runner.py` [line ~867] — writes `execution_state` and
`effective_action` to the `security_overlays.csv` output.

### 5c. UI

Cat 5 "Policy-Suppressed Actions" section in `app.js`. Items with
`execution_state == "BLOCKED_BY_POLICY"` are routed out of Cat 1 and into Cat 5.

---

## Field reference summary

| Field | Type | Owner | Meaning |
|-------|------|-------|---------|
| `optimizer_decision` | str | `optimizer_metadata` dict | Overall optimizer outcome per rec |
| `optimizer_status` | str | Per-candidate dict | Per-candidate gate result |
| `mandate_blocked` | bool | `optimizer_metadata` dict | True if mandate gates the entire node |
| `mandate_gate` | str | Per-candidate dict | `PASS` / `FAIL` — gate result for this candidate's node |
| `etf_gate` | str | Per-candidate dict | `PASS` / `FAIL [reasons]` for ETF vehicles |
| `worsens_overweight` | bool | Per-candidate dict | True if this ETF deepens OW nodes |
| `execution_state` | str | `security_overlays.csv` | Policy-layer execution disposition |
| `effective_action` | str | `security_overlays.csv` | Policy-modified recommended action |

---

*Phase 23.4 — Design document 1 of 5.*
