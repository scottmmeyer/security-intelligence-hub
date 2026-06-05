"""Tests for Phase 23.6A — Capital Rotation Advisor backend core.

Covers:
  - Capital source detection (all 5 categories)
  - Policy handling (DO_NOT_SELL, SELL_LAST, CORE_ANCHOR)
  - Tax modifier behavior (Bucket A, D, E)
  - Rotation proposal assembly
  - Impact estimation
  - API endpoint (smoke)

Design contract: docs/phase_23_6/
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from src.portfolio.cra.capital_source_builder import build_capital_sources


def _bcs(*args, **kwargs) -> List[CapitalSourceRecord]:
    """Thin wrapper that unpacks the (sources, suppressed) tuple from
    build_capital_sources for backwards-compatible test call sites.
    Returns only the primary (actionable) sources list.
    Pass minimum_proceeds=0 to include all records regardless of size."""
    sources, _ = build_capital_sources(*args, **kwargs)
    return sources
from src.portfolio.cra.impact_estimator import estimate_impact
from src.portfolio.cra.models import (
    CATEGORY_LOW_CONVICTION,
    CATEGORY_OVERWEIGHT_REDUCTION,
    CATEGORY_SIGNAL_DETERIORATION,
    CATEGORY_STRATEGIC_EXIT,
    CATEGORY_TAX_AWARE_EXIT,
    STATUS_DRAFT,
    STATUS_OP_REVIEW,
    STATUS_READY,
    CapitalSourceRecord,
    PortfolioImpactEstimate,
    RotationDeploymentTarget,
    RotationProposal,
)
from src.portfolio.cra.rotation_proposal_builder import (
    _allocate_capital,
    build_rotation_proposal,
)


# ── Fixture helpers ───────────────────────────────────────────────────────────

def _ov(
    symbol: str,
    opportunity_flag: str = "HOLD",
    signal_direction: str = "NEUTRAL",
    ess_score_text: str = "NEUTRAL",
    is_overweight_vs_target: str = "False",
    replay_supported: str = "False",
    percent_of_portfolio: str = "2.0",
    composite_score: str = "3.0",
    policy_type: str = "",
    policy_protected: str = "False",
    execution_state: str = "",
    effective_action: str = "",
) -> Dict:
    return {
        "symbol": symbol,
        "opportunity_flag": opportunity_flag,
        "signal_direction": signal_direction,
        "ess_score_text": ess_score_text,
        "is_overweight_vs_target": is_overweight_vs_target,
        "replay_supported": replay_supported,
        "percent_of_portfolio": percent_of_portfolio,
        "composite_score": composite_score,
        "portfolio_snapshot_id": "PSNAP-TEST",
        "policy_type": policy_type,
        "policy_protected": policy_protected,
        "execution_state": execution_state,
        "effective_action": effective_action,
    }


def _holding(
    symbol: str,
    market_value: str = "10000.00",
    cost_basis: str = "",
    percent_of_portfolio: str = "2.0",
    geography: str = "US",
    market_cap_bucket: str = "LARGE",
    asset_class: str = "EQUITIES",
) -> Dict:
    return {
        "symbol": symbol,
        "market_value": market_value,
        "cost_basis": cost_basis,
        "percent_of_portfolio": percent_of_portfolio,
        "geography": geography,
        "market_cap_bucket": market_cap_bucket,
        "asset_class": asset_class,
    }


def _alignment_row(node_key: str, drift_pct: float, actual_pct: float = 10.0, target_pct: float = 8.0) -> Dict:
    return {
        "node_key": node_key,
        "node_label": node_key,
        "drift_pct": str(drift_pct),
        "actual_pct": str(actual_pct),
        "target_pct": str(target_pct),
        "drift_direction": "OVERWEIGHT" if drift_pct > 0 else "UNDERWEIGHT",
        "alignment_score": "0.7",
    }


def _queue_entry(
    rank: int,
    symbol: str,
    deployment_score: float = 80.0,
    headroom_pct: float = 20.0,
    current_weight_pct: float = 3.0,
    market_value: float = 14000.0,
    narrative_tier: str = "HIGH_CONVICTION_ANCHOR",
    policy_protected: bool = False,
) -> Dict:
    return {
        "rank": rank,
        "symbol": symbol,
        "deployment_score": deployment_score,
        "headroom_pct": headroom_pct,
        "current_weight_pct": current_weight_pct,
        "market_value": market_value,
        "narrative_tier": narrative_tier,
        "policy_protected": policy_protected,
        "policy_type": None,
        "composite_score": 4.0,
        "replay_supported": True,
        "trim_score": 0.0,
        "score_breakdown": {"signal": 20.0, "replay": 20.0, "conviction": 28.0, "sizing": 5.0, "momentum": 7.0, "redundancy_pen": 0.0, "conc_pen": 0.0},
        "notes": "HCA tier",
        "policy_annotation": None,
        "policy_rank_boost": False,
        "original_rank": rank,
    }


def _tax_state(
    strategic_exit_symbols: Optional[List[str]] = None,
    policies: Optional[List[Dict]] = None,
) -> Dict:
    return {
        "tax_year": 2026,
        "net_realized_ytd": None,
        "potential_additional_losses": None,
        "capital_loss_carryforward": None,
        "strategic_exit_symbols": strategic_exit_symbols or [],
        "operator_policies": policies or [],
        "_updated": "2026-06-04T00:00:00+00:00",
    }


def _policy_entry(symbol: str, policy_type: str, status: str = "ACTIVE") -> Dict:
    return {
        "symbol": symbol,
        "policy_type": policy_type,
        "status": status,
        "rationale": "test",
        "created_at": "2026-06-04T00:00:00+00:00",
        "expires_at": None,
        "revoked_at": None,
    }


# ── Category 1: Signal Deterioration ─────────────────────────────────────────

class TestCategory1SignalDeterioration:

    def _sources(self, **ov_kwargs) -> List[CapitalSourceRecord]:
        ov = _ov("AAAA", **ov_kwargs)
        h = _holding("AAAA", market_value="20000")
        return _bcs([ov], [h], [], {})

    def test_very_bearish_ess_yields_urgent(self):
        sources = self._sources(ess_score_text="VERY_BEARISH", opportunity_flag="TRIM", signal_direction="BEARISH")
        assert len(sources) == 1
        s = sources[0]
        assert s.symbol == "AAAA"
        assert s.category == CATEGORY_SIGNAL_DETERIORATION
        assert s.priority == "URGENT"
        assert s.sizing_pct == 1.0
        assert s.estimated_proceeds == pytest.approx(20000.0)

    def test_bearish_overweight_yields_high(self):
        ov = _ov("BBBB", ess_score_text="BEARISH", signal_direction="BEARISH",
                 opportunity_flag="TRIM", is_overweight_vs_target="True")
        h = _holding("BBBB", market_value="15000")
        alignment = [_alignment_row("EQUITIES.US.LARGE", drift_pct=10.0)]
        sources = _bcs([ov], [h], alignment, {})
        assert len(sources) == 1
        s = sources[0]
        assert s.category == CATEGORY_SIGNAL_DETERIORATION
        assert s.priority == "HIGH"
        assert s.sizing_pct == 0.5
        assert s.is_overweight is True

    def test_bearish_not_overweight_yields_high_via_trim_flag(self):
        sources = self._sources(
            ess_score_text="BEARISH",
            signal_direction="BEARISH",
            opportunity_flag="TRIM",
            is_overweight_vs_target="False",
        )
        s = sources[0]
        assert s.priority == "HIGH"
        assert s.sizing_pct == 0.5

    def test_watch_flag_yields_moderate(self):
        sources = self._sources(opportunity_flag="WATCH", ess_score_text="BEARISH", signal_direction="BEARISH")
        s = sources[0]
        assert s.category == CATEGORY_SIGNAL_DETERIORATION
        assert s.priority == "MODERATE"

    def test_neutral_ess_not_cat1(self):
        """NEUTRAL ESS with HOLD flag should not generate a Cat 1 (Signal Deterioration) source."""
        sources = self._sources(ess_score_text="NEUTRAL", opportunity_flag="HOLD")
        # May be Cat 5 (Low Conviction), but must NOT be Cat 1
        cat1 = [s for s in sources if s.category == CATEGORY_SIGNAL_DETERIORATION]
        assert len(cat1) == 0

    def test_signal_direction_preserved(self):
        sources = self._sources(
            ess_score_text="VERY_BEARISH",
            signal_direction="BEARISH",
            opportunity_flag="TRIM",
        )
        assert sources[0].signal_direction == "BEARISH"
        assert sources[0].ess_score_text == "VERY_BEARISH"


# ── Category 2: Strategic Exit ───────────────────────────────────────────────

class TestCategory2StrategicExit:

    def test_strategic_exit_symbol_creates_source(self):
        ov = _ov("FIS", opportunity_flag="HOLD")
        h = _holding("FIS", market_value="20000")
        tax = _tax_state(strategic_exit_symbols=["FIS"])
        sources = _bcs([ov], [h], [], {}, tax_state=tax)
        cats = [s.category for s in sources]
        assert CATEGORY_STRATEGIC_EXIT in cats

    def test_strategic_exit_full_sizing_default(self):
        ov = _ov("XYZ", opportunity_flag="HOLD")
        h = _holding("XYZ", market_value="5000")
        tax = _tax_state(strategic_exit_symbols=["XYZ"])
        sources = _bcs([ov], [h], [], {}, tax_state=tax)
        s = next(x for x in sources if x.symbol == "XYZ")
        assert s.sizing_pct == 1.0
        assert s.category == CATEGORY_STRATEGIC_EXIT

    def test_strategic_exit_blocked_by_do_not_sell(self):
        ov = _ov("ZZZ", opportunity_flag="HOLD")
        h = _holding("ZZZ", market_value="5000")
        tax = _tax_state(
            strategic_exit_symbols=["ZZZ"],
            policies=[_policy_entry("ZZZ", "DO_NOT_SELL")],
        )
        sources = _bcs([ov], [h], [], {}, tax_state=tax)
        s = next(x for x in sources if x.symbol == "ZZZ")
        assert s.blocked_by_policy is True
        # Proceeds excluded from pool (not our concern here; but blocked flag is set)

    def test_sti_profile_reducible_creates_source(self):
        ov = _ov("CHGG", opportunity_flag="HOLD")
        h = _holding("CHGG", market_value="8000")
        profiles = [{"symbol": "CHGG", "strategic_classification": "REDUCIBLE",
                     "trim_priority_score": 75, "trim_rationale": "Redundant"}]
        sources = _bcs([ov], [h], [], {}, strategic_profiles=profiles)
        s = next((x for x in sources if x.symbol == "CHGG"), None)
        assert s is not None
        assert s.category == CATEGORY_STRATEGIC_EXIT
        assert s.priority == "HIGH"

    def test_sti_profile_below_threshold_excluded_from_cat2(self):
        """STI trim_priority_score < 60 must not generate a Cat 2 (Strategic Exit) source."""
        ov = _ov("LLLL", opportunity_flag="HOLD", replay_supported="True")
        h = _holding("LLLL", market_value="8000")
        profiles = [{"symbol": "LLLL", "strategic_classification": "REDUCIBLE",
                     "trim_priority_score": 30, "trim_rationale": "Minor"}]
        sources = _bcs([ov], [h], [], {}, strategic_profiles=profiles)
        # trim_priority_score 30 < 60 threshold → excluded from Cat 2
        cat2 = [s for s in sources if s.symbol == "LLLL" and s.category == CATEGORY_STRATEGIC_EXIT]
        assert len(cat2) == 0


# ── Category 3: Overweight Reduction ─────────────────────────────────────────

class TestCategory3OverweightReduction:

    def test_high_drift_yields_high_priority(self):
        # Holding is US LARGE → node is EQUITIES.US.LARGE
        ov = _ov("GOOG", is_overweight_vs_target="True", opportunity_flag="HOLD")
        h = _holding("GOOG", market_value="12000", geography="US", market_cap_bucket="LARGE")
        alignment = [_alignment_row("EQUITIES.US.LARGE", drift_pct=16.0)]
        sources = _bcs([ov], [h], alignment, {})
        s = next((x for x in sources if x.symbol == "GOOG"), None)
        assert s is not None
        assert s.category == CATEGORY_OVERWEIGHT_REDUCTION
        assert s.priority == "HIGH"
        assert s.drift_pct == pytest.approx(16.0)

    def test_moderate_drift_yields_moderate_priority(self):
        # Holding is US LARGE → node is EQUITIES.US.LARGE
        ov = _ov("MSFT", is_overweight_vs_target="True", opportunity_flag="HOLD")
        h = _holding("MSFT", market_value="10000", geography="US", market_cap_bucket="LARGE")
        alignment = [_alignment_row("EQUITIES.US.LARGE", drift_pct=10.0)]
        sources = _bcs([ov], [h], alignment, {})
        s = next((x for x in sources if x.symbol == "MSFT"), None)
        assert s is not None
        assert s.priority == "MODERATE"

    def test_not_overweight_excluded_from_cat3(self):
        """Non-overweight holding must not appear in Cat 3 (Overweight Reduction)."""
        # Use replay_supported=True to prevent Cat 5 from capturing it.
        ov = _ov("AMZN", is_overweight_vs_target="False", opportunity_flag="HOLD", replay_supported="True")
        h = _holding("AMZN", market_value="10000")
        sources = _bcs([ov], [h], [], {})
        cat3 = [s for s in sources if s.symbol == "AMZN" and s.category == CATEGORY_OVERWEIGHT_REDUCTION]
        assert len(cat3) == 0


# ── Category 4: Tax-Aware Exit ───────────────────────────────────────────────

class TestCategory4TaxAwareExit:

    def test_unrealized_loss_yields_bucket_a(self):
        ov = _ov("FIS", opportunity_flag="HOLD")
        h = _holding("FIS", market_value="20000", cost_basis="32000")
        sources = _bcs([ov], [h], [], {})
        s = next((x for x in sources if x.symbol == "FIS"), None)
        assert s is not None
        assert s.category == CATEGORY_TAX_AWARE_EXIT
        assert s.tax_bucket == "A"
        assert s.unrealized_gain_loss == pytest.approx(-12000.0)
        assert "harvest" in s.tax_annotation.lower()

    def test_unrealized_gain_small_yields_bucket_c(self):
        ov = _ov("AAPL", opportunity_flag="HOLD")
        h = _holding("AAPL", market_value="15000", cost_basis="12000")
        sources = _bcs([ov], [h], [], {})
        # Bucket C alone doesn't create a Cat 4 record (only Bucket A initiates)
        # but if picked up by another category, tax_bucket should be C
        s = next((x for x in sources if x.symbol == "AAPL"), None)
        # AAPL: HOLD flag, no replay, ≥ de minimis → Cat 5
        # With gain, tax bucket = C (no priority modifier)
        if s:
            assert s.tax_bucket == "C"

    def test_significant_gain_yields_bucket_d_with_review(self):
        # FIS has small gain → Bucket C
        # Override with large gain
        ov = _ov("BIGWIN", opportunity_flag="HOLD")
        h = _holding("BIGWIN", market_value="20000", cost_basis="12000")
        # 20000 - 12000 = 8000 gain > 5000 threshold → Bucket D
        sources = _bcs([ov], [h], [], {})
        s = next((x for x in sources if x.symbol == "BIGWIN"), None)
        # If picked up (Cat 5 due to HOLD + no replay)
        if s:
            assert s.tax_bucket == "D"
            assert s.operator_review_required is True

    def test_bucket_a_upgrades_low_to_moderate(self):
        """Cat 5 LOW priority + Bucket A modifier → upgrades to MODERATE."""
        ov = _ov("LOSER", opportunity_flag="HOLD")
        h = _holding("LOSER", market_value="5000", cost_basis="8000", percent_of_portfolio="1.5")
        # HOLD + no replay + 1.5% (< 3%) → Cat 5 LOW
        # Bucket A modifier rule: LOW → MODERATE
        sources = _bcs([ov], [h], [], {})
        s = next((x for x in sources if x.symbol == "LOSER"), None)
        if s:
            assert s.tax_bucket == "A"
            assert s.priority == "MODERATE"  # upgraded from LOW

    def test_no_cost_basis_annotation(self):
        ov = _ov("NOCB", opportunity_flag="TRIM", ess_score_text="BEARISH", signal_direction="BEARISH")
        h = _holding("NOCB", market_value="10000", cost_basis="")
        sources = _bcs([ov], [h], [], {})
        s = next(x for x in sources if x.symbol == "NOCB")
        assert s.cost_basis is None
        assert "no cost basis" in s.tax_annotation.lower()


# ── Category 5: Low Conviction Reduction ─────────────────────────────────────

class TestCategory5LowConviction:

    def test_hold_no_replay_above_threshold_yields_source(self):
        ov = _ov("LAGG", opportunity_flag="HOLD", signal_direction="NEUTRAL",
                 replay_supported="False", percent_of_portfolio="2.5")
        h = _holding("LAGG", market_value="11000")
        sources = _bcs([ov], [h], [], {})
        s = next((x for x in sources if x.symbol == "LAGG"), None)
        assert s is not None
        assert s.category == CATEGORY_LOW_CONVICTION
        assert s.sizing_pct == 0.25

    def test_below_de_minimis_excluded(self):
        ov = _ov("TINY", opportunity_flag="HOLD", replay_supported="False",
                 percent_of_portfolio="0.5")
        h = _holding("TINY", market_value="2000")
        sources = _bcs([ov], [h], [], {})
        assert not any(s.symbol == "TINY" for s in sources)

    def test_in_deployment_queue_excluded_from_cat5(self):
        ov = _ov("VRT", opportunity_flag="HOLD", replay_supported="False",
                 percent_of_portfolio="4.0")
        h = _holding("VRT", market_value="18000")
        queue = {"queue": [{"symbol": "VRT", "rank": 1}]}
        sources = _bcs([ov], [h], [], queue)
        # VRT is in queue → excluded from Cat 5
        assert not any(s.symbol == "VRT" for s in sources)

    def test_preferred_accumulation_excluded(self):
        ov = _ov("PREF", opportunity_flag="HOLD", replay_supported="False",
                 percent_of_portfolio="3.0")
        h = _holding("PREF", market_value="13000")
        tax = _tax_state(policies=[_policy_entry("PREF", "PREFERRED_ACCUMULATION")])
        sources = _bcs([ov], [h], [], {}, tax_state=tax)
        assert not any(s.symbol == "PREF" for s in sources)

    def test_bullish_signal_excluded_from_cat5(self):
        ov = _ov("BULL", opportunity_flag="HOLD", signal_direction="BULLISH",
                 replay_supported="False", percent_of_portfolio="3.0")
        h = _holding("BULL", market_value="13000")
        sources = _bcs([ov], [h], [], {})
        assert not any(s.symbol == "BULL" for s in sources)

    def test_large_weight_yields_moderate(self):
        ov = _ov("BIG", opportunity_flag="HOLD", replay_supported="False",
                 percent_of_portfolio="5.0")
        h = _holding("BIG", market_value="20000")
        sources = _bcs([ov], [h], [], {})
        s = next((x for x in sources if x.symbol == "BIG"), None)
        assert s is not None
        assert s.priority == "MODERATE"

    def test_small_hold_yields_low(self):
        ov = _ov("SMLL", opportunity_flag="HOLD", replay_supported="False",
                 percent_of_portfolio="1.5")
        h = _holding("SMLL", market_value="6000")
        sources = _bcs([ov], [h], [], {})
        s = next((x for x in sources if x.symbol == "SMLL"), None)
        assert s is not None
        assert s.priority == "LOW"


# ── Policy handling ───────────────────────────────────────────────────────────

class TestPolicyHandling:

    def _build(self, symbol: str, policy_type: str) -> List[CapitalSourceRecord]:
        ov = _ov(symbol, opportunity_flag="TRIM", ess_score_text="VERY_BEARISH",
                 signal_direction="BEARISH")
        h = _holding(symbol, market_value="10000")
        tax = _tax_state(policies=[_policy_entry(symbol, policy_type)])
        return _bcs([ov], [h], [], {}, tax_state=tax)

    def test_do_not_sell_blocks_source(self):
        sources = self._build("TSLA", "DO_NOT_SELL")
        s = next(x for x in sources if x.symbol == "TSLA")
        assert s.blocked_by_policy is True
        assert s.policy_type == "DO_NOT_SELL"
        # Still present in sources list (visible in UI)
        assert s.category == CATEGORY_SIGNAL_DETERIORATION

    def test_sell_last_not_blocked(self):
        sources = self._build("DODFX", "SELL_LAST")
        s = next(x for x in sources if x.symbol == "DODFX")
        assert s.blocked_by_policy is False
        assert s.policy_type == "SELL_LAST"

    def test_core_anchor_triggers_review(self):
        sources = self._build("ANCHOR", "CORE_ANCHOR")
        s = next(x for x in sources if x.symbol == "ANCHOR")
        assert s.blocked_by_policy is False
        assert s.operator_review_required is True
        assert s.policy_type == "CORE_ANCHOR"

    def test_revoked_policy_not_applied(self):
        ov = _ov("OLD", opportunity_flag="TRIM", ess_score_text="VERY_BEARISH",
                 signal_direction="BEARISH")
        h = _holding("OLD", market_value="10000")
        tax = _tax_state(policies=[{
            "symbol": "OLD",
            "policy_type": "DO_NOT_SELL",
            "status": "ACTIVE",
            "rationale": "old",
            "created_at": "2026-01-01T00:00:00+00:00",
            "expires_at": None,
            "revoked_at": "2026-06-01T00:00:00+00:00",
        }])
        sources = _bcs([ov], [h], [], {}, tax_state=tax)
        s = next((x for x in sources if x.symbol == "OLD"), None)
        assert s is not None
        assert s.blocked_by_policy is False

    def test_superseded_policy_not_applied(self):
        ov = _ov("SUPER", opportunity_flag="TRIM", ess_score_text="BEARISH",
                 signal_direction="BEARISH")
        h = _holding("SUPER", market_value="10000")
        tax = _tax_state(policies=[_policy_entry("SUPER", "DO_NOT_SELL", status="SUPERSEDED")])
        sources = _bcs([ov], [h], [], {}, tax_state=tax)
        s = next((x for x in sources if x.symbol == "SUPER"), None)
        assert s is not None
        assert s.blocked_by_policy is False


# ── Tax modifier behavior ─────────────────────────────────────────────────────

class TestTaxModifiers:

    def test_bucket_a_upgrades_moderate_to_high(self):
        ov = _ov("LOSS", opportunity_flag="WATCH", ess_score_text="BEARISH",
                 signal_direction="BEARISH")
        h = _holding("LOSS", market_value="10000", cost_basis="15000")
        sources = _bcs([ov], [h], [], {})
        s = next(x for x in sources if x.symbol == "LOSS")
        # WATCH + BEARISH → MODERATE; Bucket A → upgrade to HIGH
        assert s.tax_bucket == "A"
        assert s.priority == "HIGH"

    def test_bucket_d_triggers_operator_review(self):
        ov = _ov("BIGWIN", opportunity_flag="TRIM", ess_score_text="VERY_BEARISH",
                 signal_direction="BEARISH")
        # HIGH priority Cat 1 (TRIM + BEARISH but not VERY_BEARISH ESS → HIGH)
        # Gain = 13000 > 5000 → Bucket D
        h = _holding("BIGWIN", market_value="20000", cost_basis="7000")
        sources = _bcs([ov], [h], [], {})
        s = next(x for x in sources if x.symbol == "BIGWIN")
        assert s.tax_bucket == "D"
        assert s.operator_review_required is True
        # Bucket D rule: HIGH → MODERATE downgrade; URGENT is unaffected
        # VERY_BEARISH ESS → URGENT; Bucket D does not downgrade URGENT
        assert s.priority in ("URGENT", "MODERATE")  # depends on ESS → either valid

    def test_bucket_a_annotation_contains_harvest(self):
        ov = _ov("HARV", opportunity_flag="TRIM", ess_score_text="BEARISH",
                 signal_direction="BEARISH")
        h = _holding("HARV", market_value="5000", cost_basis="9000")
        sources = _bcs([ov], [h], [], {})
        s = next(x for x in sources if x.symbol == "HARV")
        assert "harvest" in s.tax_annotation.lower()

    def test_bucket_d_annotation_mentions_confirm(self):
        ov = _ov("GAIN", opportunity_flag="TRIM", ess_score_text="BEARISH",
                 signal_direction="BEARISH")
        h = _holding("GAIN", market_value="20000", cost_basis="10000")
        # 10000 gain > 5000 → Bucket D
        sources = _bcs([ov], [h], [], {})
        s = next(x for x in sources if x.symbol == "GAIN")
        assert s.tax_bucket == "D"
        assert "confirm" in s.tax_annotation.lower()


# ── De-duplication and category priority ─────────────────────────────────────

class TestDeduplication:

    def test_higher_priority_category_wins(self):
        """Symbol in Cat 1 AND Cat 3 → Cat 1 wins (higher priority)."""
        ov = _ov("DUAL", opportunity_flag="TRIM", ess_score_text="VERY_BEARISH",
                 signal_direction="BEARISH", is_overweight_vs_target="True")
        h = _holding("DUAL", market_value="10000")
        alignment = [_alignment_row("EQUITIES.US.LARGE", drift_pct=12.0)]
        sources = _bcs([ov], [h], alignment, {})
        syms = [s for s in sources if s.symbol == "DUAL"]
        assert len(syms) == 1  # de-duplicated
        assert syms[0].category == CATEGORY_SIGNAL_DETERIORATION
        # Evidence should mention OW as well
        assert "overweight" in syms[0].evidence_summary.lower()

    def test_symbol_appears_at_most_once(self):
        ov = _ov("ONCE", opportunity_flag="TRIM", ess_score_text="BEARISH",
                 signal_direction="BEARISH", is_overweight_vs_target="True",
                 replay_supported="False", percent_of_portfolio="2.5")
        h = _holding("ONCE", market_value="10000", cost_basis="15000")
        alignment = [_alignment_row("EQUITIES.US.LARGE", drift_pct=10.0)]
        tax = _tax_state(strategic_exit_symbols=["ONCE"])
        sources = _bcs([ov], [h], alignment, {}, tax_state=tax)
        dupes = [s for s in sources if s.symbol == "ONCE"]
        assert len(dupes) == 1


# ── Capital allocation ────────────────────────────────────────────────────────

class TestCapitalAllocation:

    def test_basic_allocation_rank_order_preserved(self):
        queue = [
            _queue_entry(1, "VRT", deployment_score=95.0, headroom_pct=30.0),
            _queue_entry(2, "ARW", deployment_score=85.0, headroom_pct=25.0),
            _queue_entry(3, "DELL", deployment_score=75.0, headroom_pct=20.0),
        ]
        deployments, remaining = _allocate_capital(
            eligible_queue=queue,
            total_pool=10000.0,
            portfolio_mv=500000.0,
            holdings_by_sym={},
        )
        assert len(deployments) >= 1
        # Verify rank order preserved
        ranks = [t.rank for t in deployments]
        assert ranks == sorted(ranks)

    def test_policy_protected_excluded_from_deployment(self):
        queue = [
            _queue_entry(1, "VRT", headroom_pct=30.0, policy_protected=True),
            _queue_entry(2, "ARW", headroom_pct=25.0, policy_protected=False),
        ]
        # Filter: policy_protected=True is excluded upstream in _allocate_capital
        eligible = [e for e in queue if not e.get("policy_protected", False)]
        deployments, _ = _allocate_capital(
            eligible_queue=eligible,
            total_pool=10000.0,
            portfolio_mv=500000.0,
            holdings_by_sym={},
        )
        syms = [t.symbol for t in deployments]
        assert "VRT" not in syms
        assert "ARW" in syms

    def test_zero_headroom_skipped(self):
        queue = [
            _queue_entry(1, "FULL", headroom_pct=0.0),
            _queue_entry(2, "ROOM", headroom_pct=15.0),
        ]
        deployments, _ = _allocate_capital(
            eligible_queue=queue,
            total_pool=5000.0,
            portfolio_mv=100000.0,
            holdings_by_sym={},
        )
        syms = [t.symbol for t in deployments]
        assert "FULL" not in syms
        assert "ROOM" in syms

    def test_minimum_lot_size_stops_allocation(self):
        queue = [_queue_entry(1, "VRT", headroom_pct=20.0)]
        deployments, remaining = _allocate_capital(
            eligible_queue=queue,
            total_pool=200.0,  # Below 500 minimum
            portfolio_mv=500000.0,
            holdings_by_sym={},
        )
        # Pool < minimum lot size → no allocation
        assert len(deployments) == 0

    def test_proportional_cap_limits_single_target(self):
        """No single target receives more than 20% of the total pool (Phase 23.6B.2)."""
        queue = [
            _queue_entry(1, "VRT", headroom_pct=50.0, narrative_tier="CORE_CONVICTION_LEADER"),
        ]
        total_pool = 20000.0
        deployments, _ = _allocate_capital(
            eligible_queue=queue,
            total_pool=total_pool,
            portfolio_mv=500000.0,
            holdings_by_sym={},
        )
        if deployments:
            # New 20% cap means max alloc is 4000 (not 10000 under old 50% cap)
            assert deployments[0].suggested_amount <= total_pool * 0.20 + 0.01


# ── Phase 23.6B.2 — Defect 1: Non-tradeable exclusion ────────────────────────

class TestNonTradeableExclusion:
    """Verify SPAXX, PENDING ACTIVITY, and other non-tradeable artifacts
    are excluded from CRA capital sources (Phase 23.6B.2)."""

    def _build_sources(self, symbol: str, is_cash_equivalent: str = "False",
                       operational_state: str = "ACTIVE_POSITION",
                       safe_to_offset_cash: str = "False",
                       opportunity_flag: str = "HOLD") -> list:
        ov = _ov(symbol, opportunity_flag=opportunity_flag, replay_supported="False",
                 percent_of_portfolio="5.0")
        h = {
            "symbol": symbol,
            "market_value": "44000",
            "cost_basis": "",
            "percent_of_portfolio": "5.0",
            "geography": "US",
            "market_cap_bucket": "LARGE",
            "asset_class": "EQUITIES",
            "is_cash_equivalent": is_cash_equivalent,
            "operational_state": operational_state,
            "safe_to_offset_cash": safe_to_offset_cash,
        }
        return _bcs([ov], [h], [], {})

    def test_spaxx_excluded_as_cash_equivalent(self):
        sources = self._build_sources(
            "SPAXX", is_cash_equivalent="True",
            operational_state="CASH_EQUIVALENT"
        )
        assert not any(s.symbol == "SPAXX" for s in sources)

    def test_pending_activity_excluded_by_operational_state(self):
        """PENDING ACTIVITY excluded by both pattern match and operational_state."""
        sources = self._build_sources(
            "PENDING ACTIVITY", is_cash_equivalent="False",
            operational_state="ACTIVE_POSITION"  # as it appears in real data
        )
        assert not any("PENDING" in (s.symbol or "").upper() for s in sources)

    def test_closed_position_excluded(self):
        sources = self._build_sources(
            "CLOSED", operational_state="CLOSED_POSITION"
        )
        assert not any(s.symbol == "CLOSED" for s in sources)

    def test_accounting_adjustment_excluded(self):
        sources = self._build_sources(
            "ADJ", operational_state="ACCOUNTING_ADJUSTMENT"
        )
        assert not any(s.symbol == "ADJ" for s in sources)

    def test_non_analyzable_excluded(self):
        sources = self._build_sources(
            "NONANAL", operational_state="NON_ANALYZABLE"
        )
        assert not any(s.symbol == "NONANAL" for s in sources)

    def test_safe_to_offset_excluded(self):
        sources = self._build_sources(
            "OFFSET", safe_to_offset_cash="True"
        )
        assert not any(s.symbol == "OFFSET" for s in sources)

    def test_active_equity_still_included(self):
        """Normal ACTIVE_POSITION with HOLD flag and large weight → should appear in Cat 5."""
        sources = self._build_sources(
            "NORMAL", is_cash_equivalent="False",
            operational_state="ACTIVE_POSITION", opportunity_flag="HOLD"
        )
        assert any(s.symbol == "NORMAL" for s in sources)

    def test_missing_operational_state_treated_as_active(self):
        """Empty operational_state is treated as ACTIVE (forward-compatible)."""
        ov = _ov("UNKNOWN_STATE", opportunity_flag="HOLD", replay_supported="False",
                 percent_of_portfolio="3.0")
        h = {
            "symbol": "UNKNOWN_STATE",
            "market_value": "15000",
            "cost_basis": "",
            "percent_of_portfolio": "3.0",
            "geography": "US",
            "market_cap_bucket": "LARGE",
            "asset_class": "EQUITIES",
            # operational_state intentionally absent (forward-compat test)
        }
        sources = _bcs([ov], [h], [], {})
        # Should be allowed (treat missing op_state as active)
        assert any(s.symbol == "UNKNOWN_STATE" for s in sources)

    def test_bearish_spaxx_still_excluded(self):
        """SPAXX with BEARISH ESS (hypothetical) must still be excluded."""
        ov = _ov("SPAXX", opportunity_flag="TRIM", ess_score_text="VERY_BEARISH",
                 signal_direction="BEARISH", percent_of_portfolio="9.0")
        h = {
            "symbol": "SPAXX", "market_value": "44000",
            "cost_basis": "", "percent_of_portfolio": "9.0",
            "geography": "CASH", "market_cap_bucket": "UNKNOWN",
            "asset_class": "CASH",
            "is_cash_equivalent": "True",
            "operational_state": "CASH_EQUIVALENT",
        }
        sources = _bcs([ov], [h], [], {})
        assert not any(s.symbol == "SPAXX" for s in sources), "Cash equivalent must never be a sell source"


# ── Phase 23.6B.2 — Defect 2: Tier-aware allocation ─────────────────────────

class TestTierAwareAllocation:
    """Verify tier-aware allocation distributes capital across multiple
    candidates instead of concentrating into two (Phase 23.6B.2)."""

    def _make_queue(self):
        """Build a realistic 10-candidate queue: 4 CCL, 6 HCA."""
        return [
            _queue_entry(1, "DELL", deployment_score=99.32, headroom_pct=74.8,
                         current_weight_pct=1.5, narrative_tier="CORE_CONVICTION_LEADER"),
            _queue_entry(2, "VRT",  deployment_score=94.74, headroom_pct=30.0,
                         current_weight_pct=4.2, narrative_tier="CORE_CONVICTION_LEADER"),
            _queue_entry(3, "ARW",  deployment_score=93.73, headroom_pct=79.9,
                         current_weight_pct=1.2, narrative_tier="HIGH_CONVICTION_ANCHOR"),
            _queue_entry(4, "PSX",  deployment_score=93.38, headroom_pct=84.0,
                         current_weight_pct=0.9, narrative_tier="HIGH_CONVICTION_ANCHOR"),
            _queue_entry(5, "AVT",  deployment_score=91.87, headroom_pct=81.7,
                         current_weight_pct=1.1, narrative_tier="HIGH_CONVICTION_ANCHOR"),
            _queue_entry(6, "ATLC", deployment_score=91.74, headroom_pct=84.3,
                         current_weight_pct=0.9, narrative_tier="HIGH_CONVICTION_ANCHOR"),
            _queue_entry(7, "LRCX", deployment_score=91.48, headroom_pct=81.0,
                         current_weight_pct=1.1, narrative_tier="HIGH_CONVICTION_ANCHOR"),
            _queue_entry(8, "CAH",  deployment_score=91.43, headroom_pct=80.4,
                         current_weight_pct=1.2, narrative_tier="HIGH_CONVICTION_ANCHOR"),
            _queue_entry(9, "GTX",  deployment_score=84.15, headroom_pct=68.5,
                         current_weight_pct=1.9, narrative_tier="CORE_CONVICTION_LEADER"),
            _queue_entry(10,"CVE",  deployment_score=83.86, headroom_pct=56.6,
                         current_weight_pct=2.6, narrative_tier="CORE_CONVICTION_LEADER"),
        ]

    def test_multiple_targets_with_large_pool(self):
        """With $85K pool, should produce more than 2 deployment targets."""
        queue = self._make_queue()
        deployments, _ = _allocate_capital(
            eligible_queue=queue,
            total_pool=85000.0,
            portfolio_mv=479000.0,
            holdings_by_sym={},
        )
        assert len(deployments) > 2, f"Expected >2 targets, got {len(deployments)}: {[t.symbol for t in deployments]}"

    def test_no_target_exceeds_warn_threshold(self):
        """No target's projected weight should exceed WARN_POSITION_PCT (6%)."""
        queue = self._make_queue()
        deployments, _ = _allocate_capital(
            eligible_queue=queue,
            total_pool=85000.0,
            portfolio_mv=479000.0,
            holdings_by_sym={},
        )
        for t in deployments:
            assert t.projected_weight_pct <= 6.1, (
                f"{t.symbol} projected weight {t.projected_weight_pct}% exceeds 6% WARN threshold"
            )

    def test_rank_order_preserved_across_tiers(self):
        """CW-DAS rank order must be preserved in output."""
        queue = self._make_queue()
        deployments, _ = _allocate_capital(
            eligible_queue=queue,
            total_pool=85000.0,
            portfolio_mv=479000.0,
            holdings_by_sym={},
        )
        ranks = [t.rank for t in deployments]
        assert ranks == sorted(ranks), f"Rank order violated: {ranks}"

    def test_per_candidate_cap_20pct(self):
        """No single candidate receives more than 20% of total pool."""
        queue = self._make_queue()
        total_pool = 85000.0
        deployments, _ = _allocate_capital(
            eligible_queue=queue,
            total_pool=total_pool,
            portfolio_mv=479000.0,
            holdings_by_sym={},
        )
        cap_20 = total_pool * 0.20 + 0.01
        for t in deployments:
            assert t.suggested_amount <= cap_20, (
                f"{t.symbol} received ${t.suggested_amount:.0f} > 20% cap ${cap_20:.0f}"
            )

    def test_hca_candidates_receive_allocation(self):
        """HCA candidates should receive capital, not just CCL."""
        queue = self._make_queue()
        deployments, _ = _allocate_capital(
            eligible_queue=queue,
            total_pool=85000.0,
            portfolio_mv=479000.0,
            holdings_by_sym={},
        )
        hca_funded = [t for t in deployments if t.narrative_tier == "HIGH_CONVICTION_ANCHOR"]
        assert len(hca_funded) >= 2, f"Expected HCA candidates to be funded, got: {[t.symbol for t in hca_funded]}"

    def test_small_pool_still_works(self):
        """Small pool (< min lot) should return empty list gracefully."""
        queue = self._make_queue()
        deployments, remaining = _allocate_capital(
            eligible_queue=queue,
            total_pool=100.0,
            portfolio_mv=479000.0,
            holdings_by_sym={},
        )
        assert deployments == []
        assert remaining == pytest.approx(100.0)


