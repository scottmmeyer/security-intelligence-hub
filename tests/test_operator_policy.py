"""Phase 23.2 — Unit tests for OperatorPolicyRegistry and OperatorPolicy.

Covers:
  - OperatorPolicy.is_active(): ACTIVE, REVOKED, expired
  - OperatorPolicyRegistry.load(): from file, missing file, empty policies
  - active_policy_type(), predicates, all_active(), policy_snapshot()
  - check_policy_conflict() and check_policy_warning()
"""
import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.portfolio.operator_policy import (
    OperatorPolicy,
    OperatorPolicyRegistry,
    POLICY_TYPES,
    POLICY_CONFLICTS,
    check_policy_conflict,
    check_policy_warning,
    build_policy_annotations,
    build_policy_suppressed_entries,
)


# ─── helpers ──────────────────────────────────────────────────────────────────

def _make_state(policies: list[dict]) -> str:
    """Write a temp state file and return its path."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump({"operator_policies": policies}, f)
    f.close()
    return f.name


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _future(days: int = 30) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def _past(days: int = 1) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


# ─── OperatorPolicy.is_active ─────────────────────────────────────────────────

def test_policy_is_active_basic():
    p = OperatorPolicy(
        symbol="TSLA",
        policy_type="DO_NOT_SELL",
        status="ACTIVE",
        rationale="Concentrated position",
        created_at=_now(),
        expires_at=None,
        revoked_at=None,
    )
    assert p.is_active() is True


def test_policy_is_active_revoked():
    p = OperatorPolicy(
        symbol="TSLA",
        policy_type="DO_NOT_SELL",
        status="REVOKED",
        rationale="",
        created_at=_now(),
        expires_at=None,
        revoked_at=_now(),
    )
    assert p.is_active() is False


def test_policy_is_active_expired():
    p = OperatorPolicy(
        symbol="TSLA",
        policy_type="DO_NOT_SELL",
        status="ACTIVE",
        rationale="",
        created_at=_now(),
        expires_at=_past(1),
        revoked_at=None,
    )
    assert p.is_active() is False


def test_policy_is_active_not_yet_expired():
    p = OperatorPolicy(
        symbol="TSLA",
        policy_type="DO_NOT_SELL",
        status="ACTIVE",
        rationale="",
        created_at=_now(),
        expires_at=_future(30),
        revoked_at=None,
    )
    assert p.is_active() is True


def test_policy_is_active_superseded():
    p = OperatorPolicy(
        symbol="TSLA",
        policy_type="SELL_LAST",
        status="SUPERSEDED",
        rationale="",
        created_at=_now(),
        expires_at=None,
        revoked_at=None,
    )
    assert p.is_active() is False


# ─── OperatorPolicyRegistry.load ─────────────────────────────────────────────

def test_registry_load_missing_file():
    reg = OperatorPolicyRegistry.load("/tmp/__nonexistent_sih_test__.json")
    assert reg.all_active() == {}


def test_registry_load_empty_policies():
    path = _make_state([])
    reg = OperatorPolicyRegistry.load(path)
    assert reg.all_active() == {}


def test_registry_load_tsla_do_not_sell():
    path = _make_state([{
        "symbol": "TSLA",
        "policy_type": "DO_NOT_SELL",
        "status": "ACTIVE",
        "rationale": "Concentrated position — not a sell candidate",
        "created_at": _now(),
        "expires_at": None,
        "revoked_at": None,
    }])
    reg = OperatorPolicyRegistry.load(path)
    assert reg.is_do_not_sell("TSLA") is True
    assert reg.active_policy_type("TSLA") == "DO_NOT_SELL"
    assert len(reg.all_active()) == 1  # dict with 1 entry


def test_registry_load_dodfx_sell_last():
    path = _make_state([{
        "symbol": "DODFX",
        "policy_type": "SELL_LAST",
        "status": "ACTIVE",
        "rationale": "Fund — sell only after individual positions exhausted",
        "created_at": _now(),
        "expires_at": None,
        "revoked_at": None,
    }])
    reg = OperatorPolicyRegistry.load(path)
    assert reg.is_sell_last("DODFX") is True
    assert reg.active_policy_type("DODFX") == "SELL_LAST"


def test_registry_load_multiple_policies():
    path = _make_state([
        {"symbol": "TSLA", "policy_type": "DO_NOT_SELL", "status": "ACTIVE",
         "rationale": "", "created_at": _now(), "expires_at": None, "revoked_at": None},
        {"symbol": "DODFX", "policy_type": "SELL_LAST", "status": "ACTIVE",
         "rationale": "", "created_at": _now(), "expires_at": None, "revoked_at": None},
        {"symbol": "AAPL", "policy_type": "CORE_ANCHOR", "status": "REVOKED",
         "rationale": "", "created_at": _now(), "expires_at": None, "revoked_at": _now()},
    ])
    reg = OperatorPolicyRegistry.load(path)
    active = reg.all_active()
    assert len(active) == 2
    assert reg.is_do_not_sell("TSLA") is True
    assert reg.is_sell_last("DODFX") is True
    assert reg.active_policy_type("AAPL") is None  # revoked


def test_registry_load_skips_revoked():
    path = _make_state([{
        "symbol": "TSLA",
        "policy_type": "DO_NOT_SELL",
        "status": "REVOKED",
        "rationale": "",
        "created_at": _now(),
        "expires_at": None,
        "revoked_at": _now(),
    }])
    reg = OperatorPolicyRegistry.load(path)
    assert reg.is_do_not_sell("TSLA") is False
    assert reg.active_policy_type("TSLA") is None


def test_registry_load_skips_expired():
    path = _make_state([{
        "symbol": "TSLA",
        "policy_type": "CORE_ANCHOR",
        "status": "ACTIVE",
        "rationale": "",
        "created_at": _now(),
        "expires_at": _past(1),
        "revoked_at": None,
    }])
    reg = OperatorPolicyRegistry.load(path)
    assert reg.is_core_anchor("TSLA") is False


# ─── OperatorPolicyRegistry predicates ──────────────────────────────────────

def test_predicates_all():
    path = _make_state([
        {"symbol": "A", "policy_type": "DO_NOT_SELL", "status": "ACTIVE",
         "rationale": "", "created_at": _now(), "expires_at": None, "revoked_at": None},
        {"symbol": "B", "policy_type": "SELL_LAST", "status": "ACTIVE",
         "rationale": "", "created_at": _now(), "expires_at": None, "revoked_at": None},
        {"symbol": "C", "policy_type": "CORE_ANCHOR", "status": "ACTIVE",
         "rationale": "", "created_at": _now(), "expires_at": None, "revoked_at": None},
        {"symbol": "D", "policy_type": "PREFERRED_ACCUMULATION", "status": "ACTIVE",
         "rationale": "", "created_at": _now(), "expires_at": None, "revoked_at": None},
    ])
    reg = OperatorPolicyRegistry.load(path)
    assert reg.is_do_not_sell("A") is True
    assert reg.is_sell_last("B") is True
    assert reg.is_core_anchor("C") is True
    assert reg.is_preferred_accumulation("D") is True
    # cross-predicate — should be False
    assert reg.is_do_not_sell("B") is False
    assert reg.is_sell_last("A") is False


# ─── policy_snapshot ─────────────────────────────────────────────────────────

def test_policy_snapshot_empty():
    reg = OperatorPolicyRegistry.load("/tmp/__nonexistent_sih_test__.json")
    snap = reg.policy_snapshot()
    assert snap == {}


def test_policy_snapshot_content():
    path = _make_state([
        {"symbol": "TSLA", "policy_type": "DO_NOT_SELL", "status": "ACTIVE",
         "rationale": "", "created_at": _now(), "expires_at": None, "revoked_at": None},
        {"symbol": "DODFX", "policy_type": "SELL_LAST", "status": "ACTIVE",
         "rationale": "", "created_at": _now(), "expires_at": None, "revoked_at": None},
    ])
    reg = OperatorPolicyRegistry.load(path)
    snap = reg.policy_snapshot()
    # policy_snapshot returns {symbol: {policy_type, status, created_at}}
    assert set(snap.keys()) == {"TSLA", "DODFX"}
    assert snap["TSLA"]["policy_type"] == "DO_NOT_SELL"
    assert snap["DODFX"]["policy_type"] == "SELL_LAST"


# ─── conflict / warning checks ───────────────────────────────────────────────

def test_no_conflict_same_type():
    conflict, msg = check_policy_conflict("DO_NOT_SELL", "DO_NOT_SELL")
    assert conflict is False
    assert msg is None


def test_conflict_do_not_sell_sell_last():
    conflict, msg = check_policy_conflict("DO_NOT_SELL", "SELL_LAST")
    assert conflict is True
    assert msg is not None
    assert "DO_NOT_SELL" in msg or "SELL_LAST" in msg


def test_conflict_sell_last_do_not_sell():
    conflict, msg = check_policy_conflict("SELL_LAST", "DO_NOT_SELL")
    assert conflict is True


def test_no_conflict_core_anchor_preferred():
    conflict, msg = check_policy_conflict("CORE_ANCHOR", "PREFERRED_ACCUMULATION")
    assert conflict is False


def test_warning_sell_last_preferred_accumulation():
    warn = check_policy_warning("SELL_LAST", "PREFERRED_ACCUMULATION")
    assert warn is not None


def test_no_warning_core_anchor_do_not_sell():
    warn = check_policy_warning("CORE_ANCHOR", "DO_NOT_SELL")
    assert warn is None
