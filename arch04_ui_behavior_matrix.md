# ARCH-04: UI Behavior Matrix

**Date:** 2026-06-09

---

## PAP Recommendation Lanes

| Scenario | execState (rec) | PAP Lane | Policy Badge Shown |
|---|---|---|---|
| All symbols EXECUTABLE, no constraints | EXECUTABLE | Actions | None |
| Mixed: some EXECUTABLE, some DEFERRED | EXECUTABLE | Actions | Per-symbol: `⏸ DODFX: Sell Last` |
| Mixed: some EXECUTABLE, some BLOCKED | EXECUTABLE | Actions | Per-symbol: `🔒 TSLA: Blocked` |
| Mixed: some EXECUTABLE, some BLOCKED+DEFERRED | EXECUTABLE | Actions | Per-symbol badges for each constrained symbol |
| All DEFERRED, none EXECUTABLE | DEFERRED_BY_POLICY | Blocked | Full-width `⏸ Sell Last — deferred` badge |
| All BLOCKED, none EXECUTABLE | BLOCKED_BY_POLICY | Blocked | Full-width `🔒 Operator Protected — not executable` badge |

---

## Per-Symbol Badge Rendering (ARCH-04, new)

Shown only when `r.execution_state === "EXECUTABLE"` AND `symbol_execution_states` contains constrained symbols.

Rendered in a `rec-sym-policy-strip` div, one compact badge per constrained symbol:
```
🔒 TSLA: Blocked   [hover: "To unblock: remove DO_NOT_SELL policy on TSLA"]
⏸ DODFX: Sell Last [hover: "To prioritize: remove SELL_LAST policy on DODFX"]
```

---

## CRA Capital Sources Panel

CRA `capital_source_builder.py` already evaluates policy **per-symbol** independently of this fix. No UI change needed. DODFX shows `⏸ Sell Last` in CRA regardless of other symbols.

## Reduction Queue (ARCH-02 panel)

Reduction Queue uses CRA capital sources (per-symbol by design). No change needed. TSLA shows `🔒 Blocked`, DODFX shows `⏸ Sell Last`.

## PAP Cat 3 (Allocation Reduction)

`_computePortfolioActions()` already uses `ov.policy_type` directly from the overlay (per-symbol). No change needed. KGC shows `EXECUTABLE` in Cat 3 already.

## PAP Cat 4 (Funding Sources)

Same as Cat 3 — per-symbol from overlay. No change needed.

## Security Overlay Panel

Per-symbol overlay data was always correct. No change needed.

---

## KGC Display — Before vs After

| Surface | Before ARCH-04 | After ARCH-04 |
|---|---|---|
| PAP Recs — lane | Blocked | **Actions** |
| PAP Recs — policy badge | `⏸ Sell Last — deferred` | None (individual KGC policy-free) |
| PAP Cat 3 | EXECUTABLE | EXECUTABLE (unchanged) |
| Reduction Queue | EXECUTABLE (CRA was already correct) | EXECUTABLE (unchanged) |
| Security Overlay | EXECUTABLE | EXECUTABLE (unchanged) |

---

## DODFX Display — Unchanged

| Surface | Before | After | Changed? |
|---|---|---|---|
| symbol_execution_states | N/A | DEFERRED_BY_POLICY | Added (new field) |
| PAP Recs (if rec is all-deferred) | ⏸ Sell Last badge | ⏸ DODFX: Sell Last badge | Minor (per-symbol label) |
| PAP Cat 3 | ⏸ SELL_LAST | ⏸ SELL_LAST | No |
| Reduction Queue | ⏸ Sell Last | ⏸ Sell Last | No |

---

## TSLA Display — Unchanged

| Surface | Before | After | Changed? |
|---|---|---|---|
| symbol_execution_states | N/A | BLOCKED_BY_POLICY | Added (new field) |
| PAP Recs (if rec is all-blocked) | 🔒 Operator Protected | 🔒 Operator Protected | No |
| PAP Cat 1 (DQ policy_suppressed) | 🔒 BLOCKED | 🔒 BLOCKED | No |
| Reduction Queue | 🔒 Blocked | 🔒 Blocked | No |