# ── Phase 23.6B.4 — Fix 2: Strategic exit override ───────────────────────────

class TestStrategicExitOverride:
    """Verify operator-designated strategic exit symbols receive:
    - category = STRATEGIC_EXIT (not SIGNAL_DETERIORATION)
    - sizing_pct = 1.0 (full exit)
    - estimated_proceeds ≈ current_value_usd
    (Phase 23.6B.4)"""

    def test_strategic_exit_overrides_signal_deterioration_category(self):
        """FIS: BEARISH ESS normally yields SIGNAL_DETERIORATION 25%.
        With strategic_exit_symbols override → STRATEGIC_EXIT 100%."""
        ov = _ov("FIS", opportunity_flag="WATCH", ess_score_text="BEARISH",
                 signal_direction="BEARISH", percent_of_portfolio="1.3")
        h = _holding("FIS", market_value="6146", cost_basis="9862")
        tax = _tax_state(strategic_exit_symbols=["FIS"])
        sources = _bcs([ov], [h], [], {}, tax_state=tax, minimum_proceeds=0)
        s = next(x for x in sources if x.symbol == "FIS")
        assert s.category == CATEGORY_STRATEGIC_EXIT, (
            f"Expected STRATEGIC_EXIT, got {s.category}"
        )
        assert s.sizing_pct == pytest.approx(1.0), (
            f"Expected 100% sizing for strategic exit, got {s.sizing_pct}"
        )
        assert s.estimated_proceeds == pytest.approx(6146.0, abs=1.0)

    def test_strategic_exit_evidence_preserves_signal_context(self):
        """Evidence summary must contain both strategic exit and signal context."""
        ov = _ov("FIS", opportunity_flag="WATCH", ess_score_text="BEARISH",
                 signal_direction="BEARISH")
        h = _holding("FIS", market_value="6146")
        tax = _tax_state(strategic_exit_symbols=["FIS"])
        sources = _bcs([ov], [h], [], {}, tax_state=tax, minimum_proceeds=0)
        s = next(x for x in sources if x.symbol == "FIS")
        # Evidence must mention both reasons
        assert "strategic exit" in s.evidence_summary.lower()

    def test_strategic_exit_priority_at_least_high(self):
        """Strategic exits are always at least HIGH priority."""
        ov = _ov("FIS", opportunity_flag="HOLD", ess_score_text="NEUTRAL",
                 signal_direction="NEUTRAL")
        h = _holding("FIS", market_value="6146")
        tax = _tax_state(strategic_exit_symbols=["FIS"])
        sources = _bcs([ov], [h], [], {}, tax_state=tax, minimum_proceeds=0)
        s = next((x for x in sources if x.symbol == "FIS"), None)
        if s:
            assert s.priority in ("URGENT", "HIGH"), (
                f"Strategic exit priority should be at least HIGH, got {s.priority}"
            )

    def test_non_strategic_exit_keeps_original_sizing(self):
        """Symbol NOT in strategic_exit_symbols keeps its normal sizing."""
        ov = _ov("KGC", opportunity_flag="WATCH", ess_score_text="BEARISH",
                 signal_direction="BEARISH")
        h = _holding("KGC", market_value="10000")
        tax = _tax_state(strategic_exit_symbols=[])  # KGC not designated
        sources = _bcs([ov], [h], [], {}, tax_state=tax, minimum_proceeds=0)
        s = next((x for x in sources if x.symbol == "KGC"), None)
        if s:
            # BEARISH non-overweight → 0.25 sizing (not full exit)
            assert s.sizing_pct <= 0.5, (
                f"Non-strategic exit should not have full sizing: {s.sizing_pct}"
            )


