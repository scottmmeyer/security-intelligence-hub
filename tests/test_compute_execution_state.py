"""Phase 23.3 — Unit tests for compute_execution_state.

Covers:
  - EXECUTABLE: no policy, buy flags, non-sell flags
  - BLOCKED_BY_POLICY: DO_NOT_SELL + sell/trim flags
  - DEFERRED_BY_POLICY: SELL_LAST + sell/trim flags
  - INFORMATIONAL_ONLY: CORE_ANCHOR + TRIM
  - Edge cases: empty flag, unknown flag, PREFERRED_ACCUMULATION
  - Case-insensitivity of flag input
"""
import json
import tempfile
from datetime import datetime, timezone

from src.portfolio.operator_policy import (
    OperatorPolicyRegistry,
    compute_execution_state,
)


# ─── helpers ──────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_registry(symbol: str, policy_type: str) -> OperatorPolicyRegistry:
    """Return a registry with a single active policy for symbol."""
    data = {
        "operator_policies": [
            {
                "symbol": symbol,
                "policy_type": policy_type,
                "status": "ACTIVE",
                "rationale": "test",
                "created_at": _now(),
            }
        ]
    }
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump(data, f)
    f.close()
    return OperatorPolicyRegistry.load(f.name)


def _empty_registry() -> OperatorPolicyRegistry:
    return OperatorPolicyRegistry({})


# ─── EXECUTABLE: no policy ────────────────────────────────────────────────────

def test_executable_no_policy_trim():
    reg = _empty_registry()
    state, action = compute_execution_state("TSLA", "TRIM", reg)
    assert state == "EXECUTABLE"
    assert action == "TRIM"


def test_executable_no_policy_hold():
    reg = _empty_registry()
    state, action = compute_execution_state("FIS", "HOLD", reg)
    assert state == "EXECUTABLE"
    assert action == "HOLD"


def test_executable_no_policy_accumulate():
    reg = _empty_registry()
    state, action = compute_execution_state("AAPL", "ACCUMULATE", reg)
    assert state == "EXECUTABLE"
    assert action == "ACCUMULATE"


def test_executable_empty_flag():
    reg = _empty_registry()
    state, action = compute_execution_state("AAPL", "", reg)
    assert state == "EXECUTABLE"
    assert action == "HOLD"


# ─── BLOCKED_BY_POLICY: DO_NOT_SELL ──────────────────────────────────────────

def test_blocked_do_not_sell_trim():
    reg = _make_registry("TSLA", "DO_NOT_SELL")
    state, action = compute_execution_state("TSLA", "TRIM", reg)
    assert state == "BLOCKED_BY_POLICY"
    assert action == "MONITOR_ONLY"


def test_blocked_do_not_sell_reduce_candidate():
    reg = _make_registry("TSLA", "DO_NOT_SELL")
    state, action = compute_execution_state("TSLA", "REDUCE_CANDIDATE", reg)
    assert state == "BLOCKED_BY_POLICY"
    assert action == "MONITOR_ONLY"


def test_blocked_do_not_sell_sell():
    reg = _make_registry("TSLA", "DO_NOT_SELL")
    state, action = compute_execution_state("TSLA", "SELL", reg)
    assert state == "BLOCKED_BY_POLICY"
    assert action == "MONITOR_ONLY"


def test_blocked_do_not_sell_reduce():
    reg = _make_registry("TSLA", "DO_NOT_SELL")
    state, action = compute_execution_state("TSLA", "REDUCE", reg)
    assert state == "BLOCKED_BY_POLICY"
    assert action == "MONITOR_ONLY"


def test_do_not_sell_accumulate_is_executable():
    """DO_NOT_SELL should not block non-sell actions."""
    reg = _make_registry("TSLA", "DO_NOT_SELL")
    state, action = compute_execution_state("TSLA", "ACCUMULATE", reg)
    assert state == "EXECUTABLE"
    assert action == "ACCUMULATE"


def test_do_not_sell_hold_is_executable():
    reg = _make_registry("TSLA", "DO_NOT_SELL")
    state, action = compute_execution_state("TSLA", "HOLD", reg)
    assert state == "EXECUTABLE"
    assert action == "HOLD"


