"""Phase 23.5 — Block Diagnostics + Next Best Action: backend unit tests.

Validates:
  1. _make_result() includes mandate_type in optimizer_metadata output.
  2. _make_result() includes concentration_tolerance in optimizer_metadata output.
  3. score_etf_candidate() adds overlap_with_ow_pct when worsens_overweight=True.
  4. score_etf_candidate() adds ow_node_key when worsens_overweight=True.
  5. overlap_with_ow_pct is 0.0 and ow_node_key is "" when worsens_overweight=False.
  6. run_parallel_optimizer() propagates mandate_type into result for MANDATE_BLOCKED node.
  7. run_parallel_optimizer() propagates concentration_tolerance for CONCENTRATED_ALPHA.
  8. run_parallel_optimizer() propagates overlap_with_ow_pct from ETF candidates.
  9. All new fields are additive — no existing fields removed or changed.
 10. DeploymentCandidate includes allocation_node field (additive, correct format).
"""
from __future__ import annotations

import dataclasses
from typing import Optional

import pytest

from src.portfolio.optimizer import (
    run_parallel_optimizer,
    score_etf_candidate,
    _make_result,
)
from src.portfolio.models import (
    AllocationAlignmentResult,
    MandateDriftInterpretation,
    PortfolioHolding,
)
from src.portfolio.deployment_queue import build_deployment_queue, DeploymentCandidate


# ─────────────────────────────────────────────────────────────────────────────
# Shared test factories
# ─────────────────────────────────────────────────────────────────────────────

_NOW  = "2026-06-04T00:00:00Z"
_RUN  = "RUN-23-5-TEST"
_SNAP = "PSNAP-23-5-TEST"


def _holding(
    symbol: str,
    pct: float = 2.0,
    geography: str = "US",
    market_cap_bucket: str = "LARGE",
    composite_score: Optional[float] = None,
    ess_score_text: Optional[str] = None,
    narrative_tier: str = "CCL",
    replay_supported: bool = True,
    is_cash_eq: bool = False,
) -> PortfolioHolding:
    return PortfolioHolding(
        portfolio_snapshot_id=_SNAP,
        snapshot_date="2026-06-04",
        account_name="Test",
        symbol=symbol,
        description=f"{symbol} test",
        quantity=100.0,
        market_value=pct * 1000,
        percent_of_portfolio=pct,
        asset_class="EQUITIES",
        geography=geography,
        market_cap_bucket=market_cap_bucket,
        mega_subtier="N/A",
        sector="Technology",
        industry="ALL",
        security_type="STOCK",
        cost_basis=None,
        composite_score=composite_score,
        ess_score_text=ess_score_text,
        zacks_rating=None,
        benchmark_id=None,
        investable_vehicle_id=None,
        source_file="test.csv",
        created_at_utc=_NOW,
        exposure_thematic_mix=(),
        exposure_mega_subtier_mix=(),
        strategic_role=None,
        is_cash_equivalent=is_cash_eq,
    )


def _alignment_result(
    node_key: str,
    drift_direction: str = "UNDERWEIGHT",
    severity: str = "MODERATE",
    drift_pct: float = -7.0,
) -> AllocationAlignmentResult:
    return AllocationAlignmentResult(
        analysis_run_id=_RUN,
        portfolio_snapshot_id=_SNAP,
        node_key=node_key,
        node_label=node_key,
        dimension_type="MARKET_CAP",
        actual_pct=8.0,
        target_pct=15.0,
        tactical_target_pct=15.0,
        drift_pct=drift_pct,
        drift_direction=drift_direction,
        severity=severity,
        concentration_risk="LOW",
        alignment_score=0.5,
        recommendation_priority=2,
        created_at_utc=_NOW,
        etf_derived_actual_pct=0.0,
    )


