"""Phase 7.3A — Parallel Optimizer unit tests.

Validates:
  1. Legacy recommendation order is unchanged when optimizer runs.
  2. optimizer_metadata is populated on each recommendation.
  3. VOO receives low/blocked PIS when it worsens the HYPER_MEGA overweight.
  4. VRT outranks VOO for US Large (CCL tier, composite 4.556, replay=True).
  5. LRCX outranks VOO for US Large (HCA tier, composite 4.500, replay=True).
  6. DELL outranks VOO for US Large (HCA tier, composite 4.500, replay=True).
  7. Mandate-blocked recommendations cannot receive actionable PIS.
  8. Security-first: securities in target node are evaluated before ETFs.
  9. ETF gate blocks candidates with NCS < 10% after OW leakage penalty.
  10. Conflict detection: T1 (worsens OW), T2 (shared vehicle), T3 (mandate vs engine).
  11. run_parallel_optimizer returns a result for every recommendation.
"""
from __future__ import annotations

import dataclasses
from typing import Optional

import pytest

from src.portfolio.optimizer import (
    run_parallel_optimizer,
    score_security_candidate,
    score_etf_candidate,
    detect_conflicts,
    _mandate_gate_for_node,
    _holding_in_target_node,
    _overweight_nodes_from_alignment,
)
from src.portfolio.models import (
    AllocationAlignmentResult,
    MandateDriftInterpretation,
    PortfolioHolding,
    VehicleSuitabilityNote,
)


# ─────────────────────────────────────────────────────────────────────────────
# Test factories
# ─────────────────────────────────────────────────────────────────────────────

_NOW = "2026-05-29T00:00:00Z"
_RUN = "RUN-OPT-TEST"
_SNAP = "PSNAP-OPT-TEST"


def _holding(
    symbol: str,
    pct: float = 2.0,
    asset_class: str = "EQUITIES",
    geography: str = "US",
    market_cap_bucket: str = "LARGE",
    mega_subtier: str = "N/A",
    composite_score: Optional[float] = None,
    ess_score_text: Optional[str] = None,
    is_cash_eq: bool = False,
) -> PortfolioHolding:
    return PortfolioHolding(
        portfolio_snapshot_id=_SNAP,
        snapshot_date="2026-05-29",
        account_name="Test",
        symbol=symbol,
        description=f"{symbol} test",
        quantity=100.0,
        market_value=pct * 1000,
        percent_of_portfolio=pct,
        asset_class=asset_class,
        geography=geography,
        market_cap_bucket=market_cap_bucket,
        mega_subtier=mega_subtier,
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
    actual_pct: float = 8.0,
    tactical_target_pct: float = 15.0,
    drift_pct: float = -7.0,
) -> AllocationAlignmentResult:
    return AllocationAlignmentResult(
        analysis_run_id=_RUN,
        portfolio_snapshot_id=_SNAP,
        node_key=node_key,
        node_label=node_key,
        dimension_type="MARKET_CAP",
        actual_pct=actual_pct,
        target_pct=tactical_target_pct,
        tactical_target_pct=tactical_target_pct,
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
    mandate_urgency: str = "MODERATE",
    mandate_drift_label: str = "STANDARD_UNDERWEIGHT",
    suppress: bool = False,
) -> MandateDriftInterpretation:
    return MandateDriftInterpretation(
        node_key=node_key,
        node_label=node_key,
        mandate_type="CONCENTRATED_ALPHA",
        raw_drift_pct=-7.0,
        raw_severity="MODERATE",
        mandate_severity="MODERATE",
        mandate_drift_label=mandate_drift_label,
        mandate_urgency=mandate_urgency,
        mandate_rationale="test",
        suppress_recommendation=suppress,
    )


def _veh_suitability_note(
    symbol: str,
    target_coverage: float = 15.0,
    off_target: float = 60.0,
    overlap: float = 30.0,
    worsens: bool = False,
    suit_score: float = 55.0,
    suit_tier: str = "MEDIUM",
) -> dict:
    """Build a VehicleSuitabilityNote as a dict (same as what rec dicts carry)."""
    return {
        "symbol": symbol,
        "target_node_coverage_pct": target_coverage,
        "off_target_exposure_pct": off_target,
        "overlap_with_existing_pct": overlap,
        "worsens_existing_overweight": worsens,
        "thematic_concentration_added": "",
        "strategic_role": "BROAD_US_EQUITY",
        "suitability_score": suit_score,
        "suitability_tier": suit_tier,
        "suitability_explanation": f"{symbol} test explanation",
    }