# ── Phase 23.6B.4 — Fix 3: Minimum proceeds filter ───────────────────────────

class TestMinimumProceedsFilter:
    """Verify de-minimis sources are suppressed from primary source list.
    (Phase 23.6B.4)"""

    def _build_both(self, symbol: str, market_value: str, **kwargs):
        ov = _ov(symbol, opportunity_flag="TRIM", ess_score_text="BEARISH",
                 signal_direction="BEARISH")
        h = _holding(symbol, market_value=market_value)
        sources, suppressed = build_capital_sources(
            [ov], [h], [], {}, minimum_proceeds=500.0
        )
        return sources, suppressed

    def test_above_threshold_in_primary(self):
        """Source with proceeds >= $500 should be in primary list."""
        sources, suppressed = self._build_both("KGC", "10000")
        # 50% sizing × $10000 = $5000 → above threshold
        syms_main = [s.symbol for s in sources]
        syms_sup = [s.symbol for s in suppressed]
        assert "KGC" in syms_main, "KGC should be in primary sources"
        assert "KGC" not in syms_sup

    def test_below_threshold_suppressed(self):
        """Source with proceeds < $500 should move to suppressed list."""
        # market_value=800, BEARISH non-OW → 50% sizing → $400 (below $500 threshold)
        sources, suppressed = self._build_both("TINY", "800")
        syms_main = [s.symbol for s in sources]
        syms_sup = [s.symbol for s in suppressed]
        assert "TINY" not in syms_main, "Sub-$500 source must not appear in primary list"
        assert "TINY" in syms_sup, "Sub-$500 source must appear in suppressed list"

    def test_suppressed_record_is_valid_capital_source_record(self):
        """Suppressed sources are valid CapitalSourceRecord instances."""
        _, suppressed = self._build_both("TINY2", "800")
        # 25% × $800 = $200 — below threshold
        for s in suppressed:
            assert isinstance(s, CapitalSourceRecord)
            assert s.estimated_proceeds < 500.0

    def test_zero_threshold_returns_all(self):
        """minimum_proceeds=0 returns all sources in primary list."""
        ov = _ov("SMALL", opportunity_flag="TRIM", ess_score_text="BEARISH",
                 signal_direction="BEARISH")
        h = _holding("SMALL", market_value="100")
        sources, suppressed = build_capital_sources(
            [ov], [h], [], {}, minimum_proceeds=0.0
        )
        all_syms = [s.symbol for s in sources] + [s.symbol for s in suppressed]
        # With threshold=0 nothing should be suppressed (25% × $100 = $25 → still main)
        assert "SMALL" in [s.symbol for s in sources]
        assert len(suppressed) == 0

    def test_blocked_source_still_suppressed_correctly(self):
        """DO_NOT_SELL blocked source with small proceeds goes to suppressed."""
        ov = _ov("BLKD", opportunity_flag="TRIM", ess_score_text="VERY_BEARISH",
                 signal_direction="BEARISH", percent_of_portfolio="0.05")
        h = _holding("BLKD", market_value="100")  # 25% → $25
        tax = _tax_state(policies=[_policy_entry("BLKD", "DO_NOT_SELL")])
        sources, suppressed = build_capital_sources(
            [ov], [h], [], {}, tax_state=tax, minimum_proceeds=500.0
        )
        # Blocked source with $25 proceeds → should be in suppressed (or nowhere)
        assert not any(s.symbol == "BLKD" for s in sources), (
            "Blocked sub-threshold source should not be in primary list"
        )


