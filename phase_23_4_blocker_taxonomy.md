# Phase 23.4 — Blocker Taxonomy
**Forensic analysis only. No implementation changes.**

Generated: 2026-06-04  
Baseline: PAR-20260603-0487E65C | 853 tests | 0 failures | 1 skip

---

## Taxonomy overview

All actionable blockers in the system fall into three orthogonal dimensions:

| Dimension | Values |
|-----------|--------|
| **Layer** | Mandate | ETF Suitability | Operator Policy |
| **Scope** | Node-level | Vehicle-level | Symbol-level |
| **Reversibility** | Mandate-driven (persistent until mandate changes) | Data-driven (changes when suitability changes) | Operator-controlled (explicit override) |

---

## Taxonomy tier 1 — Mandate blockers

These blockers originate in the Portfolio Mandate Intelligence (PMI) layer and apply
at the **allocation node** level. They block entire classes of deployment action
regardless of which specific vehicle would be used.

### Type M1: INTENTIONAL drift — mandate accepts the overweight/underweight as deliberate

**Trigger**: `evaluate_drift_under_mandate()` returns a `MandateDriftInterpretation` with
`mandate_drift_label` containing `"INTENTIONAL"` and `suppress_recommendation=True`.

**Condition**: `tolerance >= 0.8` AND `raw_severity in ("LOW", "MODERATE")`.

**Primary mandate**: CONCENTRATED_ALPHA (`concentration_tolerance=0.9`).

**Meaning**: The portfolio is deviating from its target model in this node, but the mandate
explicitly accepts that deviation as portfolio policy. Adding to an underweight node would
move toward the target model — but the mandate says the drift is intentional and does not
need correction.

**Blocker codes triggered**:
- `_mandate_gate_for_node()` returns `mandate_blocked=True`
- `optimizer_decision = "MANDATE_BLOCKED"` on all INCREASE_UNDERWEIGHT recs for this node
- UI badges: `MANDATE_BLOCKED` + `CONFLICTS_WITH_MANDATE`
- Banner: "Mandate Blocked — no deployment action currently available"

**Example**: EQUITIES.US.MEGA node is 4% underweight. CONCENTRATED_ALPHA mandate has
concentration_tolerance=0.9 → tolerance=0.9 → INTENTIONAL label → block.

---

### Type M2: ON_TARGET — allocation node is within mandate tolerance

**Trigger**: `drift_direction == "ON_TARGET"` in `evaluate_drift_under_mandate()`.

**Condition**: Node is ON_TARGET (actual ≈ tactical target).

**Meaning**: There is no actionable gap to deploy into. An INCREASE_UNDERWEIGHT rec for
this node would be contradicted by the current alignment state.

**Blocker codes triggered**: Same as M1 — `suppress_recommendation=True`,
`mandate_urgency="INFORMATIONAL"` → `mandate_blocked=True`.

**Note**: M2 is less commonly visible because ON_TARGET nodes rarely generate
INCREASE_UNDERWEIGHT recommendations at all. However, if a rec is stale and the node has
re-aligned since it was generated, this path can fire.

---

## Taxonomy tier 2 — ETF suitability blockers

These blockers originate in the optimizer's ETF scoring logic and apply at the
**vehicle** level. They do not block the deployment action itself — only the specific
ETF vehicle being evaluated.

### Type V1: Low suitability tier

**Trigger**: `suit_tier == "LOW"` in `score_etf_candidate()`.

**Condition**: The pre-computed suitability note assigns this ETF a LOW suitability
rating for the target node.

**Meaning**: The ETF's exposure composition is a poor match for the target allocation
node. It may hold mostly out-of-node securities, or its style/geography doesn't align.

**Blocker codes triggered**:
- `etf_gate = "FAIL [suitability=LOW]"` on this candidate
- `optimizer_status = "ETF_GATED"` (heavy PIS discount: × 0.3)
- UI badge: `ETF_GATE_FAILED: {symbol}`

**Example**: VOO (S&P 500 broad ETF) being evaluated for EQUITIES.US.LARGE.GROWTH node —
suitability might be LOW because it includes many non-growth large-caps.

---

### Type V2: Insufficient node coverage (NCS < 10%)

**Trigger**: `ncs < 10.0` in `score_etf_candidate()`.

**Condition**: Node Coverage Score falls below the 10% minimum threshold.

**NCS formula**: `ncs = max(0.0, target_coverage - (overlap_ow × 0.6 if worsens else 0.0))`

**Meaning**: Less than 10% of this ETF's allocation would land in the target allocation
node. Most of the capital deployed via this vehicle would miss the intended allocation.

**Blocker codes triggered**: Same as V1 (`ETF_GATED`, `ETF_GATE_FAILED` badge).

**Example**: A sector ETF (e.g., XLK) being evaluated for EQUITIES.US.LARGE node — if
large-cap tech is only 8% of the target node's definition, NCS < 10%.

---

### Type V3: Worsens existing overweight

**Trigger**: `worsens_existing_overweight=True` from vehicle suitability note.

**Condition**: Buying this ETF would increase exposure to a node that is already
MODERATE+ overweight (HIGH or MODERATE severity per the alignment engine).

**Meaning**: The ETF holds meaningful weight in a node the portfolio is already too heavy
in. Deploying this vehicle would worsen the structural balance problem.

