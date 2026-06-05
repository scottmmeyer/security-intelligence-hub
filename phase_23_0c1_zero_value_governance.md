# Phase 23.0C.1 — Zero-Value Position Governance Design

**PAR Run**: PAR-20260603-B66B00E3  
**Date**: 2026-06-03  
**Status**: COMPLETE

---

## 1. Problem Statement

Zero-value positions (quantity > 0, market_value = 0) exist in real Fidelity portfolios as a normal artifact of:
- Fractional contra entries from corporate actions
- Odd-lot buyout residues
- Stale positions pending final settlement
- Litigation/bankruptcy holdbacks

These positions are **not data errors** — they appear in official brokerage exports. The system must handle them correctly: keep them auditable but exclude them from analytical calculations that assume economic weight.

---

## 2. Classification: ZERO_VALUE_LEGACY_POSITION

Introduce a named classification for this position type:

```
operational_state: ZERO_VALUE_LEGACY_POSITION
```

**Trigger conditions** (any of):
- `quantity > 0` AND `market_value == 0`
- Source price field is Fidelity unpriced sentinel (`--`)
- Symbol matches Fidelity internal ID pattern (e.g., `M26CNTxxx`, `Mxxxxxxx`)

---

## 3. Exclusion Matrix

| Calculation | Include Zero-Value Position? | Notes |
|-------------|------------------------------|-------|
| Total portfolio market value | NO | $0 contributes nothing, but explicit exclusion prevents edge cases |
| Allocation % (L1, L2, L3) | NO | Must be excluded — RC-02 annotation confirms |
| Deployable cash | NO | No liquidation value |
| Adjusted deployable cash | NO | No liquidation value |
| CW-DAS sizing | NO | No ESS score available |
| Funding source selection | NO | Cannot fund a purchase |
| PAP Category 1–4 routing | NO | No conviction data, no price |
| Deployment queue | NO | Not actionable |
| Reconciliation cash sum | NO | Not cash — wrong type |
| Holdings audit (visible) | YES | Must appear in audit trail |
| Position count | YES | Should count in raw census |
| Holdings CSV export | YES | Required for portability |

---

## 4. Reconciliation Handling

**Current behavior (RC-02)**:
```
RC-02 PASS | L1 Excluded (zero-value): 0.0000%
```

This confirms M26CNT069 is already excluded from allocation math (it contributes 0.0% and is noted in the exclusion bucket). The existing handling is **correct**.

**Recommended change**: RC-02's annotation `L1 Excluded (zero-value): 0.0000%` should be upgraded to list specific excluded symbols for auditability. Current form only shows the aggregate percentage. Proposed format:

```
L1 Excluded (zero-value): 0.0000% [1 position: M26CNT069]
```

---

## 5. Reconciliation Check for Zero-Value Positions

Introduce or modify a dedicated check (new check `RC-ZV01` or extend RC-02):

| Check | Logic |
|-------|-------|
| **RC-ZV01** | For each holding with `quantity > 0` and `market_value == 0`: verify it is excluded from allocation sum, deployable cash, and CW-DAS universe |
| Outcome when correct | PASS |
| Outcome when zero-value included in allocation sum | FAIL |
| Outcome when zero-value present but noted in audit | PASS with annotation |

---

## 6. Ingestion Pipeline Corrections

Three fields need correction for M26CNT069 specifically:

| Field | Current Value | Correct Value |
|-------|---------------|---------------|
| `security_type` | `ETF` | `CONTRA_ENTRY` (or new type `LEGACY_RESIDUE`) |
| `operational_state` | `ACTIVE_POSITION` | `ZERO_VALUE_LEGACY_POSITION` |
| `asset_class` | `EQUITIES` | `UNCLASSIFIED` or `LEGACY` |

**Root cause of misclassification**: The ingestion heuristic assigned `ETF` based on the symbol pattern or fallback logic when the source classification (`Cash`) was not mapped correctly. A whitelist or pattern match for Fidelity internal IDs (`M26CNT`, `M[0-9]{2}CNT`) should direct classification to `LEGACY_RESIDUE`.

---

## 7. Monitoring Rule

Track M26CNT069 (and any future zero-value positions) across PAR runs:

- If a zero-value position appears in more than 2 consecutive PAR runs (>30 calendar days): elevate to **WARN** with operator notification — "Stale contra position may require Fidelity operations contact"
- If a zero-value position appears in more than 6 consecutive runs (>90 days): elevate to **FAIL** — stalled corporate action requires resolution

---

## 8. Impact Summary

Adopting `ZERO_VALUE_LEGACY_POSITION` governance:
- Corrects `security_type` and `operational_state` misclassification
- Makes zero-value exclusion explicit and auditable per position (not just aggregate 0.0%)
- Enables future monitoring across PAR runs
- Does not change any financial calculation (RC-05 PASS, RC-02 PASS are unaffected)
- Reduces false analytical risk signals from unpriced ghost positions