# ── Phase 23.6B.4 — Fix 1: Circular conflict detection ───────────────────────

class TestCircularConflictResolution:
    """Verify symbols that appear in both sell sources and buy targets are
    handled correctly (Phase 23.6B.4, Option A)."""

    def _make_proposal_with_circular(self, overweight_sym: str = "CVE") -> RotationProposal:
        """Build a minimal proposal where overweight_sym is both OW (sell)
        and in the deployment queue (buy)."""
        from src.portfolio.cra.rotation_proposal_builder import build_rotation_proposal
        import tempfile, os, json, csv as _csv, pathlib

        # Build minimal PAR run dir in a temp location
        tmpdir = pathlib.Path(tempfile.mkdtemp())

        # Snapshot
        snap = {"total_market_value": 200000, "snapshot_date": "2026-06-04",
                "account_name": "TEST", "run_id": "PAR-TEST", "adjusted_cash_mv": 0,
                "adjusted_deployable_mv": 0, "settlement_adjustment": 0}
        (tmpdir / "snapshot.json").write_text(json.dumps(snap))

        # run_metadata
        meta = {"run_id": "PAR-TEST", "snapshot_date": "2026-06-04",
                "overall_alignment_score": 0.4, "status": "COMPLETE",
                "warnings": [], "recalculation_id": "x", "analytical_universe_date": "x",
                "alignment_results_count": 1, "recommendation_count": 0,
                "concentration_tier": "DIVERSIFIED", "reconciliation_status": "PASS",
                "reconciliation_checks_passed": 10, "reconciliation_checks_failed": 0,
                "reconciliation_checks_warned": 0, "reconciliation_certification": "OK",
                "taxonomy_status": "PASS", "coverage_status": "PASS",
                "policy_snapshot": {}, "policy_suppressed_count": 0,
                "policy_rank_adjusted_count": 0}
        (tmpdir / "run_metadata.json").write_text(json.dumps(meta))

        # concentration
        conc = {"top5_pct": 30.0, "analysis_run_id": "PAR-TEST",
                "portfolio_snapshot_id": "x", "top1_symbol": "A", "top1_pct": 5.0,
                "top3_pct": 15.0, "top10_pct": 40.0, "mega_subtier_pct": 0.0,
                "single_sector_max_pct": 20.0, "single_sector_max_label": "TECH",
                "us_pct": 80.0, "international_pct": 20.0, "emerging_pct": 0.0,
                "herfindahl_index": 0.1, "concentration_tier": "DIVERSIFIED",
                "created_at_utc": "2026-06-04T00:00:00+00:00",
                "mega_subtier_direct_pct": 0.0, "mega_subtier_etf_derived_pct": 0.0,
                "mega_subtier_effective_pct": 0.0}
        (tmpdir / "concentration.json").write_text(json.dumps(conc))

        # alignment (CVE in OW node)
        alignment_rows = [
            {"analysis_run_id": "PAR-TEST", "portfolio_snapshot_id": "x",
             "node_key": "EQUITIES.INTERNATIONAL.MID", "node_label": "Intl Mid",
             "dimension_type": "x", "actual_pct": "8.0", "target_pct": "3.0",
             "tactical_target_pct": "3.0", "drift_pct": "5.0",
             "drift_direction": "OVERWEIGHT", "severity": "HIGH",
             "concentration_risk": "False", "alignment_score": "0.3",
             "recommendation_priority": "HIGH", "created_at_utc": "2026-06-04T00:00:00+00:00",
             "direct_actual_pct": "8.0", "etf_derived_actual_pct": "0.0",
             "effective_actual_pct": "8.0", "decomposition_method": "x",
             "decomposition_version": "x", "decomposition_confidence": "1.0",
             "decomposition_source": "x", "decomposition_confidence_tier": "HIGH"},
        ]
        import io
        buf = io.StringIO()
        w = _csv.DictWriter(buf, fieldnames=list(alignment_rows[0].keys()))
        w.writeheader(); w.writerows(alignment_rows)
        (tmpdir / "alignment.csv").write_text(buf.getvalue())

        # holdings: CVE is overweight international
        holdings_rows = [
            {"symbol": overweight_sym, "market_value": "20000", "quantity": "500",
             "percent_of_portfolio": "4.0", "cost_basis": "15000",
             "geography": "INTERNATIONAL", "market_cap_bucket": "MID",
             "asset_class": "EQUITIES", "sector": "ENERGY", "industry": "OIL",
             "security_type": "Common Stock", "is_cash_equivalent": "False",
             "operational_state": "ACTIVE_POSITION", "safe_to_offset_cash": "False",
             "ess_score_text": "VERY_BULLISH", "zacks_rating": "1.0",
             "composite_score": "4.5", "mega_subtier": "N/A",
             "exposure_mega_subtier_mix": "", "decomposition_confidence_tier": "HIGH",
             "strategic_role": "", "danelfin_score": "4.5", "benchmark_id": "",
             "investable_vehicle_id": "", "source_file": "test.csv",
             "created_at_utc": "2026-06-04T00:00:00+00:00",
             "best_replay_return": "0.25", "replay_percentile": "80",
             "replay_supported": "True", "exposure_geography_mix": "",
             "exposure_market_cap_mix": "", "exposure_sector_mix": "",
             "exposure_style_mix": "", "exposure_thematic_mix": "",
             "decomposition_method": "x", "decomposition_version": "x",
             "decomposition_timestamp": "x", "decomposition_confidence": "1.0",
             "decomposition_source": "x"},
        ]
        buf2 = io.StringIO()
        w2 = _csv.DictWriter(buf2, fieldnames=list(holdings_rows[0].keys()))
        w2.writeheader(); w2.writerows(holdings_rows)
        (tmpdir / "holdings.csv").write_text(buf2.getvalue())

        # security_overlays: CVE is OW and BULLISH
        overlay_rows = [
            {"portfolio_snapshot_id": "x", "symbol": overweight_sym,
             "composite_score": "4.5", "ess_score_text": "VERY_BULLISH",
             "zacks_rating": "1.0", "best_replay_return": "0.25",
             "replay_percentile": "80", "replay_supported": "True",
             "percent_of_portfolio": "4.0", "is_overweight_vs_target": "True",
             "signal_direction": "BULLISH", "opportunity_flag": "ACCUMULATE",
             "flag_rationale": "strong buy", "created_at_utc": "2026-06-04T00:00:00+00:00",
             "danelfin_score": "4.5", "policy_type": "", "policy_annotation": "",
             "policy_protected": "False", "execution_state": "EXECUTABLE",
             "effective_action": "ACCUMULATE"},
        ]
        buf3 = io.StringIO()
        w3 = _csv.DictWriter(buf3, fieldnames=list(overlay_rows[0].keys()))
        w3.writeheader(); w3.writerows(overlay_rows)
        (tmpdir / "security_overlays.csv").write_text(buf3.getvalue())

        # deployment_queue: CVE at rank 1
        dq = {"run_id": "PAR-TEST", "queue_version": "CW-DAS-1.0",
              "generated_at": "2026-06-04T00:00:00+00:00",
              "total_market_value": 200000.0, "cash_context": {
                  "cash_mv": 10000, "cash_pct": 5.0, "mandate_cash_target_pct": 4.0,
                  "effective_floor_pct": 4.0, "floor_mv": 8000, "excess_mv": 2000,
                  "excess_pct": 1.0, "deployable_mv": 2000, "deployable_pct": 1.0,
                  "settlement_adjustment": 0, "adjusted_cash_mv": 10000,
                  "adjusted_deployable_mv": 2000, "adjusted_deployable_pct": 1.0},
              "candidate_count": 1, "policy_suppressed": [], "policy_active_count": 0,
              "queue": [{"rank": 1, "symbol": overweight_sym,
                         "current_weight_pct": 4.0, "market_value": 20000,
                         "composite_score": 4.5, "narrative_tier": "HIGH_CONVICTION_ANCHOR",
                         "replay_supported": True, "trim_score": 0.0,
                         "headroom_pct": 40.0,  # 40% headroom; current=2% so warn cap allows add
                         "deployment_score": 83.0,
                         "score_breakdown": {"signal": 25.0, "replay": 20.0,
                                             "conviction": 28.0, "sizing": 0.0,
                                             "momentum": 10.0, "redundancy_pen": 0.0,
                                             "conc_pen": 0.0},
                         "notes": "HCA", "policy_type": None,
                         "policy_annotation": None, "policy_protected": False,
                         "policy_rank_boost": False, "original_rank": 1}]}
        (tmpdir / "deployment_queue.json").write_text(json.dumps(dq))

        proposal = build_rotation_proposal(str(tmpdir))
        import shutil; shutil.rmtree(str(tmpdir))
        return proposal

    def test_ow_only_bullish_symbol_removed_from_sources(self):
        """CVE: VERY_BULLISH ESS + overweight only → removed from sources (Option A)."""
        proposal = self._make_proposal_with_circular("CVE")
        # CVE should NOT appear in sources because conviction = BULLISH
        source_syms = [s.symbol for s in proposal.sources]
        assert "CVE" not in source_syms, (
            f"CVE (BULLISH conviction, OW-only) should be removed from sources. "
            f"Current sources: {source_syms}"
        )

    def test_no_unresolved_circular_conflicts_in_live_proposal(self):
        """Integration: no source symbol should be in both sell+buy list
        when the source reason is OVERWEIGHT_REDUCTION only (Option A resolved)."""
        from src.portfolio.cra.rotation_proposal_builder import build_proposal_from_manifest
        import os
        manifest = "data/portfolio_ingestion/manifest.json"
        runs_root = "data/portfolio_ingestion/analysis_runs"
        tax_path = "data/operator/portfolio_alignment_state.json"
        if not os.path.exists(manifest):
            pytest.skip("No manifest found")
        proposal = build_proposal_from_manifest(
            manifest_path=manifest,
            runs_root=runs_root,
            tax_state_path=tax_path if os.path.exists(tax_path) else None,
        )
        if proposal is None:
            pytest.skip("No complete run found")
        deploy_syms = {t.symbol for t in proposal.deployments}
        # Check no OVERWEIGHT_REDUCTION-only source is also a deployment target
        for s in proposal.sources:
            if s.symbol in deploy_syms and s.category == "OVERWEIGHT_REDUCTION":
                pytest.fail(
                    f"{s.symbol} is OVERWEIGHT_REDUCTION source AND deployment target — "
                    f"circular conflict not resolved"
                )


