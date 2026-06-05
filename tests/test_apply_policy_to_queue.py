"""Phase 23.2 — Unit tests for apply_policy_to_queue.

Covers:
  - Empty registry: no-op, ranks preserved
  - PREFERRED_ACCUMULATION: boosted to front of buy cohort
  - CORE_ANCHOR: annotation only, no rank change
  - DO_NOT_SELL: annotation only for buy queue (no sell context)
  - SELL_LAST: annotation only for buy queue (no sell context)
  - Multiple policies: combined behavior
  - original_rank preserved correctly
"""
import json
import tempfile
from datetime import datetime, timezone

import pytest

from src.portfolio.deployment_queue import (
    DeploymentCandidate,
    CwDasBreakdown,
    apply_policy_to_queue,
)
from src.portfolio.operator_policy import OperatorPolicyRegistry


# ─── helpers ──────────────────────────────────────────────────────────────────

def _make_breakdown() -> CwDasBreakdown:
    return CwDasBreakdown(
        signal=20.0,
        replay=20.0,
        conviction=35.0,
        sizing=5.0,
        momentum=7.5,
        redundancy_pen=0.0,
        conc_pen=0.0,
    )


def _make_candidate(rank: int, symbol: str, trim_score: float = 10.0) -> DeploymentCandidate:
    return DeploymentCandidate(
        rank=rank,
        symbol=symbol,
        current_weight_pct=5.0,
        market_value=10000.0,
        composite_score=3.5,
        narrative_tier="CORE_CONVICTION_LEADER",
        replay_supported=True,
        trim_score=trim_score,
        headroom_pct=20.0,
        deployment_score=70.0,
        score_breakdown=_make_breakdown(),
        notes="",
    )


def _make_registry(policies: list[dict]) -> OperatorPolicyRegistry:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump({"operator_policies": policies}, f)
    f.close()
    return OperatorPolicyRegistry.load(f.name)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── empty registry ───────────────────────────────────────────────────────────

def test_empty_registry_no_op():
    queue = [_make_candidate(1, "AAPL"), _make_candidate(2, "TSLA"), _make_candidate(3, "NVDA")]
    registry = OperatorPolicyRegistry.load("/tmp/__nonexistent_sih_test__.json")
    result, suppressed = apply_policy_to_queue(queue, registry)
    assert [c.symbol for c in result] == ["AAPL", "TSLA", "NVDA"]
    assert [c.rank for c in result] == [1, 2, 3]
    assert suppressed == []


def test_empty_registry_policy_fields_none():
    queue = [_make_candidate(1, "AAPL")]
    registry = OperatorPolicyRegistry.load("/tmp/__nonexistent_sih_test__.json")
    result, _ = apply_policy_to_queue(queue, registry)
    c = result[0]
    assert c.policy_type is None
    assert c.policy_annotation is None
    assert c.policy_protected is False
    assert c.policy_rank_boost is False
    assert c.original_rank == 1


# ─── PREFERRED_ACCUMULATION boost ────────────────────────────────────────────

def test_preferred_accumulation_boosted_to_front():
    queue = [_make_candidate(1, "AAPL"), _make_candidate(2, "TSLA"), _make_candidate(3, "NVDA")]
    registry = _make_registry([{
        "symbol": "NVDA", "policy_type": "PREFERRED_ACCUMULATION", "status": "ACTIVE",
        "rationale": "", "created_at": _now(), "expires_at": None, "revoked_at": None,
    }])
    result, suppressed = apply_policy_to_queue(queue, registry)
    assert result[0].symbol == "NVDA"
    assert result[0].rank == 1
    assert result[0].original_rank == 3
    assert result[0].policy_rank_boost is True
    assert result[0].policy_annotation is not None
    assert suppressed == []


def test_preferred_accumulation_does_not_change_scores():
    queue = [_make_candidate(1, "AAPL"), _make_candidate(2, "NVDA")]
    registry = _make_registry([{
        "symbol": "NVDA", "policy_type": "PREFERRED_ACCUMULATION", "status": "ACTIVE",
        "rationale": "", "created_at": _now(), "expires_at": None, "revoked_at": None,
    }])
    result, _ = apply_policy_to_queue(queue, registry)
    nvda = next(c for c in result if c.symbol == "NVDA")
    assert nvda.deployment_score == 70.0  # score unchanged
    assert nvda.composite_score == 3.5    # score unchanged


