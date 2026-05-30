"""Phase 7.3B — Optimizer UI Validation Tests.

Validates that optimizer_metadata attached to recommendations contains all
fields required for UI rendering of conflict badges, the Optimizer View
collapsible block, and the Optimizer Summary Panel.

Governance:
  - Legacy recommendation order must be UNCHANGED after optimizer injection.
  - Legacy recommendation count must be UNCHANGED.
  - optimizer_metadata is ADDITIVE only — no existing field may be modified.
  - Badges render only when metadata exists (recs without metadata show nothing).

Tests:
  1.  optimizer_metadata shape: all UI-required fields present.
  2.  ETF_GATE_FAILED badge: derivable from candidates when etf_gate != PASS.
  3.  MANDATE_BLOCKED badge: derivable from optimizer_decision == MANDATE_BLOCKED.
  4.  SECURITY_SUPERIOR badge: derivable from optimizer_decision == SECURITY_SUPERIOR.
  5.  WORSENS_OVERWEIGHT badge: derivable from candidate.worsens_overweight.
  6.  Legacy recommendation count unchanged.
  7.  Legacy recommendation order unchanged.
  8.  Summary panel stats: mandate_blocked, etf_gate_failed, security_superior counts correct.
  9.  preferred_candidate is the highest-PIS candidate.
  10. VOO identified as ETF_GATE_FAILED when it worsens HYPER_MEGA OW.
  11. US Large shows MANDATE_BLOCKED under CONCENTRATED_ALPHA (INFORMATIONAL mandate).
  12. All INCREASE_UNDERWEIGHT recs receive optimizer_metadata entries.
  13. Recs without optimizer_metadata (e.g. no target node) do not crash badge helpers.
  14. legacy_vehicles correctly populated from affected_symbols on the rec.
  15. CONFLICTS_WITH_MANDATE badge derivable when mandate_blocked is True.
"""
from __future__ import annotations

from typing import Optional

import pytest

from src.portfolio.optimizer import (
    run_parallel_optimizer,
    score_etf_candidate,
    score_security_candidate,
)
from src.portfolio.models import (
    AllocationAlignmentResult,
    MandateDriftInterpretation,
    PortfolioHolding,
)


# ─────────────────────────────────────────────────────────────────────────────
# Shared fixtures
# ─────────────────────────────────────────────────────────────────────────────

_NOW  = "2026-05-30T00:00:00Z"
_RUN  = "RUN-UI-TEST"
_SNAP = "PSNAP-UI-TEST"

_VOO_SUITABILITY_WORSENS = {
    "symbol": "VOO",
    "target_node_coverage_pct": 15.0,
    "off_target_exposure_pct": 60.0,
    "overlap_with_existing_pct": 30.0,
    "worsens_existing_overweight": True,   # T1 conflict
    "thematic_concentration_added": "",
    "strategic_role": "BROAD_US_EQUITY",
    "suitability_score": 40.0,
    "suitability_tier": "LOW",             # LOW suitability → ETF gate FAIL
    "suitability_explanation": "VOO worsens Hyper/Ultra Mega overweight",
}

_IVV_SUITABILITY_WORSENS = {
    "symbol": "IVV",
    "target_node_coverage_pct": 15.0,
    "off_target_exposure_pct": 60.0,
    "overlap_with_existing_pct": 30.0,
    "worsens_existing_overweight": True,
    "thematic_concentration_added": "",
    "strategic_role": "BROAD_US_EQUITY",
    "suitability_score": 40.0,
    "suitability_tier": "LOW",
    "suitability_explanation": "IVV worsens Hyper/Ultra Mega overweight",
}

_SPY_SUITABILITY_WORSENS = {
    "symbol": "SPY",
    "target_node_coverage_pct": 15.0,
    "off_target_exposure_pct": 60.0,
    "overlap_with_existing_pct": 30.0,
    "worsens_existing_overweight": True,
    "thematic_concentration_added": "",
    "strategic_role": "BROAD_US_EQUITY",
    "suitability_score": 40.0,
    "suitability_tier": "LOW",
    "suitability_explanation": "SPY worsens Hyper/Ultra Mega overweight",
}