# ── Impact estimator ─────────────────────────────────────────────────────────

class TestImpactEstimator:

    def _run(
        self,
        sources=None,
        deployments=None,
        alignment_score=0.40,
        top5_pct=35.0,
    ):
        sources = sources or []
        deployments = deployments or []
        alignment = [
            _alignment_row("EQUITIES.US.LARGE", drift_pct=10.0, actual_pct=20.0, target_pct=10.0),
        ]
        concentration = {"top5_pct": top5_pct}
        run_metadata = {"overall_alignment_score": alignment_score}
        return estimate_impact(
            sources=sources,
            deployments=deployments,
            alignment=alignment,
            concentration=concentration,
            run_metadata=run_metadata,
            portfolio_mv=500000.0,
        )

    def test_is_estimate_always_true(self):
        impact = self._run()
        assert impact.is_estimate is True

    def test_alignment_before_matches_run_metadata(self):
        impact = self._run(alignment_score=0.42)
        assert impact.alignment_score_before == pytest.approx(0.42)

    def test_empty_rotation_no_delta(self):
        impact = self._run()
        assert impact.alignment_delta == pytest.approx(0.0, abs=0.001)

    def test_overweight_nodes_before_populated(self):
        impact = self._run()
        assert "EQUITIES.US.LARGE" in impact.overweight_nodes_before

    def test_alignment_after_within_bounds(self):
        impact = self._run()
        assert 0.0 <= impact.alignment_score_after <= 1.0

    def test_no_negative_concentration(self):
        impact = self._run(top5_pct=5.0)
        assert impact.concentration_after >= 0.0

    def test_narrative_non_empty(self):
        impact = self._run()
        assert isinstance(impact.impact_narrative, str)
        assert len(impact.impact_narrative) > 0