def _mandate_interp(
    node_key: str,
    mandate_type: str = "CONCENTRATED_ALPHA",
    mandate_urgency: str = "INFORMATIONAL",
    mandate_drift_label: str = "INTENTIONAL_UNDERWEIGHT",
    suppress: bool = True,
) -> MandateDriftInterpretation:
    return MandateDriftInterpretation(
        node_key=node_key,
        node_label=node_key,
        mandate_type=mandate_type,
        raw_drift_pct=-7.0,
        raw_severity="MODERATE",
        mandate_severity="NONE",
        mandate_drift_label=mandate_drift_label,
        mandate_urgency=mandate_urgency,
        mandate_rationale="Concentrated Alpha — intentional underweight.",
        suppress_recommendation=suppress,
    )


def _veh_note(
    symbol: str,
    worsens: bool = False,
    overlap_ow: float = 0.0,
    target_coverage: float = 15.0,
    suit_tier: str = "MEDIUM",
    suit_score: float = 55.0,
) -> dict:
    return {
        "symbol": symbol,
        "target_node_coverage_pct": target_coverage,
        "off_target_exposure_pct": 60.0,
        "overlap_with_existing_pct": overlap_ow,
        "worsens_existing_overweight": worsens,
        "thematic_concentration_added": "",
        "strategic_role": "BROAD_US_EQUITY",
        "suitability_score": suit_score,
        "suitability_tier": suit_tier,
        "suitability_explanation": "test",
    }