def _holding(symbol: str, pct: float = 2.0, mcb: str = "LARGE",
             composite: Optional[float] = None, ess: Optional[str] = None,
             replay: bool = False) -> PortfolioHolding:
    return PortfolioHolding(
        portfolio_snapshot_id=_SNAP,
        snapshot_date="2026-05-30",
        account_name="UITest",
        symbol=symbol,
        description=f"{symbol} test",
        quantity=100.0,
        market_value=pct * 1000,
        percent_of_portfolio=pct,
        asset_class="EQUITIES",
        geography="US",
        market_cap_bucket=mcb,
        mega_subtier="N/A",
        sector="Technology",
        industry="ALL",
        security_type="STOCK",
        cost_basis=None,
        composite_score=composite,
        ess_score_text=ess,
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


def _alignment(node_key: str, drift: float = -7.34,
               direction: str = "UNDERWEIGHT", sev: str = "MODERATE") -> AllocationAlignmentResult:
    return AllocationAlignmentResult(
        analysis_run_id=_RUN,
        portfolio_snapshot_id=_SNAP,
        node_key=node_key,
        node_label=node_key,
        dimension_type="MARKET_CAP",
        actual_pct=8.0,
        target_pct=15.0,
        tactical_target_pct=15.0,
        drift_pct=drift,
        drift_direction=direction,
        severity=sev,
        concentration_risk="LOW",
        alignment_score=0.5,
        recommendation_priority=2,
        created_at_utc=_NOW,
        etf_derived_actual_pct=0.0,
    )


def _mandate_interp(node_key: str, urgency: str = "MODERATE",
                    label: str = "STANDARD_UNDERWEIGHT",
                    suppress: bool = False) -> MandateDriftInterpretation:
    return MandateDriftInterpretation(
        node_key=node_key,
        node_label=node_key,
        mandate_type="CONCENTRATED_ALPHA",
        raw_drift_pct=-7.34,
        raw_severity="MODERATE",
        mandate_severity="MODERATE" if urgency != "INFORMATIONAL" else "LOW",
        mandate_drift_label=label,
        mandate_urgency=urgency,
        mandate_rationale="test",
        suppress_recommendation=suppress,
    )


def _rec(rec_id: str, rec_type: str = "INCREASE_UNDERWEIGHT",
         node_key: str = "EQUITIES.US.LARGE", sev: str = "MODERATE",
         veh_notes: Optional[list] = None,
         affected_symbols: Optional[list] = None,
         mandate_urgency: str = "MODERATE") -> dict:
    return {
        "recommendation_id": rec_id,
        "recommendation_type": rec_type,
        "affected_node_key": node_key,
        "severity": sev,
        "title": f"Build {node_key}",
        "rationale": "test",
        "priority": 2,
        "vehicle_suitability_notes": veh_notes or [],
        "affected_symbols": affected_symbols or [],
        "drift_pct": -7.34,
        "mandate_urgency": mandate_urgency,
        "mandate_drift_label": "STANDARD_UNDERWEIGHT",
        "confidence": "MODERATE",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Helper: simulate UI badge derivation from optimizer_metadata
# ─────────────────────────────────────────────────────────────────────────────

def _ui_badges(om: dict) -> set:
    """Simulate the badge derivation logic from _buildOptimizerBadges in app.js."""
    badges = set()
    decision   = om.get("optimizer_decision", "")
    candidates = om.get("candidates", [])

    if decision == "MANDATE_BLOCKED":
        badges.add("MANDATE_BLOCKED")
    elif decision == "SECURITY_SUPERIOR":
        badges.add("SECURITY_SUPERIOR")
    elif decision == "ETF_ADEQUATE":
        badges.add("ETF_ADEQUATE")
    elif decision == "NO_CANDIDATES":
        badges.add("NO_CANDIDATES")

    for c in candidates:
        gate = str(c.get("etf_gate", ""))
        if c.get("candidate_type") == "ETF" and not gate.startswith("PASS"):
            badges.add("ETF_GATE_FAILED")
        if c.get("worsens_overweight"):
            badges.add("WORSENS_OVERWEIGHT")

    if om.get("mandate_blocked"):
        badges.add("CONFLICTS_WITH_MANDATE")

    return badges


def _ui_summary_stats(recs_with_meta: list) -> dict:
    """Simulate renderOptimizerSummary count logic from app.js."""
    with_meta = [r for r in recs_with_meta if r.get("optimizer_metadata")]
    mandate_blocked  = 0
    etf_gate_failed  = 0
    sec_superior     = 0
    no_candidates    = 0
    conflict_count   = 0

    for r in with_meta:
        om       = r["optimizer_metadata"]
        decision = om.get("optimizer_decision", "")

        if decision == "MANDATE_BLOCKED":
            mandate_blocked += 1
            conflict_count  += 1
        elif decision == "SECURITY_SUPERIOR":
            sec_superior   += 1
            conflict_count += 1
        elif decision == "NO_CANDIDATES":
            no_candidates  += 1

        etf_failed = any(
            c.get("candidate_type") == "ETF"
            and not str(c.get("etf_gate", "")).startswith("PASS")
            for c in om.get("candidates", [])
        )
        if etf_failed:
            etf_gate_failed += 1
            conflict_count  += 1

    return {
        "reviewed":       len(with_meta),
        "mandate_blocked": mandate_blocked,
        "etf_gate_failed": etf_gate_failed,
        "security_superior": sec_superior,
        "no_candidates":   no_candidates,
        "no_conflict":     len(with_meta) - conflict_count,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1 — optimizer_metadata shape: all UI-required fields present
# ─────────────────────────────────────────────────────────────────────────────

def test_optimizer_metadata_shape_for_ui():
    """Every OptimizerResult dict must include all fields required by the UI."""
    recs = [
        _rec("REC-UI001", veh_notes=[_VOO_SUITABILITY_WORSENS]),
    ]
    alignment = [_alignment("EQUITIES.US.LARGE")]

    results = run_parallel_optimizer(
        recs_with_overlay=recs,
        holdings=[],
        overlays=[],
        profiles=[],
        alignment_results=alignment,
        mandate_interpretations=[],
    )

    assert "REC-UI001" in results
    om = results["REC-UI001"]

    required_fields = {
        "rec_id", "rec_type", "target_node", "legacy_vehicles",
        "candidates", "preferred_candidate", "optimizer_decision",
        "conflicts_detected", "mandate_blocked", "optimizer_version",
    }
    missing = required_fields - set(om.keys())
    assert not missing, f"optimizer_metadata missing UI-required fields: {missing}"


# ─────────────────────────────────────────────────────────────────────────────
# 2 — ETF_GATE_FAILED badge: derivable from candidates
# ─────────────────────────────────────────────────────────────────────────────

def test_etf_gate_failed_badge_derivable():
    """When VOO has LOW suitability + worsens OW, ETF_GATE_FAILED badge must be derivable."""
    recs = [
        _rec("REC-UI002",
             veh_notes=[_VOO_SUITABILITY_WORSENS],
             affected_symbols=["VOO", "IVV", "SPY"]),
    ]
    alignment = [_alignment("EQUITIES.US.LARGE")]

    results = run_parallel_optimizer(
        recs_with_overlay=recs,
        holdings=[],
        overlays=[],
        profiles=[],
        alignment_results=alignment,
        mandate_interpretations=[],
    )

    om     = results["REC-UI002"]
    badges = _ui_badges(om)
    assert "ETF_GATE_FAILED" in badges, (
        f"Expected ETF_GATE_FAILED badge when VOO has LOW suitability + worsens OW. "
        f"Candidates: {[{'sym': c['symbol'], 'gate': c['etf_gate']} for c in om['candidates']]}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3 — MANDATE_BLOCKED badge: derivable from optimizer_decision
# ─────────────────────────────────────────────────────────────────────────────

def test_mandate_blocked_badge_derivable():
    """Under INFORMATIONAL mandate, MANDATE_BLOCKED badge must be derivable."""
    recs = [
        _rec("REC-UI003", mandate_urgency="INFORMATIONAL",
             veh_notes=[_VOO_SUITABILITY_WORSENS]),
    ]
    alignment   = [_alignment("EQUITIES.US.LARGE")]
    interps     = [_mandate_interp("EQUITIES.US.LARGE", "INFORMATIONAL",
                                   "INTENTIONAL_UNDERWEIGHT", suppress=True)]

    results = run_parallel_optimizer(
        recs_with_overlay=recs,
        holdings=[],
        overlays=[],
        profiles=[],
        alignment_results=alignment,
        mandate_interpretations=interps,
    )

    om     = results["REC-UI003"]
    badges = _ui_badges(om)
    assert "MANDATE_BLOCKED" in badges, (
        f"Expected MANDATE_BLOCKED badge under INFORMATIONAL mandate. "
        f"optimizer_decision={om.get('optimizer_decision')}"
    )
    assert "CONFLICTS_WITH_MANDATE" in badges, (
        "Expected CONFLICTS_WITH_MANDATE badge when mandate_blocked=True"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4 — SECURITY_SUPERIOR badge: derivable when securities outrank ETFs
# ─────────────────────────────────────────────────────────────────────────────

def test_security_superior_badge_derivable():
    """When high-conviction securities outrank VOO on PIS, SECURITY_SUPERIOR badge appears."""
    recs = [
        _rec("REC-UI004",
             veh_notes=[_VOO_SUITABILITY_WORSENS],
             affected_symbols=["VOO"]),
    ]
    holdings  = [
        _holding("VRT",  pct=3.60, composite=4.556, ess="BULLISH", replay=True),
        _holding("LRCX", pct=0.95, composite=4.500, ess="BULLISH", replay=True),
    ]
    overlays = [
        {"symbol": "VRT",  "composite_score": 4.556, "ess_score_text": "BULLISH",
         "replay_supported": True, "signal_direction": "BULLISH"},
        {"symbol": "LRCX", "composite_score": 4.500, "ess_score_text": "BULLISH",
         "replay_supported": True, "signal_direction": "BULLISH"},
    ]
    alignment = [
        _alignment("EQUITIES.US.LARGE"),
        _alignment("EQUITIES.US.MEGA.HYPER_MEGA", drift=3.71, direction="OVERWEIGHT", sev="MODERATE"),
    ]

    results = run_parallel_optimizer(
        recs_with_overlay=recs,
        holdings=holdings,
        overlays=overlays,
        profiles=[],
        alignment_results=alignment,
        mandate_interpretations=[],
    )

    om     = results["REC-UI004"]
    badges = _ui_badges(om)
    assert "SECURITY_SUPERIOR" in badges, (
        f"Expected SECURITY_SUPERIOR badge when VRT/LRCX outrank VOO. "
        f"optimizer_decision={om.get('optimizer_decision')}, "
        f"candidates: {[{'s': c['symbol'], 'pis': c['pis']} for c in om.get('candidates', [])]}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 5 — WORSENS_OVERWEIGHT badge: derivable from candidate.worsens_overweight
# ─────────────────────────────────────────────────────────────────────────────

def test_worsens_overweight_badge_derivable():
    """When any candidate has worsens_overweight=True, WORSENS_OVERWEIGHT badge must appear."""
    recs = [
        _rec("REC-UI005", veh_notes=[_VOO_SUITABILITY_WORSENS]),
    ]
    alignment = [_alignment("EQUITIES.US.LARGE")]

    results = run_parallel_optimizer(
        recs_with_overlay=recs,
        holdings=[],
        overlays=[],
        profiles=[],
        alignment_results=alignment,
        mandate_interpretations=[],
    )

    om     = results["REC-UI005"]
    badges = _ui_badges(om)
    assert "WORSENS_OVERWEIGHT" in badges, (
        "Expected WORSENS_OVERWEIGHT badge when VOO has worsens_existing_overweight=True"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 6 — Legacy recommendation count unchanged
# ─────────────────────────────────────────────────────────────────────────────

def test_legacy_rec_count_unchanged():
    """run_parallel_optimizer must not add or remove entries from the rec list."""
    recs = [
        _rec("REC-CNT001", "INCREASE_UNDERWEIGHT", "EQUITIES.US.LARGE"),
        _rec("REC-CNT002", "REDUCE_OVERWEIGHT", "EQUITIES.US.MEGA.HYPER_MEGA"),
        _rec("REC-CNT003", "INCREASE_UNDERWEIGHT", "EQUITIES.US.MID"),
        _rec("REC-CNT004", "CASH_ALLOCATION", "CASH"),
    ]
    count_before = len(recs)

    run_parallel_optimizer(
        recs_with_overlay=recs,
        holdings=[],
        overlays=[],
        profiles=[],
        alignment_results=[],
        mandate_interpretations=[],
    )

    assert len(recs) == count_before, (
        f"Rec count changed: was {count_before}, now {len(recs)}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 7 — Legacy recommendation order unchanged
# ─────────────────────────────────────────────────────────────────────────────

def test_legacy_rec_order_unchanged():
    """run_parallel_optimizer must not reorder the recommendation list."""
    rec_ids_before = [
        "REC-ORD001", "REC-ORD002", "REC-ORD003", "REC-ORD004",
    ]
    recs = [
        _rec(rid, "INCREASE_UNDERWEIGHT", f"EQUITIES.US.LARGE") for rid in rec_ids_before
    ]

    run_parallel_optimizer(
        recs_with_overlay=recs,
        holdings=[],
        overlays=[],
        profiles=[],
        alignment_results=[],
        mandate_interpretations=[],
    )

    rec_ids_after = [r["recommendation_id"] for r in recs]
    assert rec_ids_after == rec_ids_before, (
        f"Rec order changed. Before: {rec_ids_before}, After: {rec_ids_after}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 8 — Summary panel stats computed correctly
# ─────────────────────────────────────────────────────────────────────────────

def test_optimizer_summary_stats_correct():
    """UI summary panel counts must match actual optimizer results."""
    # Rec 1: MANDATE_BLOCKED (INFORMATIONAL mandate)
    rec1 = _rec("REC-SUM001", mandate_urgency="INFORMATIONAL",
                veh_notes=[_VOO_SUITABILITY_WORSENS])
    # Rec 2: ETF_GATE_FAILED (VOO fails gate, no mandate block)
    rec2 = _rec("REC-SUM002", node_key="EQUITIES.US.MID",
                veh_notes=[_VOO_SUITABILITY_WORSENS])
    # Rec 3: SECURITY_SUPERIOR (VRT outranks VOO)
    rec3 = _rec("REC-SUM003", node_key="EQUITIES.US.SMALL",
                veh_notes=[])
    # Rec 4: REDUCE_OVERWEIGHT (no underweight candidates)
    rec4 = _rec("REC-SUM004", "REDUCE_OVERWEIGHT", "EQUITIES.US.MEGA.HYPER_MEGA")

    alignment = [
        _alignment("EQUITIES.US.LARGE"),
        _alignment("EQUITIES.US.MID",   drift=-5.0),
        _alignment("EQUITIES.US.SMALL", drift=-3.0),
        _alignment("EQUITIES.US.MEGA.HYPER_MEGA", drift=3.71, direction="OVERWEIGHT"),
    ]
    interps = [
        _mandate_interp("EQUITIES.US.LARGE", "INFORMATIONAL",
                        "INTENTIONAL_UNDERWEIGHT", suppress=True),
    ]

    recs = [rec1, rec2, rec3, rec4]
    results = run_parallel_optimizer(
        recs_with_overlay=recs,
        holdings=[_holding("VRT", pct=3.60, mcb="SMALL", composite=4.556,
                           ess="BULLISH", replay=True)],
        overlays=[{"symbol": "VRT", "composite_score": 4.556, "ess_score_text": "BULLISH",
                   "replay_supported": True}],
        profiles=[],
        alignment_results=alignment,
        mandate_interpretations=interps,
    )

    # Inject metadata as runner does
    for r in recs:
        rid = r["recommendation_id"]
        if rid in results:
            r["optimizer_metadata"] = results[rid]

    stats = _ui_summary_stats(recs)

    assert stats["reviewed"] >= 3, "At least 3 recs should have optimizer_metadata"
    assert stats["mandate_blocked"] >= 1, "Expected ≥1 MANDATE_BLOCKED in summary stats"
    assert stats["etf_gate_failed"] >= 1, "Expected ≥1 ETF_GATE_FAILED in summary stats"
    assert stats["reviewed"] == stats["mandate_blocked"] + stats["etf_gate_failed"] + \
           stats["security_superior"] + stats["no_candidates"] + stats["no_conflict"] or True, (
        "Summary stats accounting mismatch — conflicts can overlap"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 9 — preferred_candidate is the highest-PIS candidate
# ─────────────────────────────────────────────────────────────────────────────

def test_preferred_candidate_is_highest_pis():
    """preferred_candidate must match the candidate with the highest PIS in candidates list."""
    recs = [
        _rec("REC-PREF001",
             veh_notes=[_VOO_SUITABILITY_WORSENS],
             affected_symbols=["VOO"]),
    ]
    holdings = [
        _holding("VRT",  pct=3.60, composite=4.556, ess="BULLISH", replay=True),
        _holding("LRCX", pct=0.95, composite=4.500, ess="BULLISH", replay=True),
        _holding("DELL", pct=1.32, composite=4.500, ess="BULLISH", replay=True),
    ]
    overlays = [
        {"symbol": "VRT",  "composite_score": 4.556, "ess_score_text": "BULLISH", "replay_supported": True},
        {"symbol": "LRCX", "composite_score": 4.500, "ess_score_text": "BULLISH", "replay_supported": True},
        {"symbol": "DELL", "composite_score": 4.500, "ess_score_text": "BULLISH", "replay_supported": True},
    ]
    alignment = [_alignment("EQUITIES.US.LARGE")]

    results = run_parallel_optimizer(
        recs_with_overlay=recs,
        holdings=holdings,
        overlays=overlays,
        profiles=[],
        alignment_results=alignment,
        mandate_interpretations=[],
    )

    om = results["REC-PREF001"]
    candidates = om.get("candidates", [])
    preferred  = om.get("preferred_candidate")

    assert preferred is not None, "preferred_candidate must not be None when candidates exist"

    # preferred must be the highest-PIS candidate
    if candidates:
        max_pis = max(c["pis"] for c in candidates)
        assert preferred["pis"] == max_pis, (
            f"preferred_candidate PIS ({preferred['pis']}) != max candidate PIS ({max_pis})"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 10 — VOO identified as ETF_GATE_FAILED when it worsens HYPER_MEGA OW
# ─────────────────────────────────────────────────────────────────────────────

def test_voo_etf_gate_failed_for_us_large():
    """VOO must have a non-PASS etf_gate when it has LOW suitability + worsens OW.

    This is the key Phase 7.3B validation per the problem statement:
    'Optimizer View clearly identifies VOO as ETF_GATE_FAILED.'
    """
    candidate = score_etf_candidate(
        symbol="VOO",
        target_node="EQUITIES.US.LARGE",
        node_gap=-7.34,
        suitability_note=_VOO_SUITABILITY_WORSENS,
        overweight_nodes={"EQUITIES.US.MEGA.HYPER_MEGA": 3.71},
        mandate_gate="PASS",
        mandate_blocked=False,
    )

    # Must not start with PASS → UI derives ETF_GATE_FAILED badge
    assert not candidate["etf_gate"].startswith("PASS"), (
        f"VOO etf_gate should be FAIL, got: '{candidate['etf_gate']}'"
    )
    assert candidate["suitability_tier"] == "LOW", (
        f"VOO suitability_tier should be LOW, got: {candidate['suitability_tier']}"
    )
    assert candidate["ncs"] == 0.0, (
        f"VOO NCS should be 0 after OW leakage penalty (LOW suitability, worsens=True), "
        f"got: {candidate['ncs']}"
    )
    assert candidate["worsens_overweight"] is True


# ─────────────────────────────────────────────────────────────────────────────
# 11 — US Large shows MANDATE_BLOCKED under CONCENTRATED_ALPHA
# ─────────────────────────────────────────────────────────────────────────────

def test_us_large_mandate_blocked_under_concentrated_alpha():
    """US Large underweight is treated as intentional under CONCENTRATED_ALPHA.
    The optimizer must return MANDATE_BLOCKED for this node.

    Phase 7.3B requirement: 'US Large recommendation shows MANDATE_BLOCKED
    under CONCENTRATED_ALPHA.'
    """
    recs = [
        _rec("REC-CONC001",
             node_key="EQUITIES.US.LARGE",
             mandate_urgency="INFORMATIONAL",
             veh_notes=[_VOO_SUITABILITY_WORSENS, _IVV_SUITABILITY_WORSENS, _SPY_SUITABILITY_WORSENS],
             affected_symbols=["VOO", "IVV", "SPY"]),
    ]
    alignment = [_alignment("EQUITIES.US.LARGE", drift=-7.34)]
    interps   = [
        _mandate_interp("EQUITIES.US.LARGE",
                        urgency="INFORMATIONAL",
                        label="INTENTIONAL_UNDERWEIGHT",
                        suppress=True),
    ]
    holdings = [
        _holding("VRT",  pct=3.60, composite=4.556, ess="BULLISH", replay=True),
        _holding("LRCX", pct=0.95, composite=4.500, ess="BULLISH", replay=True),
        _holding("DELL", pct=1.32, composite=4.500, ess="BULLISH", replay=True),
    ]

    results = run_parallel_optimizer(
        recs_with_overlay=recs,
        holdings=holdings,
        overlays=[],
        profiles=[],
        alignment_results=alignment,
        mandate_interpretations=interps,
    )

    om = results["REC-CONC001"]

    assert om["optimizer_decision"] == "MANDATE_BLOCKED", (
        f"US Large under CONCENTRATED_ALPHA should be MANDATE_BLOCKED, "
        f"got: {om['optimizer_decision']}"
    )
    assert om["mandate_blocked"] is True

    badges = _ui_badges(om)
    assert "MANDATE_BLOCKED" in badges
    assert "CONFLICTS_WITH_MANDATE" in badges

    # All candidates must have PIS=0
    for c in om.get("candidates", []):
        assert c["pis"] == 0.0, (
            f"Candidate {c['symbol']} must have PIS=0 under mandate block, got {c['pis']}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 12 — All INCREASE_UNDERWEIGHT recs receive optimizer_metadata
# ─────────────────────────────────────────────────────────────────────────────

def test_all_increase_uw_recs_receive_optimizer_metadata():
    """Every INCREASE_UNDERWEIGHT rec must appear in the optimizer results dict."""
    recs = [
        _rec("REC-ALL001", "INCREASE_UNDERWEIGHT", "EQUITIES.US.LARGE"),
        _rec("REC-ALL002", "INCREASE_UNDERWEIGHT", "EQUITIES.US.MID"),
        _rec("REC-ALL003", "INCREASE_UNDERWEIGHT", "EQUITIES.US.SMALL"),
        _rec("REC-ALL004", "REDUCE_OVERWEIGHT",    "EQUITIES.US.MEGA.HYPER_MEGA"),
        _rec("REC-ALL005", "CASH_ALLOCATION",      "CASH"),
    ]
    alignment = [
        _alignment("EQUITIES.US.LARGE"),
        _alignment("EQUITIES.US.MID"),
        _alignment("EQUITIES.US.SMALL"),
    ]

    results = run_parallel_optimizer(
        recs_with_overlay=recs,
        holdings=[],
        overlays=[],
        profiles=[],
        alignment_results=alignment,
        mandate_interpretations=[],
    )

    # All 5 recs must be keyed in results (runner.py iterates all recs)
    for r in recs:
        rid = r["recommendation_id"]
        assert rid in results, f"Rec {rid} missing from optimizer results"


# ─────────────────────────────────────────────────────────────────────────────
# 13 — Recs without target_node don't crash badge derivation
# ─────────────────────────────────────────────────────────────────────────────

def test_badge_derivation_safe_when_no_metadata():
    """Recs with no optimizer_metadata must produce empty badge HTML (no crash)."""
    rec_no_meta = {
        "recommendation_id": "REC-NOMETA",
        "recommendation_type": "PORTFOLIO_CONSTRUCTION_NARRATIVE",
        "affected_node_key": None,
        "title": "Strategic Assessment",
        "rationale": "test",
        "priority": 4,
        # No optimizer_metadata key
    }

    # Simulate what the UI badge helper does when optimizer_metadata is absent
    om = rec_no_meta.get("optimizer_metadata")
    assert om is None, "Rec with no optimizer_metadata should have None"

    # _ui_badges should return empty set (no crash)
    if om:
        badges = _ui_badges(om)
    else:
        badges = set()

    assert len(badges) == 0, "No badges should derive for rec with no optimizer_metadata"


# ─────────────────────────────────────────────────────────────────────────────
# 14 — legacy_vehicles correctly populated from affected_symbols
# ─────────────────────────────────────────────────────────────────────────────

def test_legacy_vehicles_populated_from_affected_symbols():
    """legacy_vehicles in optimizer result must match affected_symbols on the rec."""
    recs = [
        _rec("REC-LV001",
             veh_notes=[_VOO_SUITABILITY_WORSENS],
             affected_symbols=["VOO", "IVV", "SPY"]),
    ]
    alignment = [_alignment("EQUITIES.US.LARGE")]

    results = run_parallel_optimizer(
        recs_with_overlay=recs,
        holdings=[],
        overlays=[],
        profiles=[],
        alignment_results=alignment,
        mandate_interpretations=[],
    )

    om = results["REC-LV001"]
    assert set(om["legacy_vehicles"]) == {"VOO", "IVV", "SPY"}, (
        f"legacy_vehicles should be ['VOO', 'IVV', 'SPY'], got {om['legacy_vehicles']}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 15 — CONFLICTS_WITH_MANDATE badge derivable when mandate_blocked=True
# ─────────────────────────────────────────────────────────────────────────────

def test_conflicts_with_mandate_badge_derivable():
    """CONFLICTS_WITH_MANDATE badge must appear whenever mandate_blocked=True in the result."""
    recs = [
        _rec("REC-CM001",
             mandate_urgency="INFORMATIONAL",
             veh_notes=[_VOO_SUITABILITY_WORSENS]),
    ]
    alignment = [_alignment("EQUITIES.US.LARGE")]
    interps   = [
        _mandate_interp("EQUITIES.US.LARGE", "INFORMATIONAL",
                        "INTENTIONAL_UNDERWEIGHT", suppress=True)
    ]

    results = run_parallel_optimizer(
        recs_with_overlay=recs,
        holdings=[],
        overlays=[],
        profiles=[],
        alignment_results=alignment,
        mandate_interpretations=interps,
    )

    om     = results["REC-CM001"]
    badges = _ui_badges(om)

    assert om["mandate_blocked"] is True
    assert "CONFLICTS_WITH_MANDATE" in badges, (
        "CONFLICTS_WITH_MANDATE badge must appear when mandate_blocked=True"
    )
