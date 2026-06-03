# Cash Target Integration Report — Phase 22D.6

**Phase**: 22D.6 — Strategic Cash Governance Implementation  
**Generated**: 2026-06-02  
**Mandate**: CONCENTRATED_ALPHA  
**Portfolio MV**: $475,779.42

---

## Summary

`compute_deployable_cash()` now accepts the mandate's strategic cash target as a required
parameter and uses it as the deployment floor.  The CONCENTRATED_ALPHA target of 7.0%
replaces the former hardcoded 2.0% governance minimum as the operative threshold.

The governance minimum (2.0%) remains as a hard backstop: if the mandate target were somehow
below 2%, the governance floor would still apply via `max(MIN_CASH_PCT, mandate_cash_target_pct)`.

---

## Integration Point: runner.py → deployment_queue.py

### Before (Phase 22D.5 state)

```python
# runner.py — call site (no mandate awareness)
cash_context = compute_deployable_cash(
    holdings=investable,
    total_market_value=snapshot.total_market_value,
)

# deployment_queue.py — function (hardcoded 2% floor)
def compute_deployable_cash(holdings, total_market_value):
    floor_mv = total_market_value * MIN_CASH_PCT / 100.0   # MIN_CASH_PCT = 2.0
    deployable_mv = max(0.0, cash_mv - floor_mv)           # 8.66% − 2.00% = 6.66%
    ...
```

### After (Phase 22D.6 state)

```python
# runner.py — call site (mandate-aware)
_cash_target_pct = archetype_targets.get("CASH")  # 7.0 for CONCENTRATED_ALPHA
if _cash_target_pct is None:
    raise ValueError(...)
cash_context = compute_deployable_cash(
    holdings=investable,
    total_market_value=snapshot.total_market_value,
    mandate_cash_target_pct=_cash_target_pct,
)

# deployment_queue.py — function (mandate-driven floor)
def compute_deployable_cash(holdings, total_market_value, mandate_cash_target_pct):
    effective_floor_pct = max(MIN_CASH_PCT, mandate_cash_target_pct)  # max(2.0, 7.0) = 7.0
    floor_mv = total_market_value * effective_floor_pct / 100.0
    deployable_mv = max(0.0, cash_mv - floor_mv)                       # 8.66% − 7.00% = 1.66%
    ...
```

---

## Mandate Cash Target Sources

| Mandate | YAML Node `CASH` | Effective Floor | Operator |
|---------|-----------------|-----------------|----------|
| CONCENTRATED_ALPHA | 7.0% | 7.0% | mandate wins |
| BALANCED | 5.0% | 5.0% | mandate wins |
| GROWTH | 3.0% | 3.0% | mandate wins |
| (hypothetical) | 1.0% | 2.0% | governance floor wins |

Source: `config/allocation_models/<mandate>_profile.yaml` loaded via `load_archetype_targets()`.

---

## archetype_targets Dict Availability

The `archetype_targets` dict is populated at `runner.py:568`:

```python
archetype_targets = load_archetype_targets(mandate_type)
```

For CONCENTRATED_ALPHA this resolves to:
```python
{
  "LARGE_CAP_CORE": <float>,
  "LARGE_CAP_GROWTH": <float>,
  ...
  "CASH": 7.0,
  ...
}
```

This dict is in scope at the `compute_deployable_cash()` call site 145 lines later.
Zero new loading was required for the integration.

---

## Returned `cash_context` Dict Schema

| Key | Type | Description |
|-----|------|-------------|
| `cash_mv` | float | Total cash MV ($) |
| `cash_pct` | float | Cash as % of total portfolio |
| `mandate_cash_target_pct` | float | **NEW** Mandate target used as floor input |
| `effective_floor_pct` | float | **NEW** `max(MIN_CASH_PCT, mandate_cash_target_pct)` |
| `floor_mv` | float | Effective floor in dollars |
| `excess_mv` | float | **NEW** `cash_mv − (mandate_target × total_mv / 100)` |
| `excess_pct` | float | **NEW** `excess_mv / total_mv × 100` |
| `deployable_mv` | float | Max(0, cash_mv − floor_mv) — deployable dollars |
| `deployable_pct` | float | `deployable_mv / total_mv × 100` |

---

## Key Invariants

1. `MIN_CASH_PCT = 2.0` — unchanged; governance hard minimum
2. `effective_floor_pct ≥ MIN_CASH_PCT` always
3. `deployable_mv ≥ 0` always (no negative deployable)
4. `deployable_mv + floor_mv = cash_mv` exactly when deployable > 0
5. `mandate_cash_target_pct is None` → `ValueError` (fail-closed)