# ─── DEFERRED_BY_POLICY: SELL_LAST ────────────────────────────────────────────

def test_deferred_sell_last_trim():
    reg = _make_registry("DODFX", "SELL_LAST")
    state, action = compute_execution_state("DODFX", "TRIM", reg)
    assert state == "DEFERRED_BY_POLICY"
    assert action == "TRIM_SELL_LAST"


def test_deferred_sell_last_reduce_candidate():
    reg = _make_registry("DODFX", "SELL_LAST")
    state, action = compute_execution_state("DODFX", "REDUCE_CANDIDATE", reg)
    assert state == "DEFERRED_BY_POLICY"
    assert action == "REDUCE_CANDIDATE_SELL_LAST"


def test_deferred_sell_last_reduce():
    reg = _make_registry("DODFX", "SELL_LAST")
    state, action = compute_execution_state("DODFX", "REDUCE", reg)
    assert state == "DEFERRED_BY_POLICY"
    assert action == "REDUCE_SELL_LAST"


def test_sell_last_accumulate_is_executable():
    """SELL_LAST should not affect non-sell actions."""
    reg = _make_registry("DODFX", "SELL_LAST")
    state, action = compute_execution_state("DODFX", "ACCUMULATE", reg)
    assert state == "EXECUTABLE"
    assert action == "ACCUMULATE"


# ─── INFORMATIONAL_ONLY: CORE_ANCHOR ─────────────────────────────────────────

def test_informational_core_anchor_trim():
    reg = _make_registry("MSFT", "CORE_ANCHOR")
    state, action = compute_execution_state("MSFT", "TRIM", reg)
    assert state == "INFORMATIONAL_ONLY"
    assert action == "MONITOR_ONLY"


def test_core_anchor_non_trim_is_executable():
    """CORE_ANCHOR only modifies TRIM.  HOLD and ACCUMULATE remain EXECUTABLE."""
    reg = _make_registry("MSFT", "CORE_ANCHOR")
    state, action = compute_execution_state("MSFT", "HOLD", reg)
    assert state == "EXECUTABLE"
    assert action == "HOLD"


def test_core_anchor_reduce_is_executable():
    """CORE_ANCHOR does not block REDUCE_CANDIDATE (only TRIM)."""
    reg = _make_registry("MSFT", "CORE_ANCHOR")
    state, action = compute_execution_state("MSFT", "REDUCE_CANDIDATE", reg)
    assert state == "EXECUTABLE"
    assert action == "REDUCE_CANDIDATE"


# ─── PREFERRED_ACCUMULATION ──────────────────────────────────────────────────

def test_preferred_accumulation_trim_is_executable():
    """PREFERRED_ACCUMULATION does not block any execution — annotation only."""
    reg = _make_registry("NVDA", "PREFERRED_ACCUMULATION")
    state, action = compute_execution_state("NVDA", "TRIM", reg)
    assert state == "EXECUTABLE"
    assert action == "TRIM"


# ─── Case-insensitivity ───────────────────────────────────────────────────────

def test_flag_lowercase_normalized():
    """Flag input is uppercased internally; lowercase inputs should work."""
    reg = _make_registry("TSLA", "DO_NOT_SELL")
    state, action = compute_execution_state("TSLA", "trim", reg)
    assert state == "BLOCKED_BY_POLICY"
    assert action == "MONITOR_ONLY"


def test_symbol_case_insensitive():
    """Symbol lookup is case-insensitive."""
    reg = _make_registry("TSLA", "DO_NOT_SELL")
    state, action = compute_execution_state("tsla", "TRIM", reg)
    assert state == "BLOCKED_BY_POLICY"
    assert action == "MONITOR_ONLY"


# ─── Wrong symbol — no policy match ──────────────────────────────────────────

def test_different_symbol_not_blocked():
    """Policy on TSLA should not affect AAPL."""
    reg = _make_registry("TSLA", "DO_NOT_SELL")
    state, action = compute_execution_state("AAPL", "TRIM", reg)
    assert state == "EXECUTABLE"
    assert action == "TRIM"
