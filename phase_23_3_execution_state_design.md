# Phase 23.3 — Execution State Design

**Status:** APPROVED AND IMPLEMENTED  
**Date:** 2026-06-03  
**Baseline PAR:** PAR-20260603-0487E65C

---

## Problem Statement

Phase 23.2 established a working Operator Policy layer. However, PAP (Portfolio
Action Pipeline) presentation remained confusing: a symbol like TSLA could
simultaneously display `TRIM / HIGH PRIORITY` in the signal column while
carrying a `DO_NOT_SELL` policy. The intelligence and the execution intent were
in conflict with no mediation layer between them.

Phase 23.3 resolves this by adding an **execution state** that explicitly
arbitrates between intelligence and policy for every PAP row.

---

## Architecture: Intelligence → Policy → Execution

```
Intelligence Layer          Policy Layer             Execution Layer
───────────────────         ────────────────         ────────────────
opportunity_flag      →     operator_policy    →     execution_state
ess_score_text              (DO_NOT_SELL etc.)        effective_action
composite_score
```

Intelligence scores are **never modified**. The execution layer is a pure
output annotation added on top of existing overlay data.

---

## execution_state Values

| Value | Meaning |
|-------|---------|
| `EXECUTABLE` | No policy blocks execution. Intelligence action proceeds as-is. |
| `BLOCKED_BY_POLICY` | `DO_NOT_SELL` active + sell/trim flag. Execution fully suppressed. |
| `DEFERRED_BY_POLICY` | `SELL_LAST` active + sell/trim flag. Action deferred to tail of cohort. |
| `INFORMATIONAL_ONLY` | `CORE_ANCHOR` active + `TRIM` flag. Signal surfaced for awareness only; requires manual operator confirmation. |

---

## effective_action Values

| Condition | effective_action |
|-----------|-----------------|
| `BLOCKED_BY_POLICY` | `MONITOR_ONLY` |
| `DEFERRED_BY_POLICY` | `{original_flag}_SELL_LAST` (e.g. `TRIM_SELL_LAST`, `REDUCE_SELL_LAST`) |
| `INFORMATIONAL_ONLY` | `MONITOR_ONLY` |
| `EXECUTABLE` | original `opportunity_flag` (or `HOLD` if empty) |

---

## Sell Action Flags

The following `opportunity_flag` values constitute a sell/trim context:

```python
_SELL_ACTION_FLAGS = frozenset({"TRIM", "REDUCE_CANDIDATE", "SELL", "REDUCE"})
```

Only these flags trigger policy-based execution state changes.
`HOLD`, `ACCUMULATE`, `WATCH`, and other flags are always `EXECUTABLE`.

---

## Policy Type Behavior Matrix

| Policy Type | TRIM flag | REDUCE_CANDIDATE | ACCUMULATE | HOLD |
|-------------|-----------|-----------------|------------|------|
| `DO_NOT_SELL` | BLOCKED | BLOCKED | EXECUTABLE | EXECUTABLE |
| `SELL_LAST` | DEFERRED | DEFERRED | EXECUTABLE | EXECUTABLE |
| `CORE_ANCHOR` | INFORMATIONAL | EXECUTABLE | EXECUTABLE | EXECUTABLE |
| `PREFERRED_ACCUMULATION` | EXECUTABLE | EXECUTABLE | EXECUTABLE | EXECUTABLE |
| _(none)_ | EXECUTABLE | EXECUTABLE | EXECUTABLE | EXECUTABLE |

---

## Implementation

### New function: `compute_execution_state()` — `src/portfolio/operator_policy.py`

```python
def compute_execution_state(
    symbol: str,
    opportunity_flag: str,
    registry: OperatorPolicyRegistry,
) -> tuple[str, str]:
    """Returns (execution_state, effective_action)."""
```

### Extended output: `security_overlays.csv`

Two new columns added to every overlay row:

| Column | Type | Description |
|--------|------|-------------|
| `execution_state` | str | One of four execution state values |
| `effective_action` | str | The action the operator should actually take |

Computed in `runner.py` for every overlay during the CSV write pass.
Intelligence scores and existing overlay fields are unchanged.

### New test file: `tests/test_compute_execution_state.py`

21 tests covering all four execution states, all four policy types, edge cases
(empty flag, case normalization, wrong symbol, non-sell flags).

---

## Guarantee

- Intelligence scores: **never modified**
- Existing overlay fields: **unchanged**
- Reconciliation inputs: **pre-policy data, unaffected**
- Backward compatibility: symbols with no policy always return `EXECUTABLE`