# ─── CORE_ANCHOR: annotation only ────────────────────────────────────────────

def test_core_anchor_annotation_only():
    queue = [_make_candidate(1, "AAPL"), _make_candidate(2, "TSLA")]
    registry = _make_registry([{
        "symbol": "TSLA", "policy_type": "CORE_ANCHOR", "status": "ACTIVE",
        "rationale": "", "created_at": _now(), "expires_at": None, "revoked_at": None,
    }])
    result, suppressed = apply_policy_to_queue(queue, registry)
    # Rank order preserved (no boost)
    assert [c.symbol for c in result] == ["AAPL", "TSLA"]
    tsla = next(c for c in result if c.symbol == "TSLA")
    assert tsla.policy_type == "CORE_ANCHOR"
    assert tsla.policy_annotation is not None
    assert tsla.policy_rank_boost is False
    assert suppressed == []


# ─── DO_NOT_SELL: annotation only (buy queue, no sell context) ────────────────

def test_do_not_sell_annotation_only_in_buy_context():
    queue = [_make_candidate(1, "AAPL"), _make_candidate(2, "TSLA")]
    registry = _make_registry([{
        "symbol": "TSLA", "policy_type": "DO_NOT_SELL", "status": "ACTIVE",
        "rationale": "Concentrated position", "created_at": _now(), "expires_at": None, "revoked_at": None,
    }])
    result, suppressed = apply_policy_to_queue(queue, registry)
    tsla = next(c for c in result if c.symbol == "TSLA")
    assert tsla.policy_type == "DO_NOT_SELL"
    assert tsla.policy_protected is True
    assert tsla.policy_annotation is not None
    # Not suppressed — buy queue (trim_score=10 < 60)
    assert len(suppressed) == 0


def test_do_not_sell_in_sell_context_suppressed():
    """DO_NOT_SELL with high trim_score (>=60) → removed from active queue."""
    queue = [
        _make_candidate(1, "AAPL"),
        _make_candidate(2, "TSLA", trim_score=75.0),  # high trim = sell context
    ]
    registry = _make_registry([{
        "symbol": "TSLA", "policy_type": "DO_NOT_SELL", "status": "ACTIVE",
        "rationale": "", "created_at": _now(), "expires_at": None, "revoked_at": None,
    }])
    result, suppressed = apply_policy_to_queue(queue, registry)
    active_symbols = [c.symbol for c in result]
    assert "TSLA" not in active_symbols
    assert len(suppressed) == 1
    assert suppressed[0].symbol == "TSLA"


# ─── SELL_LAST: annotation only for buy queue ────────────────────────────────

def test_sell_last_annotation_only():
    queue = [_make_candidate(1, "AAPL"), _make_candidate(2, "DODFX")]
    registry = _make_registry([{
        "symbol": "DODFX", "policy_type": "SELL_LAST", "status": "ACTIVE",
        "rationale": "", "created_at": _now(), "expires_at": None, "revoked_at": None,
    }])
    result, suppressed = apply_policy_to_queue(queue, registry)
    dodfx = next(c for c in result if c.symbol == "DODFX")
    assert dodfx.policy_type == "SELL_LAST"
    assert dodfx.policy_annotation is not None
    assert suppressed == []


# ─── original_rank preserved ─────────────────────────────────────────────────

def test_original_rank_preserved():
    queue = [_make_candidate(1, "A"), _make_candidate(2, "B"), _make_candidate(3, "C")]
    registry = OperatorPolicyRegistry.load("/tmp/__nonexistent_sih_test__.json")
    result, _ = apply_policy_to_queue(queue, registry)
    for c in result:
        assert c.original_rank == c.rank  # no reordering


def test_original_rank_preserved_after_boost():
    queue = [_make_candidate(1, "A"), _make_candidate(2, "B"), _make_candidate(3, "C")]
    registry = _make_registry([{
        "symbol": "C", "policy_type": "PREFERRED_ACCUMULATION", "status": "ACTIVE",
        "rationale": "", "created_at": _now(), "expires_at": None, "revoked_at": None,
    }])
    result, _ = apply_policy_to_queue(queue, registry)
    c_entry = next(c for c in result if c.symbol == "C")
    assert c_entry.original_rank == 3  # was rank 3 before boost
    assert c_entry.rank == 1  # now rank 1 after boost