**Blocker codes triggered**:
- `etf_gate = "FAIL [worsens_overweight=True]"` on this candidate
- `optimizer_status = "ETF_GATED"` + `conflict_penalty = 20.0`
- `worsens_overweight = True` on candidate dict
- UI badges: `ETF_GATE_FAILED: {symbol}` AND `WORSENS_OVERWEIGHT` (advisory)

**Example**: SPY/IVV/VOO all hold significant US mega-cap weight. If EQUITIES.US.MEGA
is already overweight (e.g., NVDA, MSFT, AAPL heavy), any broad S&P 500 ETF would
worsen that overweight while trying to deploy into an underweight node.

**Note**: V3 is the mechanism behind the canonical "Broad ETF violates Concentrated Alpha
mandate" scenario from the Phase 23.4 spec. The mandate (CONCENTRATED_ALPHA) blocks the
node (M1), and within that blocked context, even if you tried an ETF, it would worsens
the mega-cap OW — a V3 failure.

---

## Taxonomy tier 3 — Operator policy blockers

These blockers originate in the Phase 23.3 operator policy layer and apply at the
**symbol** level. They block specific sell/trim actions where an operator has set a
DO_NOT_SELL, SELL_LAST, or CORE_ANCHOR policy.

### Type P1: DO_NOT_SELL active (BLOCKED_BY_POLICY)

**Trigger**: `compute_execution_state()` with `policy_type="DO_NOT_SELL"` and
`opportunity_flag in {"TRIM", "SELL", "REDUCE", "REDUCE_CANDIDATE"}`.

**Blocker codes**: `execution_state="BLOCKED_BY_POLICY"`, `effective_action="MONITOR_ONLY"`.

### Type P2: SELL_LAST active (DEFERRED_BY_POLICY)

**Trigger**: `policy_type="SELL_LAST"` and sell flag.

**Blocker codes**: `execution_state="DEFERRED_BY_POLICY"`, `effective_action="{FLAG}_SELL_LAST"`.

### Type P3: CORE_ANCHOR + TRIM (INFORMATIONAL_ONLY)

**Trigger**: `policy_type="CORE_ANCHOR"` and `opportunity_flag="TRIM"`.

**Blocker codes**: `execution_state="INFORMATIONAL_ONLY"`, `effective_action="MONITOR_ONLY"`.

---

## Cross-cutting blocker interaction map

```
INCREASE_UNDERWEIGHT recommendation
    ├─ Mandate layer (node-level)
    │   ├─ M1: INTENTIONAL drift → MANDATE_BLOCKED + CONFLICTS_WITH_MANDATE
    │   └─ M2: ON_TARGET → MANDATE_BLOCKED + CONFLICTS_WITH_MANDATE
    │
    └─ ETF suitability layer (vehicle-level) — only evaluated if NOT mandate_blocked
        ├─ V1: Low suitability tier → ETF_GATE_FAILED: {symbol}
        ├─ V2: NCS < 10% → ETF_GATE_FAILED: {symbol}
        └─ V3: Worsens OW → ETF_GATE_FAILED: {symbol} + WORSENS_OVERWEIGHT (advisory)

REDUCE_OVERWEIGHT / TRIM opportunity
    └─ Operator policy layer (symbol-level)
        ├─ P1: DO_NOT_SELL → BLOCKED_BY_POLICY / MONITOR_ONLY → Cat 5
        ├─ P2: SELL_LAST → DEFERRED_BY_POLICY / {FLAG}_SELL_LAST → Cat 1 tail
        └─ P3: CORE_ANCHOR + TRIM → INFORMATIONAL_ONLY / MONITOR_ONLY
```

---

## Severity classification

| Blocker Code | Severity | Operator action required |
|-------------|----------|------------------------|
| MANDATE_BLOCKED | HIGH — no deployment path exists | Change mandate or use direct-security candidates only |
| CONFLICTS_WITH_MANDATE | ADVISORY — accompanies MANDATE_BLOCKED | Same as above |
| ETF_GATE_FAILED (V3) | MEDIUM — ETF blocked, securities may still work | Use direct securities instead |
| ETF_GATE_FAILED (V1/V2) | LOW — specific ETF wrong vehicle, others may pass | Select different ETF with better node coverage |
| WORSENS_OVERWEIGHT | LOW-MEDIUM — advisory, not a hard block | Prefer direct securities or ETFs that don't double OW |
| BLOCKED_BY_POLICY | HIGH for that position — policy prevents action | Operator must revoke policy or accept suppression |

---

## Normalized field model for blockers

A complete blocker explanation requires these data fields (currently partially available,
partially absent):

| Field | Currently available | Required for diagnostics |
|-------|-------------------|------------------------|
| `blocker_code` | Yes (inferred from badge logic) | Need canonical string |
| `blocker_reason` | Partial (banner message) | Need structured reason |
| `evidence_fields` | Partial (etf_gate string) | Need typed evidence dict |
| `affected_node` | Yes (`affected_node_key`) | Available |
| `affected_vehicles` | Yes (candidate list) | Available |
| `tolerance_value` | Not surfaced | Need from mandate layer |
| `mandate_drift_label` | Yes (on rec) | Available |
| `mandate_urgency` | Yes (on rec) | Available |
| `remediation_options` | NOT available | Phase 23.4 design target |
| `alternative_path` | NOT available | Phase 23.4 design target |

---

*Phase 23.4 — Design document 2 of 5.*
