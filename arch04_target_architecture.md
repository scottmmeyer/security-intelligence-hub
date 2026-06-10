# ARCH-04: Target Architecture

**Date:** 2026-06-09

---

## Design Principles

1. **Per-symbol evaluation** — each symbol's execution state is derived from its individual policy constraint only, not from co-occurrence with constrained symbols in the same recommendation.

2. **Rec-level state = least restrictive viable state** — a recommendation is EXECUTABLE if at least one affected symbol is EXECUTABLE. This reflects that the operator CAN act on the rec (by reducing the unconstrained symbols).

3. **Additive, not destructive** — `symbol_execution_states` is a new field added to rec dicts. Existing rec-level `execution_state` and `effective_action` continue to work but now reflect per-symbol semantics.

4. **Drilldown holdings annotated** — each holding in `drilldown.holdings` gets `execution_state`, `effective_action`, `policy_type` from its individual evaluation.

5. **No scoring changes** — signal scores (ESS, composite, RPS) are never touched. This is purely an output-layer annotation change.

---

## Target State Machine

```
For each sell-context recommendation with affected_symbols = [A, B, C, D]:

  evaluate independently:
    A → BLOCKED_BY_POLICY   (DO_NOT_SELL)
    B → EXECUTABLE          (no policy)
    C → EXECUTABLE          (no policy)
    D → DEFERRED_BY_POLICY  (SELL_LAST)

  symbol_execution_states = {
    "A": {"execution_state": "BLOCKED_BY_POLICY",   "effective_action": "MONITOR_ONLY",        "policy_type": "DO_NOT_SELL"},
    "B": {"execution_state": "EXECUTABLE",           "effective_action": "REDUCE",              "policy_type": ""},
    "C": {"execution_state": "EXECUTABLE",           "effective_action": "REDUCE",              "policy_type": ""},
    "D": {"execution_state": "DEFERRED_BY_POLICY",   "effective_action": "REDUCE_SELL_LAST",   "policy_type": "SELL_LAST"},
  }

  rec.execution_state = "EXECUTABLE"  (B and C are executable)
  rec.effective_action = "REDUCE"
  rec.card_lifecycle_state = "POLICY_ADJUSTED"  (A and D are constrained)
```

---

## Rec-Level State Rules

| Condition | Rec-Level State |
|---|---|
| At least one affected symbol is EXECUTABLE | EXECUTABLE |
| No affected symbol is EXECUTABLE; some are DEFERRED | DEFERRED_BY_POLICY |
| All affected symbols are BLOCKED (or empty) | BLOCKED_BY_POLICY |

---

## PAP Lane Placement (Updated)

| Rec-Level State | PAP Lane |
|---|---|
| EXECUTABLE | Actions lane (with per-symbol constraint badges) |
| DEFERRED_BY_POLICY | Blocked lane |
| BLOCKED_BY_POLICY | Blocked lane |

Under ARCH-04, REC-5DD333BD moves from **Blocked → Actions** lane (because KGC, VEA, SBS, CVE, GTX, etc. are all EXECUTABLE).

Under ARCH-04, REC-F129627C moves from **Blocked → Actions** lane (because MU, VOO, FXAIX are EXECUTABLE; TSLA is individually blocked with badge).

---

## Per-Symbol Policy State in UI

When `r.execution_state == "EXECUTABLE"` and `r.symbol_execution_states` contains constrained symbols, the `buildCard()` function renders a compact per-symbol badge strip:

```
[Actions Lane]
Reduce EQUITIES.INTERNATIONAL (+5.9%)
  ⏸ DODFX: Sell Last   (hover: "To prioritize: remove SELL_LAST policy on DODFX")
  [▼ View 12 Holdings]
```

When `r.execution_state == "BLOCKED_BY_POLICY"` (all symbols blocked), the existing full-width blocked badge is shown.

---

## Key Invariants

- `TSLA.execution_state` is always `BLOCKED_BY_POLICY` (has DO_NOT_SELL)
- `DODFX.execution_state` is always `DEFERRED_BY_POLICY` (has SELL_LAST)
- KGC, VEA, SBS, MU, VOO, FXAIX, etc. are now always `EXECUTABLE` (no individual policy)
- Rec-level `execution_state` reflects whether any symbol is actionable, not the worst case