def _rec_dict(
    rec_id: str = "REC-TEST0001",
    rec_type: str = "INCREASE_UNDERWEIGHT",
    node_key: str = "EQUITIES.US.LARGE",
    severity: str = "MODERATE",
    veh_notes: Optional[list] = None,
    affected_symbols: Optional[list] = None,
    mandate_urgency: str = "MODERATE",
    mandate_drift_label: str = "STANDARD_UNDERWEIGHT",
) -> dict:
    return {
        "recommendation_id": rec_id,
        "recommendation_type": rec_type,
        "affected_node_key": node_key,
        "severity": severity,
        "title": f"Build {node_key}",
        "rationale": "test",
        "priority": 2,
        "vehicle_suitability_notes": veh_notes or [],
        "affected_symbols": affected_symbols or [],
        "drift_pct": -7.0,
        "mandate_urgency": mandate_urgency,
        "mandate_drift_label": mandate_drift_label,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1 — Legacy recommendation order is unchanged when optimizer runs
# ─────────────────────────────────────────────────────────────────────────────

def test_legacy_recommendation_order_unchanged():
    """Optimizer must not modify or reorder the input rec list."""
    recs = [
        _rec_dict("REC-00000001", "INCREASE_UNDERWEIGHT", "EQUITIES.US.LARGE"),
        _rec_dict("REC-00000002", "REDUCE_OVERWEIGHT", "EQUITIES.US.MEGA.HYPER_MEGA"),
        _rec_dict("REC-00000003", "INCREASE_UNDERWEIGHT", "EQUITIES.US.MID"),
    ]
    original_ids = [r["recommendation_id"] for r in recs]

    run_parallel_optimizer(
        recs_with_overlay=recs,
        holdings=[],
        overlays=[],
        profiles=[],
        alignment_results=[],
        mandate_interpretations=[],
    )

    # Rec list order and content are unchanged
    assert [r["recommendation_id"] for r in recs] == original_ids, (
        "Optimizer must not reorder the input recommendation list"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2 — optimizer_metadata is populated on each rec
# ─────────────────────────────────────────────────────────────────────────────

def test_optimizer_metadata_populated():
    """Every rec dict should have optimizer_metadata injected by run_parallel_optimizer."""
    recs = [
        _rec_dict("REC-META0001", "INCREASE_UNDERWEIGHT", "EQUITIES.US.LARGE"),
        _rec_dict("REC-META0002", "REDUCE_OVERWEIGHT", "EQUITIES.US.MEGA.HYPER_MEGA"),
    ]

    results = run_parallel_optimizer(
        recs_with_overlay=recs,
        holdings=[],
        overlays=[],
        profiles=[],
        alignment_results=[],
        mandate_interpretations=[],
    )

    assert "REC-META0001" in results, "INCREASE_UNDERWEIGHT rec must be in optimizer_scores"
    assert "REC-META0002" in results, "REDUCE_OVERWEIGHT rec must be in optimizer_scores"

    # Verify result structure
    opt = results["REC-META0001"]
    assert "optimizer_decision" in opt
    assert "candidates" in opt
    assert "mandate_blocked" in opt
    assert "optimizer_version" in opt
    assert opt["optimizer_version"] in ("7.3A", "7.3B", "7.3C")


# ─────────────────────────────────────────────────────────────────────────────
# 3 — VOO receives low/blocked PIS when it worsens HYPER_MEGA overweight
# ─────────────────────────────────────────────────────────────────────────────

def test_voo_low_pis_when_worsens_hyper_mega():
    """VOO for EQUITIES.US.LARGE should have ETF_GATED or very low PIS
    when it has worsens_existing_overweight=True (T1 conflict with HYPER_MEGA)."""
    node_gap = -7.34  # US Large is underweight
    overweight_nodes = {"EQUITIES.US.MEGA.HYPER_MEGA": 3.71}  # HYPER_MEGA overweight

    voo_note = _veh_suitability_note(
        "VOO",
        target_coverage=15.0,
        off_target=60.0,
        overlap=30.0,
        worsens=True,             # T1 conflict
        suit_score=40.0,
        suit_tier="MEDIUM",
    )

    candidate = score_etf_candidate(
        symbol="VOO",
        target_node="EQUITIES.US.LARGE",
        node_gap=node_gap,
        suitability_note=voo_note,
        overweight_nodes=overweight_nodes,
        mandate_gate="PASS",
        mandate_blocked=False,
    )

    # VOO worsens OW → conflict_penalty=20 → should be ETF_GATED or very low PIS
    assert candidate["worsens_overweight"] is True
    # PIS should be significantly reduced due to conflict penalty
    # Expected: node_gap_component ≈ min(7.34*2, 20) * (ncs/100) − 20 conflict → likely 0 or very low
    assert candidate["pis"] < 10.0, (
        f"VOO PIS should be low when worsening HYPER_MEGA OW, got {candidate['pis']:.2f}. "
        f"Status: {candidate['optimizer_status']}"
    )
    assert candidate["optimizer_status"] in ("ETF_GATED", "SUPPRESSED"), (
        f"VOO should be ETF_GATED or SUPPRESSED when worsening OW, got {candidate['optimizer_status']}"
    )


def test_voo_mandate_blocked_when_informational():
    """VOO for US Large should receive PIS=0 when mandate urgency=INFORMATIONAL."""
    voo_note = _veh_suitability_note("VOO")
    candidate = score_etf_candidate(
        symbol="VOO",
        target_node="EQUITIES.US.LARGE",
        node_gap=-7.34,
        suitability_note=voo_note,
        overweight_nodes={},
        mandate_gate="FAIL",
        mandate_blocked=True,  # Mandate INFORMATIONAL → blocked
    )
    assert candidate["pis"] == 0.0, (
        f"VOO PIS should be 0 when mandate blocked, got {candidate['pis']}"
    )
    assert candidate["optimizer_status"] == "MANDATE_BLOCKED"


# ─────────────────────────────────────────────────────────────────────────────
# 4 — VRT outranks VOO for US Large
# ─────────────────────────────────────────────────────────────────────────────

def test_vrt_outranks_voo_for_us_large():
    """VRT (CCL tier, composite 4.556, replay=True) should outscore VOO
    (ETF with T1 conflict) for EQUITIES.US.LARGE deployment."""
    node_gap = -7.34

    vrt_candidate = score_security_candidate(
        symbol="VRT",
        target_node="EQUITIES.US.LARGE",
        node_gap=node_gap,
        composite_score=4.556,
        ess_score="BULLISH",
        replay_supported=True,
        sti_tier="CCL",
        trim_priority_score=15.0,
        percent_of_portfolio=3.60,
        overweight_nodes={"EQUITIES.US.MEGA.HYPER_MEGA": 3.71},
        mandate_gate="PASS",
        mandate_blocked=False,
    )

    voo_note = _veh_suitability_note(
        "VOO", target_coverage=15.0, off_target=60.0, overlap=30.0,
        worsens=True, suit_score=40.0, suit_tier="MEDIUM"
    )
    voo_candidate = score_etf_candidate(
        symbol="VOO",
        target_node="EQUITIES.US.LARGE",
        node_gap=node_gap,
        suitability_note=voo_note,
        overweight_nodes={"EQUITIES.US.MEGA.HYPER_MEGA": 3.71},
        mandate_gate="PASS",
        mandate_blocked=False,
    )

    assert vrt_candidate["pis"] > voo_candidate["pis"], (
        f"VRT PIS ({vrt_candidate['pis']:.1f}) should exceed VOO PIS ({voo_candidate['pis']:.1f}) "
        f"for EQUITIES.US.LARGE. VRT: CCL tier, composite=4.556, replay=True. "
        f"VOO: T1 conflict (worsens HYPER_MEGA OW), NCS≈15%."
    )
    assert vrt_candidate["pis"] >= 60.0, (
        f"VRT should have PIS ≥ 60 (CCL+composite+replay+node_gap), got {vrt_candidate['pis']:.1f}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 5 — LRCX outranks VOO for US Large
# ─────────────────────────────────────────────────────────────────────────────

def test_lrcx_outranks_voo_for_us_large():
    """LRCX (HCA tier, composite 4.500, replay=True) should outscore VOO for US Large."""
    node_gap = -7.34

    lrcx_candidate = score_security_candidate(
        symbol="LRCX",
        target_node="EQUITIES.US.LARGE",
        node_gap=node_gap,
        composite_score=4.500,
        ess_score="BULLISH",
        replay_supported=True,
        sti_tier="HCA",
        trim_priority_score=10.0,
        percent_of_portfolio=0.95,
        overweight_nodes={"EQUITIES.US.MEGA.HYPER_MEGA": 3.71},
        mandate_gate="PASS",
        mandate_blocked=False,
    )

    voo_note = _veh_suitability_note(
        "VOO", target_coverage=15.0, off_target=60.0, overlap=30.0,
        worsens=True, suit_score=40.0, suit_tier="MEDIUM"
    )
    voo_candidate = score_etf_candidate(
        symbol="VOO",
        target_node="EQUITIES.US.LARGE",
        node_gap=node_gap,
        suitability_note=voo_note,
        overweight_nodes={"EQUITIES.US.MEGA.HYPER_MEGA": 3.71},
        mandate_gate="PASS",
        mandate_blocked=False,
    )

    assert lrcx_candidate["pis"] > voo_candidate["pis"], (
        f"LRCX PIS ({lrcx_candidate['pis']:.1f}) should exceed VOO PIS ({voo_candidate['pis']:.1f})"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 6 — DELL outranks VOO for US Large
# ─────────────────────────────────────────────────────────────────────────────

def test_dell_outranks_voo_for_us_large():
    """DELL (HCA tier, composite 4.500, replay=True) should outscore VOO for US Large."""
    node_gap = -7.34

    dell_candidate = score_security_candidate(
        symbol="DELL",
        target_node="EQUITIES.US.LARGE",
        node_gap=node_gap,
        composite_score=4.500,
        ess_score="BULLISH",
        replay_supported=True,
        sti_tier="HCA",
        trim_priority_score=8.0,
        percent_of_portfolio=1.32,
        overweight_nodes={"EQUITIES.US.MEGA.HYPER_MEGA": 3.71},
        mandate_gate="PASS",
        mandate_blocked=False,
    )

    voo_note = _veh_suitability_note(
        "VOO", target_coverage=15.0, off_target=60.0, overlap=30.0,
        worsens=True, suit_score=40.0, suit_tier="MEDIUM"
    )
    voo_candidate = score_etf_candidate(
        symbol="VOO",
        target_node="EQUITIES.US.LARGE",
        node_gap=node_gap,
        suitability_note=voo_note,
        overweight_nodes={"EQUITIES.US.MEGA.HYPER_MEGA": 3.71},
        mandate_gate="PASS",
        mandate_blocked=False,
    )

    assert dell_candidate["pis"] > voo_candidate["pis"], (
        f"DELL PIS ({dell_candidate['pis']:.1f}) should exceed VOO PIS ({voo_candidate['pis']:.1f})"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 7 — Mandate-blocked recs cannot receive actionable PIS
# ─────────────────────────────────────────────────────────────────────────────

def test_mandate_blocked_cannot_receive_actionable_pis():
    """When mandate_urgency=INFORMATIONAL, all candidates receive PIS=0 and MANDATE_BLOCKED status."""
    node_gap = -7.34
    blocked_interp = _mandate_interp(
        "EQUITIES.US.LARGE",
        mandate_urgency="INFORMATIONAL",
        mandate_drift_label="INTENTIONAL_UNDERWEIGHT",
        suppress=True,
    )

    mandate_gate, mandate_blocked = _mandate_gate_for_node(
        "EQUITIES.US.LARGE", [blocked_interp]
    )
    assert mandate_blocked is True, "INFORMATIONAL mandate should set mandate_blocked=True"
    assert mandate_gate == "FAIL"

    # Security candidate with excellent signals → still gets PIS=0
    vrt_blocked = score_security_candidate(
        symbol="VRT",
        target_node="EQUITIES.US.LARGE",
        node_gap=node_gap,
        composite_score=4.556,
        ess_score="BULLISH",
        replay_supported=True,
        sti_tier="CCL",
        trim_priority_score=0.0,
        percent_of_portfolio=3.60,
        overweight_nodes={},
        mandate_gate="FAIL",
        mandate_blocked=True,
    )
    assert vrt_blocked["pis"] == 0.0, (
        f"VRT should have PIS=0 when mandate blocked, got {vrt_blocked['pis']}"
    )
    assert vrt_blocked["optimizer_status"] == "MANDATE_BLOCKED"

    # ETF candidate → also PIS=0
    voo_blocked = score_etf_candidate(
        symbol="VOO",
        target_node="EQUITIES.US.LARGE",
        node_gap=node_gap,
        suitability_note=_veh_suitability_note("VOO"),
        overweight_nodes={},
        mandate_gate="FAIL",
        mandate_blocked=True,
    )
    assert voo_blocked["pis"] == 0.0
    assert voo_blocked["optimizer_status"] == "MANDATE_BLOCKED"


def test_mandate_blocked_via_run_parallel_optimizer():
    """run_parallel_optimizer returns MANDATE_BLOCKED decision for INFORMATIONAL mandate nodes."""
    recs = [
        _rec_dict(
            "REC-MB000001",
            "INCREASE_UNDERWEIGHT",
            "EQUITIES.US.LARGE",
            mandate_urgency="INFORMATIONAL",
            mandate_drift_label="INTENTIONAL_UNDERWEIGHT",
            veh_notes=[
                _veh_suitability_note("VOO", worsens=False, suit_tier="HIGH"),
            ],
        )
    ]
    holdings = [
        _holding("VRT", pct=3.60, composite_score=4.556),
    ]
    alignment = [
        _alignment_result("EQUITIES.US.LARGE", "UNDERWEIGHT", "MODERATE", drift_pct=-7.34),
    ]
    interps = [
        _mandate_interp(
            "EQUITIES.US.LARGE",
            mandate_urgency="INFORMATIONAL",
            mandate_drift_label="INTENTIONAL_UNDERWEIGHT",
            suppress=True,
        )
    ]

    results = run_parallel_optimizer(
        recs_with_overlay=recs,
        holdings=holdings,
        overlays=[],
        profiles=[],
        alignment_results=alignment,
        mandate_interpretations=interps,
    )

    opt = results["REC-MB000001"]
    assert opt["optimizer_decision"] == "MANDATE_BLOCKED", (
        f"Expected MANDATE_BLOCKED for INFORMATIONAL mandate, got {opt['optimizer_decision']}"
    )
    assert opt["mandate_blocked"] is True

    # All candidate PIS values must be 0
    for c in opt.get("candidates", []):
        assert c["pis"] == 0.0, (
            f"All candidates should have PIS=0 under mandate block, "
            f"but {c['symbol']} has PIS={c['pis']}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 8 — Security-first: securities are evaluated before ETFs in candidate list
# ─────────────────────────────────────────────────────────────────────────────

def test_security_first_candidate_evaluation():
    """High-conviction securities in target node should appear in the candidate list
    and outrank ETFs when they have better conviction/replay signals."""
    recs = [
        _rec_dict(
            "REC-SFIRST001",
            "INCREASE_UNDERWEIGHT",
            "EQUITIES.US.LARGE",
            veh_notes=[
                _veh_suitability_note("VOO", target_coverage=15.0, worsens=True, suit_tier="MEDIUM"),
            ],
        )
    ]
    holdings = [
        _holding("VRT", pct=3.60, market_cap_bucket="LARGE", composite_score=4.556),
        _holding("LRCX", pct=0.95, market_cap_bucket="LARGE", composite_score=4.500),
    ]
    alignment = [
        _alignment_result("EQUITIES.US.LARGE", "UNDERWEIGHT", "MODERATE", drift_pct=-7.34),
    ]

    results = run_parallel_optimizer(
        recs_with_overlay=recs,
        holdings=holdings,
        overlays=[],
        profiles=[],
        alignment_results=alignment,
        mandate_interpretations=[],
    )

    opt = results["REC-SFIRST001"]
    candidates = opt.get("candidates", [])

    # Both securities should be in the candidate list
    symbols = [c["symbol"] for c in candidates]
    assert "VRT" in symbols, "VRT should appear as a candidate for EQUITIES.US.LARGE"
    assert "LRCX" in symbols, "LRCX should appear as a candidate for EQUITIES.US.LARGE"
    assert "VOO" in symbols, "VOO should appear as a candidate (from vehicle_suitability_notes)"

    # Security candidates should be ranked higher than the ETF candidate
    # (because ETF has T1 conflict)
    security_candidates = [c for c in candidates if c["candidate_type"] == "SECURITY"]
    etf_candidates = [c for c in candidates if c["candidate_type"] == "ETF"]

    if security_candidates and etf_candidates:
        top_security_pis = max(c["pis"] for c in security_candidates)
        top_etf_pis = max(c["pis"] for c in etf_candidates)
        assert top_security_pis > top_etf_pis, (
            f"Top security PIS ({top_security_pis:.1f}) should exceed top ETF PIS ({top_etf_pis:.1f}) "
            f"when ETF has T1 conflict. Optimizer decision: {opt.get('optimizer_decision')}"
        )
        assert opt["optimizer_decision"] == "SECURITY_SUPERIOR"


# ─────────────────────────────────────────────────────────────────────────────
# 9 — ETF gate blocks candidates with NCS < 10%
# ─────────────────────────────────────────────────────────────────────────────

def test_etf_gate_blocks_low_ncs():
    """ETF with effective NCS < 10% after OW leakage penalty should receive ETF_GATED status."""
    # NCS = target_coverage − overlap*0.6 = 8.0 − 30.0*0.6 = 8.0 − 18.0 = -10 → clamped to 0
    low_ncs_note = _veh_suitability_note(
        "IVV",
        target_coverage=8.0,   # Already below 10%
        off_target=70.0,
        overlap=25.0,
        worsens=True,          # Makes it even worse
        suit_score=35.0,
        suit_tier="MEDIUM",
    )
    candidate = score_etf_candidate(
        symbol="IVV",
        target_node="EQUITIES.US.LARGE",
        node_gap=-7.34,
        suitability_note=low_ncs_note,
        overweight_nodes={"EQUITIES.US.MEGA.HYPER_MEGA": 3.71},
        mandate_gate="PASS",
        mandate_blocked=False,
    )
    assert candidate["ncs"] < 10.0, (
        f"IVV NCS should be < 10% after OW leakage, got {candidate['ncs']:.2f}%"
    )
    assert candidate["optimizer_status"] == "ETF_GATED", (
        f"IVV should be ETF_GATED with NCS={candidate['ncs']:.2f}%, got {candidate['optimizer_status']}"
    )


def test_etf_gate_passes_clean_etf():
    """An ETF with good NCS (≥10%), MEDIUM+ suitability, and no OW worsening passes the gate."""
    clean_note = _veh_suitability_note(
        "VTI",
        target_coverage=17.0,   # 17% for US Large in VTI
        off_target=56.0,
        overlap=5.0,
        worsens=False,           # No T1 conflict
        suit_score=65.0,
        suit_tier="MEDIUM",
    )
    candidate = score_etf_candidate(
        symbol="VTI",
        target_node="EQUITIES.US.LARGE",
        node_gap=-7.34,
        suitability_note=clean_note,
        overweight_nodes={},
        mandate_gate="PASS",
        mandate_blocked=False,
    )
    assert "PASS" in candidate["etf_gate"], (
        f"VTI ETF gate should be PASS, got '{candidate['etf_gate']}'"
    )
    assert candidate["optimizer_status"] == "ACTIONABLE"
    assert candidate["pis"] > 0.0


# ─────────────────────────────────────────────────────────────────────────────
# 10 — Conflict detection: T1, T2, T3
# ─────────────────────────────────────────────────────────────────────────────

def test_conflict_detection_t1_worsens_overweight():
    """T1 conflict detected when a Build rec's vehicle worsens an OW node being Reduced."""
    recs = [
        {
            "recommendation_id": "REC-CF000001",
            "recommendation_type": "INCREASE_UNDERWEIGHT",
            "affected_node_key": "EQUITIES.US.LARGE",
            "severity": "MODERATE",
            "title": "Build US Large",
            "vehicle_suitability_notes": [
                _veh_suitability_note("VOO", worsens=True),  # VOO worsens OW
            ],
            "mandate_urgency": "MODERATE",
        },
        {
            "recommendation_id": "REC-CF000002",
            "recommendation_type": "REDUCE_OVERWEIGHT",
            "affected_node_key": "EQUITIES.US.MEGA.HYPER_MEGA",
            "severity": "MODERATE",
            "title": "Reduce Hyper Mega",
            "vehicle_suitability_notes": [],
            "mandate_urgency": "MODERATE",
        },
    ]
    conflicts = detect_conflicts(recs)
    t1_conflicts = [c for c in conflicts if c["conflict_type"] == "T1"]
    assert len(t1_conflicts) >= 1, (
        f"Expected at least 1 T1 conflict (VOO worsens HYPER_MEGA OW), got {conflicts}"
    )
    assert t1_conflicts[0]["vehicle"] == "VOO"


def test_conflict_detection_t2_shared_vehicle():
    """T2 conflict detected when the same vehicle appears in two separate Build recs."""
    recs = [
        {
            "recommendation_id": "REC-CF000003",
            "recommendation_type": "INCREASE_UNDERWEIGHT",
            "affected_node_key": "EQUITIES.US.LARGE",
            "severity": "MODERATE",
            "title": "Build US Large",
            "affected_symbols": ["VOO", "IVV"],
            "vehicle_suitability_notes": [],
            "mandate_urgency": "MODERATE",
        },
        {
            "recommendation_id": "REC-CF000004",
            "recommendation_type": "INCREASE_UNDERWEIGHT",
            "affected_node_key": "EQUITIES.US.MEGA",
            "severity": "MODERATE",
            "title": "Build US Mega",
            "affected_symbols": ["VOO", "QQQ"],
            "vehicle_suitability_notes": [],
            "mandate_urgency": "MODERATE",
        },
    ]
    conflicts = detect_conflicts(recs)
    t2_conflicts = [c for c in conflicts if c["conflict_type"] == "T2"]
    assert len(t2_conflicts) >= 1, (
        f"Expected T2 conflict for shared VOO vehicle, got {conflicts}"
    )
    assert any(c["vehicle"] == "VOO" for c in t2_conflicts)


def test_conflict_detection_t3_mandate_severity_mismatch():
    """T3 conflict detected when engine severity=MODERATE but mandate_urgency=INFORMATIONAL."""
    recs = [
        {
            "recommendation_id": "REC-CF000005",
            "recommendation_type": "INCREASE_UNDERWEIGHT",
            "affected_node_key": "EQUITIES.US.LARGE",
            "severity": "MODERATE",               # Engine says MODERATE
            "title": "Build US Large",
            "vehicle_suitability_notes": [],
            "mandate_urgency": "INFORMATIONAL",    # Mandate says INFORMATIONAL → T3
        }
    ]
    conflicts = detect_conflicts(recs)
    t3_conflicts = [c for c in conflicts if c["conflict_type"] == "T3"]
    assert len(t3_conflicts) >= 1, (
        f"Expected T3 conflict for severity vs mandate_urgency mismatch, got {conflicts}"
    )
    assert t3_conflicts[0]["rec_a_id"] == "REC-CF000005"


# ─────────────────────────────────────────────────────────────────────────────
# 11 — run_parallel_optimizer returns result for every rec
# ─────────────────────────────────────────────────────────────────────────────

def test_run_parallel_optimizer_covers_all_recs():
    """run_parallel_optimizer must return exactly one result per input rec."""
    recs = [
        _rec_dict("REC-ALL00001", "INCREASE_UNDERWEIGHT", "EQUITIES.US.LARGE"),
        _rec_dict("REC-ALL00002", "REDUCE_OVERWEIGHT", "EQUITIES.US.MEGA.HYPER_MEGA"),
        _rec_dict("REC-ALL00003", "IMPROVE_RISK_PROFILE", None),
        _rec_dict("REC-ALL00004", "DIVERSIFY_CONCENTRATION", None),
    ]

    results = run_parallel_optimizer(
        recs_with_overlay=recs,
        holdings=[],
        overlays=[],
        profiles=[],
        alignment_results=[],
        mandate_interpretations=[],
    )

    for rec in recs:
        rid = rec["recommendation_id"]
        assert rid in results, f"optimizer_scores missing result for rec {rid}"

    assert results["REC-ALL00001"]["rec_type"] == "INCREASE_UNDERWEIGHT"
    assert results["REC-ALL00002"]["rec_type"] == "REDUCE_OVERWEIGHT"
    assert results["REC-ALL00002"]["optimizer_decision"] == "REDUCE_COHERENT"
    assert results["REC-ALL00003"]["optimizer_decision"] == "NOT_APPLICABLE"
    assert results["REC-ALL00004"]["optimizer_decision"] == "NOT_APPLICABLE"


# ─────────────────────────────────────────────────────────────────────────────
# 12 — _holding_in_target_node correctly matches holdings to allocation nodes
# ─────────────────────────────────────────────────────────────────────────────

def test_holding_in_target_node_direct_large():
    """PortfolioHolding with EQUITIES/US/LARGE should match EQUITIES.US.LARGE."""
    h = _holding("VRT", market_cap_bucket="LARGE", geography="US", asset_class="EQUITIES")
    assert _holding_in_target_node(h, "EQUITIES.US.LARGE") is True
    assert _holding_in_target_node(h, "EQUITIES.US.MEGA") is False
    assert _holding_in_target_node(h, "EQUITIES.US") is True
    assert _holding_in_target_node(h, "EQUITIES") is True


def test_holding_in_target_node_mega_subtier():
    """MEGA cap with HYPER_MEGA subtier should match only its subtier node."""
    h = _holding(
        "NVDA",
        market_cap_bucket="MEGA",
        geography="US",
        asset_class="EQUITIES",
        mega_subtier="HYPER_MEGA",
    )
    assert _holding_in_target_node(h, "EQUITIES.US.MEGA.HYPER_MEGA") is True
    assert _holding_in_target_node(h, "EQUITIES.US.MEGA.EXTENDED_MEGA") is False
    assert _holding_in_target_node(h, "EQUITIES.US.MEGA") is True
    assert _holding_in_target_node(h, "EQUITIES.US.LARGE") is False


def test_holding_cash_excluded_from_equity_nodes():
    """Cash-equivalent holdings should never match equity allocation nodes."""
    h = _holding("SNSXX", asset_class="CASH", is_cash_eq=True)
    assert _holding_in_target_node(h, "EQUITIES.US.LARGE") is False
    assert _holding_in_target_node(h, "EQUITIES") is False


# ─────────────────────────────────────────────────────────────────────────────
# 13 — PIS component breakdown is internally consistent
# ─────────────────────────────────────────────────────────────────────────────

def test_pis_components_sum_to_total():
    """The sum of PIS components should equal final PIS (before mandate gate)."""
    candidate = score_security_candidate(
        symbol="LRCX",
        target_node="EQUITIES.US.LARGE",
        node_gap=-7.34,
        composite_score=4.500,
        ess_score="BULLISH",
        replay_supported=True,
        sti_tier="HCA",
        trim_priority_score=10.0,
        percent_of_portfolio=0.95,
        overweight_nodes={},
        mandate_gate="PASS",
        mandate_blocked=False,
    )
    components = candidate["components"]
    computed_pis = (
        components["composite_component"]
        + components["replay_component"]
        + components["node_gap_component"]
        + components["conviction_component"]
        + components["ess_component"]
        - components["trim_penalty"]
        - components["concentration_penalty"]
        - components["conflict_penalty"]
    )
    assert abs(candidate["pis"] - max(0.0, round(computed_pis, 2))) < 0.05, (
        f"PIS components don't sum correctly: computed={computed_pis:.2f}, "
        f"reported={candidate['pis']:.2f}. Components: {components}"
    )


def test_security_pis_formula_spot_check_vrt():
    """Spot-check VRT PIS against Phase 7.2 expected value (~76.7)."""
    # Phase 7.2 expected: VRT PIS ≈ 76.7
    # composite=4.556 → 4.556*6=27.34
    # replay=True → 20
    # node_gap=-7.34 → min(7.34*2,20)=14.68
    # CCL → 10
    # ESS=BULLISH → 3
    # trim_score=15 → penalty=3
    # concentration penalty (3.60 < 5%) → 0
    # Total: 27.34+20+14.68+10+3-3 = 72.02
    # Note: slight differences from Phase 7.2 are expected (formula uses max 20 for replay)
    candidate = score_security_candidate(
        symbol="VRT",
        target_node="EQUITIES.US.LARGE",
        node_gap=-7.34,
        composite_score=4.556,
        ess_score="BULLISH",
        replay_supported=True,
        sti_tier="CCL",
        trim_priority_score=15.0,
        percent_of_portfolio=3.60,
        overweight_nodes={},
        mandate_gate="PASS",
        mandate_blocked=False,
    )
    # Expect PIS in the 65-80 range
    assert 60.0 <= candidate["pis"] <= 85.0, (
        f"VRT PIS expected ~72 (compare to Phase 7.2 audit ~76.7), got {candidate['pis']:.2f}. "
        f"Components: {candidate['components']}"
    )
    assert candidate["optimizer_status"] == "ACTIONABLE"


# ─────────────────────────────────────────────────────────────────────────────
# 14 — Overweight node detection from alignment
# ─────────────────────────────────────────────────────────────────────────────

def test_overweight_nodes_from_alignment():
    """_overweight_nodes_from_alignment returns only MODERATE+ OW nodes."""
    alignment = [
        _alignment_result("EQUITIES.US.MEGA.HYPER_MEGA", "OVERWEIGHT", "MODERATE", drift_pct=3.71),
        _alignment_result("EQUITIES.US.LARGE", "UNDERWEIGHT", "MODERATE", drift_pct=-7.34),
        _alignment_result("EQUITIES.INTERNATIONAL", "OVERWEIGHT", "LOW", drift_pct=1.0),
    ]
    ow_nodes = _overweight_nodes_from_alignment(alignment)
    assert "EQUITIES.US.MEGA.HYPER_MEGA" in ow_nodes
    assert "EQUITIES.US.LARGE" not in ow_nodes  # underweight
    assert "EQUITIES.INTERNATIONAL" not in ow_nodes  # severity=LOW excluded


# ─────────────────────────────────────────────────────────────────────────────
# 15 — mandate gate function
# ─────────────────────────────────────────────────────────────────────────────

def test_mandate_gate_pass_for_standard_underweight():
    """Standard underweight nodes with MODERATE urgency should pass the gate."""
    interps = [_mandate_interp("EQUITIES.US.LARGE", "MODERATE", "STANDARD_UNDERWEIGHT")]
    gate, blocked = _mandate_gate_for_node("EQUITIES.US.LARGE", interps)
    assert gate == "PASS"
    assert blocked is False


def test_mandate_gate_fail_for_informational():
    """INFORMATIONAL urgency should fail the mandate gate."""
    interps = [
        _mandate_interp("EQUITIES.US.LARGE", "INFORMATIONAL", "INTENTIONAL_UNDERWEIGHT", suppress=True)
    ]
    gate, blocked = _mandate_gate_for_node("EQUITIES.US.LARGE", interps)
    assert gate == "FAIL"
    assert blocked is True


def test_mandate_gate_pass_for_unknown_node():
    """Nodes with no interpretation should pass the mandate gate (no block)."""
    gate, blocked = _mandate_gate_for_node("EQUITIES.FRONTIER", [])
    assert gate == "PASS"
    assert blocked is False
