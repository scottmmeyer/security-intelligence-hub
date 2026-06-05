"""Phase 23.2 — Unit tests for operator_policy API helper functions.

Covers:
  - build_policy_annotations(): empty registry, annotations present, non-policy symbol
  - build_policy_suppressed_entries(): TRIM + DO_NOT_SELL, no policy, no sell context
  - check_policy_conflict(): all POLICY_CONFLICTS pairs
  - check_policy_warning(): POLICY_WARNINGS pairs
"""
import json
import tempfile
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from src.portfolio.operator_policy import (
    OperatorPolicyRegistry,
    POLICY_TYPES,
    POLICY_CONFLICTS,
    POLICY_WARNINGS,
    check_policy_conflict,
    check_policy_warning,
    build_policy_annotations,
    build_policy_suppressed_entries,
)


# ─── helpers ──────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_registry(policies: list[dict]) -> OperatorPolicyRegistry:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump({"operator_policies": policies}, f)
    f.close()
    return OperatorPolicyRegistry.load(f.name)


def _make_overlay(symbol: str, opportunity_flag: str = "", composite_score: float = 3.0):
    """Minimal overlay-like object using SimpleNamespace."""
    return SimpleNamespace(
        symbol=symbol,
        opportunity_flag=opportunity_flag,
        composite_score=composite_score,
    )


# ─── build_policy_annotations ────────────────────────────────────────────────

def test_build_policy_annotations_empty_registry():
    registry = OperatorPolicyRegistry.load("/tmp/__nonexistent_sih_test__.json")
    result = build_policy_annotations(["TSLA", "AAPL"], registry)
    for sym in ["TSLA", "AAPL"]:
        assert result[sym]["policy_type"] == ""
        assert result[sym]["policy_annotation"] == ""
        assert result[sym]["policy_protected"] is False


def test_build_policy_annotations_do_not_sell():
    registry = _make_registry([{
        "symbol": "TSLA", "policy_type": "DO_NOT_SELL", "status": "ACTIVE",
        "rationale": "", "created_at": _now(), "expires_at": None, "revoked_at": None,
    }])
    result = build_policy_annotations(["TSLA", "AAPL"], registry)
    assert result["TSLA"]["policy_type"] == "DO_NOT_SELL"
    assert result["TSLA"]["policy_protected"] is True
    assert result["TSLA"]["policy_annotation"] != ""
    # AAPL has no policy
    assert result["AAPL"]["policy_type"] == ""
    assert result["AAPL"]["policy_protected"] is False


def test_build_policy_annotations_all_types():
    registry = _make_registry([
        {"symbol": "A", "policy_type": "DO_NOT_SELL", "status": "ACTIVE",
         "rationale": "", "created_at": _now(), "expires_at": None, "revoked_at": None},
        {"symbol": "B", "policy_type": "SELL_LAST", "status": "ACTIVE",
         "rationale": "", "created_at": _now(), "expires_at": None, "revoked_at": None},
        {"symbol": "C", "policy_type": "CORE_ANCHOR", "status": "ACTIVE",
         "rationale": "", "created_at": _now(), "expires_at": None, "revoked_at": None},
        {"symbol": "D", "policy_type": "PREFERRED_ACCUMULATION", "status": "ACTIVE",
         "rationale": "", "created_at": _now(), "expires_at": None, "revoked_at": None},
    ])
    result = build_policy_annotations(["A", "B", "C", "D"], registry)
    assert result["A"]["policy_type"] == "DO_NOT_SELL"
    assert result["B"]["policy_type"] == "SELL_LAST"
    assert result["C"]["policy_type"] == "CORE_ANCHOR"
    assert result["D"]["policy_type"] == "PREFERRED_ACCUMULATION"


def test_build_policy_annotations_case_insensitive():
    """Symbols passed in lowercase are uppercased in the returned dict."""
    registry = _make_registry([{
        "symbol": "TSLA", "policy_type": "DO_NOT_SELL", "status": "ACTIVE",
        "rationale": "", "created_at": _now(), "expires_at": None, "revoked_at": None,
    }])
    result = build_policy_annotations(["tsla", "TSLA"], registry)
    # Keys are uppercased
    assert result["TSLA"]["policy_type"] == "DO_NOT_SELL"


# ─── build_policy_suppressed_entries ─────────────────────────────────────────