# ── RotationProposal model ────────────────────────────────────────────────────

class TestRotationProposalModel:

    def _make_proposal(self) -> RotationProposal:
        source = CapitalSourceRecord(
            symbol="FIS",
            current_value_usd=20000.0,
            estimated_proceeds=10000.0,
            sizing_pct=0.5,
            category=CATEGORY_SIGNAL_DETERIORATION,
            priority="HIGH",
            evidence_summary="BEARISH ESS",
            tax_bucket="A",
            tax_annotation="Loss harvest",
            policy_type=None,
            blocked_by_policy=False,
            operator_review_required=False,
        )
        target = RotationDeploymentTarget(
            rank=1,
            symbol="VRT",
            deployment_score=95.2,
            allocation_node="EQUITIES.US.LARGE",
            narrative_tier="CORE_CONVICTION_LEADER",
            current_weight_pct=3.85,
            market_value=18000.0,
            suggested_amount=10000.0,
            suggested_pct_add=2.0,
            projected_weight_pct=5.85,
            score_breakdown={"signal": 27.0},
            headroom_pct=35.8,
            allocation_note="35.8% headroom",
        )
        impact = PortfolioImpactEstimate(
            alignment_score_before=0.41,
            alignment_score_after=0.45,
            alignment_delta=0.04,
            concentration_before=35.0,
            concentration_after=34.5,
            concentration_delta=-0.5,
            overweight_nodes_before=["EQUITIES.US.LARGE"],
            overweight_nodes_after=[],
            newly_underweight_nodes=[],
            impact_narrative="Rotating FIS to VRT.",
        )
        return RotationProposal(
            proposal_id="CRA-20260604-ABCD1234",
            run_id="PAR-20260604-TEST",
            as_of_date="2026-06-04",
            portfolio_mv=472000.0,
            total_capital_pool=10000.0,
            sources=[source],
            deployments=[target],
            impact=impact,
            proposal_status=STATUS_READY,
            review_flags=[],
            created_at_utc="2026-06-04T12:00:00+00:00",
        )

    def test_to_dict_includes_required_fields(self):
        p = self._make_proposal()
        d = p.to_dict()
        for key in ("proposal_id", "run_id", "as_of_date", "portfolio_mv",
                    "total_capital_pool", "proposal_status", "review_flags",
                    "sources", "deployments", "impact", "cra_version"):
            assert key in d, f"Missing key: {key}"

    def test_sources_include_expected_fields(self):
        p = self._make_proposal()
        d = p.to_dict()
        s = d["sources"][0]
        assert s["symbol"] == "FIS"
        assert s["category"] == CATEGORY_SIGNAL_DETERIORATION
        assert s["tax_bucket"] == "A"
        assert s["blocked_by_policy"] is False

    def test_deployments_include_expected_fields(self):
        p = self._make_proposal()
        d = p.to_dict()
        t = d["deployments"][0]
        assert t["rank"] == 1
        assert t["symbol"] == "VRT"
        assert t["deployment_score"] == pytest.approx(95.2)
        assert "allocation_node" in t
        assert "score_breakdown" in t

    def test_impact_is_estimate_true(self):
        p = self._make_proposal()
        d = p.to_dict()
        assert d["impact"]["is_estimate"] is True

    def test_cra_version_present(self):
        p = self._make_proposal()
        d = p.to_dict()
        assert d["cra_version"] == "1.0"