def _rec_dict(
    rec_id: str = "REC-23500001",
    rec_type: str = "INCREASE_UNDERWEIGHT",
    node_key: str = "EQUITIES.US.LARGE",
    veh_notes: Optional[list] = None,
) -> dict:
    return {
        "recommendation_id": rec_id,
        "recommendation_type": rec_type,
        "affected_node_key": node_key,
        "severity": "MODERATE",
        "title": f"Build {node_key}",
        "rationale": "test",
        "priority": 2,
        "confidence": "HIGH",
        "affected_symbols": ["VOO"],
        "vehicle_suitability_notes": veh_notes or [],
        "mandate_urgency": "INFORMATIONAL",
        "mandate_drift_label": "INTENTIONAL_UNDERWEIGHT",
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1 — _make_result() includes mandate_type
# ─────────────────────────────────────────────────────────────────────────────

def test_make_result_includes_mandate_type():
    result = _make_result(
        rec_id="REC-TEST-MT",
        rec_type="INCREASE_UNDERWEIGHT",
        target_node="EQUITIES.US.LARGE",
        legacy_vehicles=["VOO"],
        candidates=[],
        preferred_candidate=None,
        optimizer_decision="MANDATE_BLOCKED",
        conflicts_detected=[],
        mandate_blocked=True,
        mandate_type="CONCENTRATED_ALPHA",
        concentration_tolerance=0.9,
    )
    assert "mandate_type" in result, "_make_result must include mandate_type"
    assert result["mandate_type"] == "CONCENTRATED_ALPHA"


# ─────────────────────────────────────────────────────────────────────────────
# 2 — _make_result() includes concentration_tolerance
# ─────────────────────────────────────────────────────────────────────────────

def test_make_result_includes_concentration_tolerance():
    result = _make_result(
        rec_id="REC-TEST-CT",
        rec_type="INCREASE_UNDERWEIGHT",
        target_node="EQUITIES.US.LARGE",
        legacy_vehicles=["VOO"],
        candidates=[],
        preferred_candidate=None,
        optimizer_decision="MANDATE_BLOCKED",
        conflicts_detected=[],
        mandate_blocked=True,
        mandate_type="CONCENTRATED_ALPHA",
        concentration_tolerance=0.9,
    )
    assert "concentration_tolerance" in result, "_make_result must include concentration_tolerance"
    assert result["concentration_tolerance"] == pytest.approx(0.9)


# ─────────────────────────────────────────────────────────────────────────────
# 3 — score_etf_candidate() adds overlap_with_ow_pct when worsens=True
# ─────────────────────────────────────────────────────────────────────────────

def test_etf_candidate_overlap_with_ow_pct_when_worsens():
    note = _veh_note("VOO", worsens=True, overlap_ow=30.0)
    overweight_nodes = {"EQUITIES.US.LARGE": 3.5}

    result = score_etf_candidate(
        symbol="VOO",
        target_node="EQUITIES.US.LARGE",
        node_gap=-7.0,
        suitability_note=note,
        overweight_nodes=overweight_nodes,
        mandate_gate="PASS",
        mandate_blocked=False,
    )
    assert "overlap_with_ow_pct" in result, "ETF candidate must include overlap_with_ow_pct"
    assert result["overlap_with_ow_pct"] == pytest.approx(30.0)


# ─────────────────────────────────────────────────────────────────────────────
# 4 — score_etf_candidate() adds ow_node_key when worsens=True
# ─────────────────────────────────────────────────────────────────────────────

def test_etf_candidate_ow_node_key_when_worsens():
    note = _veh_note("VOO", worsens=True, overlap_ow=30.0)
    overweight_nodes = {"EQUITIES.US.LARGE": 3.5}

    result = score_etf_candidate(
        symbol="VOO",
        target_node="EQUITIES.US.LARGE",
        node_gap=-7.0,
        suitability_note=note,
        overweight_nodes=overweight_nodes,
        mandate_gate="PASS",
        mandate_blocked=False,
    )
    assert "ow_node_key" in result, "ETF candidate must include ow_node_key"
    assert result["ow_node_key"] == "EQUITIES.US.LARGE"


# ─────────────────────────────────────────────────────────────────────────────
# 5 — overlap_with_ow_pct = 0.0 and ow_node_key = "" when worsens=False
# ─────────────────────────────────────────────────────────────────────────────

def test_etf_candidate_no_ow_fields_when_not_worsens():
    note = _veh_note("SPY", worsens=False, overlap_ow=0.0, target_coverage=15.0, suit_tier="MEDIUM")
    overweight_nodes = {}

    result = score_etf_candidate(
        symbol="SPY",
        target_node="EQUITIES.US.LARGE",
        node_gap=-7.0,
        suitability_note=note,
        overweight_nodes=overweight_nodes,
        mandate_gate="PASS",
        mandate_blocked=False,
    )
    assert result["overlap_with_ow_pct"] == 0.0, "No OW overlap when worsens=False"
    assert result["ow_node_key"] == "", "No OW node key when worsens=False"


# ─────────────────────────────────────────────────────────────────────────────
# 6 — run_parallel_optimizer() propagates mandate_type for MANDATE_BLOCKED
# ─────────────────────────────────────────────────────────────────────────────

def test_run_optimizer_propagates_mandate_type():
    recs = [_rec_dict(
        "REC-23-MT-01",
        veh_notes=[_veh_note("VOO", worsens=True, overlap_ow=30.0)],
    )]
    mandate = _mandate_interp(
        "EQUITIES.US.LARGE",
        mandate_type="CONCENTRATED_ALPHA",
        mandate_urgency="INFORMATIONAL",
        suppress=True,
    )
    results = run_parallel_optimizer(
        recs_with_overlay=recs,
        holdings=[],
        overlays=[],
        profiles=[],
        alignment_results=[_alignment_result("EQUITIES.US.LARGE")],
        mandate_interpretations=[mandate],
    )
    opt = results.get("REC-23-MT-01", {})
    assert opt.get("optimizer_decision") == "MANDATE_BLOCKED"
    assert opt.get("mandate_type") == "CONCENTRATED_ALPHA", (
        "mandate_type must be propagated for MANDATE_BLOCKED recommendations"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 7 — run_parallel_optimizer() propagates concentration_tolerance for CONCENTRATED_ALPHA
# ─────────────────────────────────────────────────────────────────────────────

def test_run_optimizer_propagates_concentration_tolerance():
    recs = [_rec_dict("REC-23-CT-01")]
    mandate = _mandate_interp(
        "EQUITIES.US.LARGE",
        mandate_type="CONCENTRATED_ALPHA",
        mandate_urgency="INFORMATIONAL",
        suppress=True,
    )
    results = run_parallel_optimizer(
        recs_with_overlay=recs,
        holdings=[],
        overlays=[],
        profiles=[],
        alignment_results=[_alignment_result("EQUITIES.US.LARGE")],
        mandate_interpretations=[mandate],
    )
    opt = results.get("REC-23-CT-01", {})
    assert opt.get("mandate_blocked") is True
    # CONCENTRATED_ALPHA concentration_tolerance = 0.9
    assert opt.get("concentration_tolerance") == pytest.approx(0.9), (
        "CONCENTRATED_ALPHA concentration_tolerance must be 0.9"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 8 — run_parallel_optimizer() propagates overlap_with_ow_pct from ETF candidates
# ─────────────────────────────────────────────────────────────────────────────

def test_run_optimizer_propagates_overlap_with_ow_pct():
    recs = [_rec_dict(
        "REC-23-OW-01",
        veh_notes=[_veh_note("VOO", worsens=True, overlap_ow=35.0, suit_tier="MEDIUM")],
    )]
    # Not mandate-blocked; ETF gate fails due to worsens=True
    results = run_parallel_optimizer(
        recs_with_overlay=recs,
        holdings=[],
        overlays=[],
        profiles=[],
        alignment_results=[
            _alignment_result("EQUITIES.US.LARGE"),
            _alignment_result("EQUITIES.US.LARGE", drift_direction="OVERWEIGHT", severity="MODERATE", drift_pct=3.5),
        ],
        mandate_interpretations=[],
    )
    opt = results.get("REC-23-OW-01", {})
    # ETF candidate should have worsens=True; overlap should propagate
    assert opt.get("overlap_with_ow_pct", -1) >= 0.0, (
        "overlap_with_ow_pct must be present and >= 0"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 9 — All new fields are additive — existing fields present and unchanged
# ─────────────────────────────────────────────────────────────────────────────

def test_new_fields_are_additive_not_destructive():
    """Existing optimizer_metadata fields must all still be present."""
    recs = [_rec_dict("REC-23-ADDITIVE")]
    mandate = _mandate_interp(
        "EQUITIES.US.LARGE",
        mandate_urgency="INFORMATIONAL",
        suppress=True,
    )
    results = run_parallel_optimizer(
        recs_with_overlay=recs,
        holdings=[],
        overlays=[],
        profiles=[],
        alignment_results=[_alignment_result("EQUITIES.US.LARGE")],
        mandate_interpretations=[mandate],
    )
    opt = results.get("REC-23-ADDITIVE", {})
    # All pre-23.5 fields must still be present
    required_pre_fields = [
        "rec_id", "rec_type", "target_node", "legacy_vehicles",
        "candidates", "preferred_candidate", "optimizer_decision",
        "conflicts_detected", "mandate_blocked", "optimizer_version",
        "preferred_display",
    ]
    for field in required_pre_fields:
        assert field in opt, f"Pre-23.5 field '{field}' must still be present in optimizer_metadata"
    # All new 23.5 fields must also be present
    for field in ["mandate_type", "concentration_tolerance", "overlap_with_ow_pct", "ow_node_key"]:
        assert field in opt, f"Phase 23.5 field '{field}' must be present in optimizer_metadata"


# ─────────────────────────────────────────────────────────────────────────────
# 10 — DeploymentCandidate includes allocation_node field
# ─────────────────────────────────────────────────────────────────────────────

def test_deployment_candidate_has_allocation_node_field():
    """DeploymentCandidate dataclass must include the allocation_node field."""
    fields = {f.name for f in dataclasses.fields(DeploymentCandidate)}
    assert "allocation_node" in fields, (
        "DeploymentCandidate must have an allocation_node field (Phase 23.5)"
    )


def test_deployment_candidate_allocation_node_default_empty():
    """allocation_node should default to empty string (backward-compatible)."""
    # Verify default is "" by checking field default
    field_defaults = {
        f.name: f.default
        for f in dataclasses.fields(DeploymentCandidate)
        if f.default is not dataclasses.MISSING
    }
    assert field_defaults.get("allocation_node") == "", (
        "allocation_node default must be '' for backward compatibility"
    )


def test_build_deployment_queue_populates_allocation_node():
    """build_deployment_queue() must populate allocation_node on returned candidates."""
    from src.portfolio.models import (
        SecurityIntelligenceOverlay,
        HoldingStrategicProfile,
    )

    # Build a minimal eligible holding
    h = PortfolioHolding(
        portfolio_snapshot_id=_SNAP,
        snapshot_date="2026-06-04",
        account_name="Test",
        symbol="VRT",
        description="VRT test",
        quantity=100.0,
        market_value=2000.0,
        percent_of_portfolio=2.0,
        asset_class="EQUITIES",
        geography="US",
        market_cap_bucket="LARGE",
        mega_subtier="N/A",
        sector="Technology",
        industry="ALL",
        security_type="STOCK",
        cost_basis=None,
        composite_score=4.5,
        ess_score_text="VERY_BULLISH",
        zacks_rating=None,
        benchmark_id=None,
        investable_vehicle_id=None,
        source_file="test.csv",
        created_at_utc=_NOW,
        exposure_thematic_mix=(),
        exposure_mega_subtier_mix=(),
        strategic_role=None,
        is_cash_equivalent=False,
    )

    overlay = SecurityIntelligenceOverlay(
        portfolio_snapshot_id=_SNAP,
        symbol="VRT",
        composite_score=4.5,
        ess_score_text="VERY_BULLISH",
        zacks_rating=None,
        best_replay_return=None,
        replay_percentile=90.0,
        replay_supported=True,
        percent_of_portfolio=2.0,
        is_overweight_vs_target=False,
        signal_direction="BULLISH",
        opportunity_flag="ACCUMULATE",
        flag_rationale="High conviction, replay-supported.",
        created_at_utc=_NOW,
    )

    profile = HoldingStrategicProfile(
        portfolio_snapshot_id=_SNAP,
        symbol="VRT",
        security_type="STOCK",
        percent_of_portfolio=2.0,
        strategic_classification="HIGH_CONVICTION_RETAIN",
        trim_priority_score=15.0,
        trim_factors=(),
        thematic_overlap_clusters=(),
        overlap_peers=(),
        thematic_redundancy_score=10.0,
        strategic_role="",
        strategic_importance="HIGH",
        exposure_origin="DIRECT_INTENTIONAL",
        trim_rationale="",
        retain_rationale="",
        classification_trace="",
        concentration_pressure=5.0,
        diversification_contribution=80.0,
        created_at_utc=_NOW,
        narrative_tier="CORE_CONVICTION_LEADER",
        strategic_anchor_rank=1,
    )

    queue = build_deployment_queue(
        portfolio_snapshot_id=_SNAP,
        holdings=[h],
        overlays=[overlay],
        strategic_profiles=[profile],
        alignment_results=[],
        total_market_value=100_000.0,
    )

    assert len(queue) > 0, "Queue should have at least one candidate"
    vrt_candidate = next((c for c in queue if c.symbol == "VRT"), None)
    assert vrt_candidate is not None, "VRT should be in deployment queue"
    assert vrt_candidate.allocation_node == "EQUITIES.US.LARGE", (
        f"allocation_node should be 'EQUITIES.US.LARGE', got '{vrt_candidate.allocation_node}'"
    )
