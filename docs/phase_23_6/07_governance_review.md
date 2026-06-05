# Phase 23.6 — Capital Rotation Advisor
## Deliverable 7: Governance Review

**Date:** 2026-06-04
**Status:** Design Phase

---

## 7.1 Architectural Boundary Review

### Non-Negotiable Constraints Verification

| Constraint | Status | Evidence |
|------------|--------|----------|
| CW-DAS not modified | ✅ COMPLIANT | CRA reads deployment_queue.json; no score changes |
| ESS not modified | ✅ COMPLIANT | ESS fields read from overlay; no recalculation |
| Replay not modified | ✅ COMPLIANT | replay_supported field read only |
| FMI not modified | ✅ COMPLIANT | FMI outputs not referenced in CRA |
| Policy engine not modified | ✅ COMPLIANT | Policies read via API; DO_NOT_SELL blocks surfaced, not overridden |
| No new scoring models | ✅ COMPLIANT | All scoring from existing system; alignment delta is a simple approximation |

---

## 7.2 Operator Authority Preservation

The CRA is a guidance surface, not an execution engine. Every design element reinforces this:

| Principle | Design Implementation |
|-----------|----------------------|
| Operator makes all execution decisions | No auto-execution; all actions require operator confirmation |
| Include/Skip is always available | Every source card has explicit Include/Skip controls |
| Impact is approximate | "Approximate — full run required" label on every impact estimate |
| Policy gates respected | DO_NOT_SELL blocks capital pool entry; CORE_ANCHOR requires confirmation gate |
| Draft is reversible | Drafts are saved to operator folder; never modify PAR outputs |
| Full re-run available | "Run Full Re-Analysis" button triggers a fresh PAR run |

---

## 7.3 Signal Authority Hierarchy

The CRA does not alter the signal authority hierarchy:

```
Tier 1: ESS (StarMine / Zacks)     — source of signal_direction
Tier 2: Replay validation           — source of replay_supported
Tier 3: Danelfin AI                 — supplemental conviction
Tier 4: CW-DAS composite           — deployment rank
──────────────────────────────────
CRA reads Tier 1–4 outputs only.
CRA does not write to, modify, or re-order any Tier 1–4 artifacts.
```

---

## 7.4 Data Integrity Rules

| Rule | Enforcement |
|------|-------------|
| CapitalSourceRecord.estimated_proceeds must not exceed current_value_usd | Enforced at construction |
| sizing_pct must be 0.0–1.0 | Enforced at construction |
| RotationDeploymentTarget.rank must match deployment_queue.json rank | Immutable copy-through |
| RotationDeploymentTarget.deployment_score unchanged from queue | Immutable copy-through |
| Impact estimate labeled is_estimate=True always | Constant; not operator-configurable |
| Blocked sources must not appear in total_capital_pool calculation | Enforced in pool assembly |
| Bucket E sources must not appear in capital pool without explicit override | Enforced by rule R2 |

---

## 7.5 Failure Mode Analysis

| Failure Mode | Impact | Mitigation |
|-------------|--------|-----------|
| No deployment queue available | CRA panel shows "No deployment queue for current run" | Degrade gracefully; do not hide panel |
| No strategic profiles available | STI-dependent categories (Strategic Exit) excluded | Source cards labeled "STI data unavailable" |
| Tax state not configured | Tax bucket = None for all holdings | Surfaced as annotation; no blocking |
| cost_basis = None | Tax gain/loss unknown | "No cost basis data" annotation on source card |
| Empty capital pool (all blocked) | No rotation proposed | Panel shows "All candidates blocked by policy" |
| All queue targets at WARN threshold | No deployment targets | Panel shows "No deployment headroom available" |
| PAR run stale | Rotation may be based on outdated signal data | Timestamp shown on CRA panel header |

---

## 7.6 Auditability

Every RotationProposal persisted in `rotation_drafts/` carries:

- `run_id` → links to the parent PAR run that produced all inputs
- `as_of_date` → date of the analysis
- `created_at_utc` → proposal construction timestamp
- `proposal_status` → DRAFT / READY / OPERATOR_REVIEW_REQUIRED (with flags)
- `cra_version` → framework version for reproducibility

This enables full audit of "what rotation was proposed, from what data, on what date."

---

## 7.7 Scope Boundary

The following capabilities are explicitly OUT OF SCOPE for Phase 23.6:

| Out of Scope | Rationale |
|-------------|-----------|
| Automated trade execution | CRA is guidance only |
| Lot selection (FIFO, HIFO, etc.) | Requires tax lot detail; operator's responsibility |
| Wash-sale tracking | Tax planning domain; beyond CRA scope |
| Multi-account rotation | Single-account PAR model scope |
| Predictive proceeds (price-movement modeling) | No predictive models in this system |
| Cross-day or multi-step rotation sequencing | Single rotation proposal per run |
| Portfolio construction optimizer | CRA uses existing CW-DAS; no optimization |