def test_suppressed_entries_do_not_sell_trim():
    registry = _make_registry([{
        "symbol": "TSLA", "policy_type": "DO_NOT_SELL", "status": "ACTIVE",
        "rationale": "", "created_at": _now(), "expires_at": None, "revoked_at": None,
    }])
    overlays = [
        _make_overlay("TSLA", opportunity_flag="TRIM"),
        _make_overlay("AAPL", opportunity_flag="TRIM"),
    ]
    result = build_policy_suppressed_entries(overlays, registry)
    assert len(result) == 1
    assert result[0]["symbol"] == "TSLA"
    assert result[0]["policy_type"] == "DO_NOT_SELL"
    assert result[0]["intelligence_flag"] == "TRIM"


def test_suppressed_entries_do_not_sell_reduce_candidate():
    registry = _make_registry([{
        "symbol": "TSLA", "policy_type": "DO_NOT_SELL", "status": "ACTIVE",
        "rationale": "", "created_at": _now(), "expires_at": None, "revoked_at": None,
    }])
    overlays = [_make_overlay("TSLA", opportunity_flag="REDUCE_CANDIDATE")]
    result = build_policy_suppressed_entries(overlays, registry)
    assert len(result) == 1
    assert result[0]["intelligence_flag"] == "REDUCE_CANDIDATE"


def test_suppressed_entries_no_policy():
    registry = OperatorPolicyRegistry.load("/tmp/__nonexistent_sih_test__.json")
    overlays = [_make_overlay("TSLA", opportunity_flag="TRIM")]
    result = build_policy_suppressed_entries(overlays, registry)
    assert result == []


def test_suppressed_entries_no_sell_context():
    """DO_NOT_SELL but no TRIM/REDUCE_CANDIDATE flag → not suppressed."""
    registry = _make_registry([{
        "symbol": "TSLA", "policy_type": "DO_NOT_SELL", "status": "ACTIVE",
        "rationale": "", "created_at": _now(), "expires_at": None, "revoked_at": None,
    }])
    overlays = [_make_overlay("TSLA", opportunity_flag="ACCUMULATE")]
    result = build_policy_suppressed_entries(overlays, registry)
    assert result == []


def test_suppressed_entries_sell_last_not_suppressed():
    """SELL_LAST + TRIM should NOT appear in suppressed (only DO_NOT_SELL does)."""
    registry = _make_registry([{
        "symbol": "DODFX", "policy_type": "SELL_LAST", "status": "ACTIVE",
        "rationale": "", "created_at": _now(), "expires_at": None, "revoked_at": None,
    }])
    overlays = [_make_overlay("DODFX", opportunity_flag="TRIM")]
    result = build_policy_suppressed_entries(overlays, registry)
    assert result == []


# ─── check_policy_conflict ────────────────────────────────────────────────────

def test_check_policy_conflict_all_same_type():
    for pt in POLICY_TYPES:
        conflict, msg = check_policy_conflict(pt, pt)
        assert conflict is False


def test_check_policy_conflict_known_conflicts():
    for pair in POLICY_CONFLICTS:
        types = list(pair)
        assert len(types) == 2
        conflict, msg = check_policy_conflict(types[0], types[1])
        assert conflict is True, f"Expected conflict for {types[0]} vs {types[1]}"
        assert msg is not None


def test_check_policy_conflict_none_existing():
    conflict, msg = check_policy_conflict(None, "DO_NOT_SELL")
    assert conflict is False


def test_check_policy_conflict_none_new():
    conflict, msg = check_policy_conflict("DO_NOT_SELL", None)
    assert conflict is False


# ─── check_policy_warning ─────────────────────────────────────────────────────

def test_check_policy_warning_known_warnings():
    for pair in POLICY_WARNINGS:
        types = list(pair)
        assert len(types) == 2
        warn = check_policy_warning(types[0], types[1])
        assert warn is not None, f"Expected warning for {types[0]} vs {types[1]}"


def test_check_policy_warning_no_warning_safe_pairs():
    safe_pairs = [
        ("DO_NOT_SELL", "CORE_ANCHOR"),
        ("CORE_ANCHOR", "DO_NOT_SELL"),
        ("DO_NOT_SELL", "PREFERRED_ACCUMULATION"),
    ]
    for a, b in safe_pairs:
        warn = check_policy_warning(a, b)
        assert warn is None, f"Unexpected warning for {a} vs {b}"


def test_check_policy_warning_none_inputs():
    assert check_policy_warning(None, "DO_NOT_SELL") is None
    assert check_policy_warning("DO_NOT_SELL", None) is None