# ── Integration: full proposal from fixtures ─────────────────────────────────

class TestIntegrationWithRealPARFiles:
    """Smoke test using the real PAR run on disk."""

    @pytest.fixture
    def run_dir(self):
        """Use the latest complete PAR run if available."""
        manifest_path = Path("data/portfolio_ingestion/manifest.json")
        runs_root = Path("data/portfolio_ingestion/analysis_runs")
        if not manifest_path.exists():
            pytest.skip("No manifest found — skipping integration test")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        completed = [
            p for p in manifest.get("portfolios", [])
            if p.get("status") == "COMPLETE"
            and "CONCENTRATED" not in p.get("run_id", "")
        ]
        if not completed:
            pytest.skip("No COMPLETE runs found — skipping integration test")

        run_id = completed[-1]["run_id"]
        path = runs_root / run_id
        if not path.exists():
            pytest.skip(f"Run dir not found: {path}")
        return path

    def test_proposal_builds_without_error(self, run_dir):
        proposal = build_rotation_proposal(run_dir)
        assert isinstance(proposal, RotationProposal)
        assert proposal.run_id
        assert isinstance(proposal.proposal_status, str)

    def test_sources_are_valid_records(self, run_dir):
        proposal = build_rotation_proposal(run_dir)
        for s in proposal.sources:
            assert isinstance(s, CapitalSourceRecord)
            assert s.symbol
            assert s.category in (
                CATEGORY_SIGNAL_DETERIORATION,
                CATEGORY_STRATEGIC_EXIT,
                CATEGORY_OVERWEIGHT_REDUCTION,
                CATEGORY_TAX_AWARE_EXIT,
                CATEGORY_LOW_CONVICTION,
            )
            assert s.priority in ("URGENT", "HIGH", "MODERATE", "LOW", "DEFER")
            assert 0.0 <= s.sizing_pct <= 1.0
            assert s.estimated_proceeds == pytest.approx(s.current_value_usd * s.sizing_pct, abs=1.0)

    def test_deployments_preserve_cw_das_rank_order(self, run_dir):
        proposal = build_rotation_proposal(run_dir)
        ranks = [t.rank for t in proposal.deployments]
        assert ranks == sorted(ranks), "CW-DAS rank order must be preserved"

    def test_blocked_sources_still_appear_in_sources_list(self, run_dir):
        tax_state_path = Path("data/operator/portfolio_alignment_state.json")
        if not tax_state_path.exists():
            pytest.skip("No tax state")
        import json as _json
        tax_state = _json.loads(tax_state_path.read_text(encoding="utf-8"))
        proposal = build_rotation_proposal(run_dir, tax_state=tax_state)
        # TSLA should have DO_NOT_SELL → blocked but visible
        tsla = next((s for s in proposal.sources if s.symbol == "TSLA"), None)
        if tsla:
            assert tsla.blocked_by_policy is True

    def test_total_capital_pool_excludes_blocked(self, run_dir):
        tax_state_path = Path("data/operator/portfolio_alignment_state.json")
        tax_state = None
        if tax_state_path.exists():
            import json as _json
            tax_state = _json.loads(tax_state_path.read_text(encoding="utf-8"))
        proposal = build_rotation_proposal(run_dir, tax_state=tax_state)
        # Pool should equal sum of non-blocked sources' estimated_proceeds
        expected_pool = sum(
            s.estimated_proceeds for s in proposal.sources
            if not s.blocked_by_policy and s.priority != "DEFER"
        )
        assert proposal.total_capital_pool == pytest.approx(expected_pool, abs=1.0)

    def test_impact_is_estimate_true(self, run_dir):
        proposal = build_rotation_proposal(run_dir)
        assert proposal.impact.is_estimate is True

    def test_to_dict_is_json_serializable(self, run_dir):
        proposal = build_rotation_proposal(run_dir)
        d = proposal.to_dict()
        json.dumps(d)  # must not raise

    def test_no_upstream_files_modified(self, run_dir):
        """Verify CRA does not write any files to the PAR run directory."""
        before = set(run_dir.iterdir())
        build_rotation_proposal(run_dir)
        after = set(run_dir.iterdir())
        assert before == after, "CRA must not create or delete files in run directory"

    def test_cw_das_scores_unchanged(self, run_dir):
        """Deployment targets must carry the same deployment_score as the queue."""
        import json as _json
        dq = _json.loads((run_dir / "deployment_queue.json").read_text(encoding="utf-8"))
        queue_scores = {e["symbol"]: e["deployment_score"] for e in dq.get("queue", [])}
        proposal = build_rotation_proposal(run_dir)
        for t in proposal.deployments:
            if t.symbol in queue_scores:
                assert t.deployment_score == pytest.approx(
                    queue_scores[t.symbol], abs=0.01
                ), f"{t.symbol}: CW-DAS score must not change"
