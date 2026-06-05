# Phase 23.4 — Unblock Action Framework
**Forensic analysis only. No implementation changes.**

Generated: 2026-06-04  
Baseline: PAR-20260603-0487E65C | 853 tests | 0 failures | 1 skip

---

## Purpose

For every blocker type identified in the taxonomy, this document defines:

1. **Human explanation** — what the operator needs to understand
2. **Evidence fields** — what data fields are needed to support the explanation
3. **Remediation actions** — concrete steps the operator can take
4. **Alternative recommendation path** — what the system can offer instead of a blocked action

---

## Framework 1 — MANDATE_BLOCKED (M1: INTENTIONAL drift)

### Human explanation

> "This allocation node is underweight versus your target model, but your active portfolio
> mandate (Concentrated Alpha) intentionally accepts equity drift. The mandate's
> concentration tolerance (0.9) classifies this shortfall as deliberate portfolio policy,
> not a correction target. No deployment action will be generated until the mandate is
> changed or this node's drift label is reassessed."

### Evidence fields required

| Field | Source | Meaning |
|-------|--------|---------|
| `mandate_type` | `mandate.mandate_type` | Active mandate name (e.g., "CONCENTRATED_ALPHA") |
| `concentration_tolerance` | `PortfolioMandate.concentration_tolerance` | Tolerance value that triggered INTENTIONAL classification |
| `mandate_drift_label` | `MandateDriftInterpretation.mandate_drift_label` | e.g., "INTENTIONAL_UNDERWEIGHT" |
| `mandate_urgency` | `MandateDriftInterpretation.mandate_urgency` | "INFORMATIONAL" |
| `raw_drift_pct` | `MandateDriftInterpretation.raw_drift_pct` | Actual gap size (e.g., −4.2pp) |
| `affected_node_key` | Recommendation | Which node is blocked (e.g., "EQUITIES.US.MEGA") |
| `node_label` | Recommendation | Human name (e.g., "US Mega Cap") |

### Remediation actions

| Priority | Action | Effect |
|----------|--------|--------|
| 1 | **Switch mandate** from CONCENTRATED_ALPHA to GROWTH or BALANCED | Lowers concentration_tolerance below 0.8 → removes INTENTIONAL label → unblocks deployment |
| 2 | **Use direct-security candidates** (do not rely on ETF vehicles) | Securities bypass ETF gate; if mandate_blocked=False after mandate change, securities get full PIS |
| 3 | **Accept the block** and allow natural drift correction over time | Appropriate if concentrated alpha strategy is intentional and desired |
| 4 | **Target high-PIS direct securities** for the node now | Even if mandate blocks INCREASE_UNDERWEIGHT recs, the operator can manually add positions to the node |

### Alternative recommendation path

When MANDATE_BLOCKED fires on an INCREASE_UNDERWEIGHT recommendation, the system should
surface direct-security alternatives from the CW-DAS deployment queue for that node:

- Query deployment queue for candidates whose `target_node` matches the blocked node
- Surface top 3–5 by `deployment_score` as "suggested alternatives" — not as recs, but as informational paths
- Example: If EQUITIES.US.MEGA is blocked, surface VRT, DELL, LRCX, ARW, CAH (the spec's example candidates) from the queue

---

## Framework 2 — MANDATE_BLOCKED (M2: ON_TARGET node)

### Human explanation

> "This allocation node is currently on target — there is no meaningful gap to deploy into.
> The recommendation may be stale, or the node has rebalanced since analysis was run.
> No deployment action is needed."

### Evidence fields required

| Field | Source | Meaning |
|-------|--------|---------|
| `drift_direction` | `AllocationAlignmentResult.drift_direction` | "ON_TARGET" |
| `raw_drift_pct` | `AllocationAlignmentResult.drift_pct` | Gap size (near 0) |
| `mandate_urgency` | "INFORMATIONAL" | Confirms ON_TARGET treatment |
| `affected_node_key` | Recommendation | Which node |

### Remediation actions

| Priority | Action | Effect |
|----------|--------|--------|
| 1 | **Re-run portfolio analysis** with current holdings | May resolve stale recommendation if node has rebalanced |
| 2 | **No action required** — node is balanced | Hold current allocation |

### Alternative recommendation path

None needed — if the node is on target, no deployment action is appropriate.

---

## Framework 3 — ETF_GATE_FAILED (V1: Low suitability)

### Human explanation

> "The ETF vehicle [SYMBOL] has a LOW suitability rating for [NODE] — it does not cover
> the target allocation tier with sufficient precision. This ETF's holdings primarily land
> in a different style, geography, or market-cap tier than the node being deployed into.
> Consider using a more targeted ETF or a direct security."

### Evidence fields required

| Field | Source | Meaning |
|-------|--------|---------|
| `symbol` | Failed ETF candidate | Which vehicle failed |
| `etf_gate` | Candidate `etf_gate` field | Full reason string, e.g., `"FAIL [suitability=LOW]"` |
| `suitability_tier` | Candidate `suitability_tier` | "LOW" |
| `ncs` (Node Coverage Score) | Candidate `ncs` | How much lands in target node (%) |
| `target_node` | Recommendation | Which node the rec targets |
| `off_target_exposure_pct` | Vehicle suitability note | How much of the ETF is off-node |

### Remediation actions

| Priority | Action | Effect |
|----------|--------|--------|
| 1 | **Select a higher-NCS ETF** for this node | A more focused ETF covering the target node may pass |
| 2 | **Use direct securities** instead | Direct holdings get perfect NCS (100%) by definition |
| 3 | **Accept ETF_GATED status** and deploy at discounted PIS | The ETF still receives 30% of its raw PIS — it may still be an acceptable vehicle if no better option exists |

### Alternative recommendation path

- Present existing SECURITY candidates for the node that have positive PIS
- If no security candidates pass, show "no viable implementation path" message

---

## Framework 4 — ETF_GATE_FAILED (V2: NCS < 10%)

### Human explanation

> "The ETF vehicle [SYMBOL] has insufficient node coverage for [NODE]: only [NCS]% of its
> allocation reaches the target tier (minimum required: 10%). Deploying this ETF would
> deliver most capital into other allocation nodes, not the intended one."

### Evidence fields required

| Field | Source | Meaning |
|-------|--------|---------|
| `symbol` | Failed ETF candidate | Which vehicle |
| `ncs` | Candidate `ncs` | Actual coverage percentage |
| `target_node_coverage_pct` | Vehicle suitability note | Raw target coverage before OW penalty |
| `overlap_with_existing_pct` | Vehicle suitability note | How much overlaps with OW nodes |
| `etf_gate` | Full reason string | `"FAIL [NCS=7.2%<10%]"` |

### Remediation actions

| Priority | Action | Effect |
|----------|--------|--------|
| 1 | **Use a more targeted ETF** with higher node coverage | ETFs with single-sector or single-style focus have higher NCS for narrow nodes |
| 2 | **Use direct securities** | NCS = 100% for direct holdings |
| 3 | **Combine two ETFs** that together cover the node | Operator discretion — system does not score combinations |

### Alternative recommendation path

- Show top SECURITY candidates with positive PIS for the target node
- Note that ETF-based alternatives need higher node concentration

---

## Framework 5 — ETF_GATE_FAILED + WORSENS_OVERWEIGHT (V3)

### Human explanation

> "The ETF vehicle [SYMBOL] would worsen the existing overweight in [OW_NODE].
> Buying this ETF while [OW_NODE] is already [OW_PCT]pp overweight would deepen
> the structural imbalance the system is trying to correct. This ETF fails the gate
> and incurs a 20-point conflict penalty."

### Evidence fields required

| Field | Source | Meaning |
|-------|--------|---------|
| `symbol` | Failed ETF candidate | Which vehicle |
| `worsens_overweight` | Candidate field | True |
| `overlap_with_existing_pct` | Vehicle suitability note | How much OW-node exposure this ETF adds |
| `overweight_nodes` | Alignment results | List of {node_key, drift_pct} for all MODERATE+ OW nodes |
| `conflict_penalty` | Candidate components | 20.0 points |
| `etf_gate` | Full reason string | `"FAIL [worsens_overweight=True]"` |

### Remediation actions

| Priority | Action | Effect |
|----------|--------|--------|
| 1 | **Use direct securities** in the target node that do NOT sit in the overweight node | Eliminates cross-node leakage entirely |
| 2 | **Rebalance OW nodes first** (run a REDUCE_OVERWEIGHT action) | Once OW node severity drops to LOW/NONE, ETF gate condition may clear |
| 3 | **Use a narrower ETF** with zero exposure to the OW node | May exist for specific sub-sectors or styles |

### Alternative recommendation path

This is the primary use case for direct-security alternatives:
- Surface CW-DAS queue candidates for the target node
- Exclude any candidate whose allocation node key prefix matches a MODERATE+ OW node
- Present 3–5 alternatives with: symbol, deployment_score, narrative_tier, ess_score_text

**Example from spec**: 
- Node: EQUITIES.US.MEGA (target, underweight)
- Blocked ETFs: VOO, IVV, SPY (all heavily weighted in EQUITIES.US.MEGA OW positions)
- Suggested direct alternatives: VRT, DELL, LRCX, ARW, CAH (directly in the target node, no OW leakage)

---

## Framework 6 — CONFLICTS_WITH_MANDATE (advisory badge)

### Human explanation

> "The legacy vehicle(s) referenced in this recommendation sit in a mandate-blocked
> allocation node. These vehicles cannot be used to implement this recommendation
> under the current mandate settings. Consider direct-security alternatives."

### Evidence fields required

Same as MANDATE_BLOCKED (Framework 1) — this badge is co-triggered with MANDATE_BLOCKED.

### Remediation actions

Same as Framework 1 — address the underlying mandate block.

### Alternative recommendation path

Same as Framework 1.

---

## Framework 7 — BLOCKED_BY_POLICY (Phase 23.3)

### Human explanation

> "The intelligence engine recommends [ACTION] for [SYMBOL], but the operator has set
> a [POLICY_TYPE] policy on this position. The action has been suppressed — no trade
> execution should occur. The signal is preserved for monitoring."

### Evidence fields required

| Field | Source | Meaning |
|-------|--------|---------|
| `symbol` | Position | Which symbol is affected |
| `policy_type` | Operator policy | "DO_NOT_SELL" / "SELL_LAST" / "CORE_ANCHOR" |
| `opportunity_flag` | Security overlay | Original flagged action (e.g., "TRIM") |
| `execution_state` | Security overlay | "BLOCKED_BY_POLICY" |
| `effective_action` | Security overlay | "MONITOR_ONLY" |
| `policy_annotation` | DeploymentCandidate | Human badge text |

### Remediation actions

| Priority | Action | Effect |
|----------|--------|--------|
| 1 | **Revoke the policy** on this symbol | Signal becomes executable |
| 2 | **Change policy to SELL_LAST** | Defers action to tail of queue rather than blocking entirely |
| 3 | **Accept suppression** and monitor | Appropriate for DO_NOT_SELL positions (tax, emotional, concentration constraint) |

### Alternative recommendation path

Cat 5 "Policy-Suppressed Actions" section shows blocked positions with their original
intelligence signal preserved as a monitoring view.

---

## Summary: framework selection matrix

| Blocker observed | Framework to apply | Primary remediation |
|-----------------|-------------------|---------------------|
| `MANDATE_BLOCKED` on EQUITIES.US.MEGA with CONCENTRATED_ALPHA | F1 | Switch mandate OR use direct securities |
| `MANDATE_BLOCKED` on ON_TARGET node | F2 | Re-run analysis, no action needed |
| `ETF_GATE_FAILED` + `suitability=LOW` | F3 | Use more targeted ETF or direct security |
| `ETF_GATE_FAILED` + `NCS<10%` | F4 | Use more targeted ETF or direct security |
| `ETF_GATE_FAILED` + `worsens_overweight=True` | F5 | Use direct securities (spec example: VRT, DELL, LRCX, ARW, CAH) |
| `CONFLICTS_WITH_MANDATE` | F6 (= F1) | Same as MANDATE_BLOCKED |
| `WORSENS_OVERWEIGHT` advisory | F5 | Use direct securities |
| `BLOCKED_BY_POLICY` | F7 | Revoke policy or change to SELL_LAST |

---

*Phase 23.4 — Design document 3 of 5.*
